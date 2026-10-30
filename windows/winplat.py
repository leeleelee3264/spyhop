"""Windows 에서 board.py 가 맥의 ps · lsof · osascript · launchctl 대신 쓰는 것들 (표준 라이브러리 ctypes 만 쓴다).

  process_rows()   ps -axo 대신: (pid, ppid, tty, start, 실행 파일) 목록
  command_line()   ps -o args= 대신: 프로그램 실행 인자
  cwd_of()         lsof -d cwd 대신: 프로그램이 일하는 폴더
  held_by()        lsof 대신: 이 파일들을 열어 둔 프로그램 (Restart Manager)
  focus()          osascript 대신: 세션이 도는 창을 앞으로
"""
import ctypes
import os
import re
import subprocess
import sys
import time
from ctypes import wintypes as W

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
ntdll = ctypes.WinDLL('ntdll')
u32 = ctypes.WinDLL('user32', use_last_error=True)
rm = ctypes.WinDLL('rstrtmgr')

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
STILL_ACTIVE = 259
ERROR_ACCESS_DENIED = 5
TH32CS_SNAPPROCESS = 0x2
INVALID_HANDLE_VALUE = W.HANDLE(-1).value
EPOCH_DIFF = 11644473600  # 1601-01-01 → 1970-01-01 (초)

# 보드가 띄우는 자식 프로그램(claude -p, codex exec …)이 창을 띄우지 않게 한다
CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_PROCESS_GROUP = 0x00000200


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [('dwSize', W.DWORD), ('cntUsage', W.DWORD), ('th32ProcessID', W.DWORD),
                ('th32DefaultHeapID', ctypes.c_size_t), ('th32ModuleID', W.DWORD), ('cntThreads', W.DWORD),
                ('th32ParentProcessID', W.DWORD), ('pcPriClassBase', ctypes.c_long), ('dwFlags', W.DWORD),
                ('szExeFile', W.WCHAR * 260)]


k32.OpenProcess.restype = W.HANDLE
k32.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]
k32.CloseHandle.argtypes = [W.HANDLE]
k32.GetExitCodeProcess.argtypes = [W.HANDLE, ctypes.POINTER(W.DWORD)]
k32.GetProcessTimes.argtypes = [W.HANDLE] + [ctypes.POINTER(W.FILETIME)] * 4
k32.QueryFullProcessImageNameW.argtypes = [W.HANDLE, W.DWORD, W.LPWSTR, ctypes.POINTER(W.DWORD)]
k32.CreateToolhelp32Snapshot.restype = W.HANDLE
k32.CreateToolhelp32Snapshot.argtypes = [W.DWORD, W.DWORD]
k32.Process32FirstW.argtypes = [W.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
k32.Process32NextW.argtypes = [W.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
k32.ReadProcessMemory.argtypes = [W.HANDLE, W.LPCVOID, W.LPVOID, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
ntdll.NtQueryInformationProcess.argtypes = [W.HANDLE, ctypes.c_int, W.LPVOID, W.ULONG, ctypes.POINTER(W.ULONG)]
k32.GetCurrentProcess.restype = W.HANDLE
k32.K32GetProcessMemoryInfo.argtypes = [W.HANDLE, ctypes.c_void_p, W.DWORD]
k32.GetUserDefaultLocaleName.argtypes = [W.LPWSTR, ctypes.c_int]


def _open(pid, access=PROCESS_QUERY_LIMITED_INFORMATION):
    return k32.OpenProcess(access, False, pid)


def alive(pid):
    """os.kill(pid, 0) 대신. Windows 에서 os.kill(pid, 0) 은 '살아 있나'가 아니라 그 프로그램에 Ctrl+C 를 보낸다."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    h = _open(pid)
    if not h:
        return ctypes.get_last_error() == ERROR_ACCESS_DENIED  # 다른 사용자 프로그램: 살아는 있다
    try:
        code = W.DWORD()
        return bool(k32.GetExitCodeProcess(h, ctypes.byref(code))) and code.value == STILL_ACTIVE
    finally:
        k32.CloseHandle(h)


def _filetime(ft):
    return ((ft.dwHighDateTime << 32) | ft.dwLowDateTime) / 1e7 - EPOCH_DIFF


def start_time(pid):
    """프로그램이 시작한 시각(epoch 초). 못 읽으면 0."""
    h = _open(pid)
    if not h:
        return 0
    try:
        c, e, k, u = W.FILETIME(), W.FILETIME(), W.FILETIME(), W.FILETIME()
        if not k32.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(k), ctypes.byref(u)):
            return 0
        return _filetime(c)
    finally:
        k32.CloseHandle(h)


def exe_path(pid):
    h = _open(pid)
    if not h:
        return ''
    try:
        buf, n = ctypes.create_unicode_buffer(32768), W.DWORD(32768)
        return buf.value if k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)) else ''
    finally:
        k32.CloseHandle(h)


def _snapshot():
    """[(pid, ppid, 실행 파일 이름)]"""
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if not snap or snap == INVALID_HANDLE_VALUE:
        return []
    out = []
    try:
        e = PROCESSENTRY32W()
        e.dwSize = ctypes.sizeof(e)
        ok = k32.Process32FirstW(snap, ctypes.byref(e))
        while ok:
            out.append((e.th32ProcessID, e.th32ParentProcessID, e.szExeFile))
            ok = k32.Process32NextW(snap, ctypes.byref(e))
    finally:
        k32.CloseHandle(snap)
    return out


# 세션이 어느 창에서 도는지: 조상 프로그램 중 처음 만나는 것으로 정한다
TERMINALS = {'windowsterminal.exe': 'Windows Terminal', 'openconsole.exe': 'Windows Terminal', 'code.exe': 'VS Code',
             'cursor.exe': 'Cursor', 'windsurf.exe': 'Windsurf', 'wezterm-gui.exe': 'WezTerm', 'alacritty.exe': 'Alacritty',
             'hyper.exe': 'Hyper', 'tabby.exe': 'Tabby', 'idea64.exe': 'IntelliJ', 'pycharm64.exe': 'PyCharm',
             'mintty.exe': 'Git Bash'}
SHELLS = {'cmd.exe', 'powershell.exe', 'pwsh.exe', 'bash.exe', 'wsl.exe', 'nu.exe', 'conhost.exe'}
AGENT_NAMES = {'claude.exe', 'codex.exe', 'bun.exe'}
_DESKTOP = {}


def is_desktop_app(path):
    """Claude 데스크톱 앱(Electron) 자체도 이름이 claude.exe 다. 옆에 resources\\app.asar 가 있으면 앱이지 세션이 아니다."""
    if path not in _DESKTOP:
        _DESKTOP[path] = bool(path) and os.path.exists(os.path.join(os.path.dirname(path), 'resources', 'app.asar'))
    return _DESKTOP[path]


def process_rows():
    """ps -axo pid=,ppid=,tty=,lstart=,comm= 대신. AI 프로그램만 시작 시각·전체 경로·tty 를 채운다(나머지는 0·이름·'??').
    tty: 터미널 앱에서 돌면 'con', Claude 데스크톱 앱이 띄운 세션이면 'app', 둘 다 아니면 '??'(화면 없는 프로그램)."""
    snap = _snapshot()
    parent = {p: pp for p, pp, _ in snap}
    name = {p: n for p, _, n in snap}
    rows = []
    for pid, ppid, exe in snap:
        if exe.lower() not in AGENT_NAMES:
            rows.append((pid, ppid, '??', 0, exe))
            continue
        path = exe_path(pid) or exe
        tty, _ = terminal_of(pid, parent, name)
        rows.append((pid, ppid, tty, start_time(pid), path))
    return rows


def terminal_of(pid, parent=None, name=None):
    """(tty, 창 이름). 조상을 거슬러 올라가며 처음 만나는 터미널 앱·Claude 앱으로 정한다."""
    if parent is None:
        snap = _snapshot()
        parent, name = {p: pp for p, pp, _ in snap}, {p: n for p, _, n in snap}
    shell, seen, p = False, 0, parent.get(pid)
    while p and seen < 30:
        n = (name.get(p) or '').lower()
        if n in TERMINALS:
            return 'con', TERMINALS[n]
        if n == 'claude.exe' and is_desktop_app(exe_path(p)):
            return 'app', 'Claude app'
        shell = shell or n in SHELLS
        p, seen = parent.get(p), seen + 1
    return ('con', 'Console') if shell else ('??', '')


def window_host(pid):
    """세션 창을 가진 조상 프로그램 번호 (focus 대상)."""
    snap = _snapshot()
    parent = {p: pp for p, pp, _ in snap}
    wins = _top_windows()
    p, seen = pid, 0
    while p and seen < 30:
        if p in wins:
            return p, wins[p]
        p, seen = parent.get(p), seen + 1
    return None, None


# ---------- 실행 인자 · 작업 폴더 ----------

class UNICODE_STRING(ctypes.Structure):
    _fields_ = [('Length', W.USHORT), ('MaximumLength', W.USHORT), ('Buffer', ctypes.c_void_p)]


class PROCESS_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [('Reserved1', ctypes.c_void_p), ('PebBaseAddress', ctypes.c_void_p), ('Reserved2', ctypes.c_void_p * 2),
                ('UniqueProcessId', ctypes.c_void_p), ('Reserved3', ctypes.c_void_p)]


def command_line(pid):
    """ps -o args= 대신 (ProcessCommandLineInformation, Windows 8.1+). 못 읽으면 ''."""
    h = _open(pid)
    if not h:
        return ''
    try:
        size = W.ULONG(0)
        ntdll.NtQueryInformationProcess(h, 60, None, 0, ctypes.byref(size))
        if not size.value:
            return ''
        buf = ctypes.create_string_buffer(size.value)
        if ntdll.NtQueryInformationProcess(h, 60, buf, size, ctypes.byref(size)) != 0:
            return ''
        us = UNICODE_STRING.from_buffer(buf)
        return ctypes.wstring_at(us.Buffer, us.Length // 2) if us.Buffer else ''
    finally:
        k32.CloseHandle(h)


shell32 = ctypes.WinDLL('shell32')
shell32.CommandLineToArgvW.restype = ctypes.POINTER(W.LPWSTR)
shell32.CommandLineToArgvW.argtypes = [W.LPCWSTR, ctypes.POINTER(ctypes.c_int)]
k32.LocalFree.argtypes = [W.HLOCAL]


def argv(pid):
    """실행 인자를 Windows 규칙(따옴표·공백)대로 나눈 목록."""
    line = command_line(pid)
    if not line:
        return []
    n = ctypes.c_int()
    p = shell32.CommandLineToArgvW(line, ctypes.byref(n))
    if not p:
        return []
    try:
        return [p[i] for i in range(n.value)]
    finally:
        k32.LocalFree(ctypes.cast(p, W.HLOCAL))


def _read(h, addr, size):
    buf, got = ctypes.create_string_buffer(size), ctypes.c_size_t()
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, size, ctypes.byref(got)) or got.value != size:
        raise OSError('read')
    return buf.raw


def cwd_of(pid):
    """lsof -d cwd 대신: PEB → RTL_USER_PROCESS_PARAMETERS.CurrentDirectory (64비트 프로그램만). 못 읽으면 None."""
    if ctypes.sizeof(ctypes.c_void_p) != 8:
        return None
    h = _open(pid, PROCESS_QUERY_INFORMATION | PROCESS_VM_READ)
    if not h:
        return None
    try:
        pbi = PROCESS_BASIC_INFORMATION()
        if ntdll.NtQueryInformationProcess(h, 0, ctypes.byref(pbi), ctypes.sizeof(pbi), None) != 0 or not pbi.PebBaseAddress:
            return None
        params = int.from_bytes(_read(h, pbi.PebBaseAddress + 0x20, 8), 'little')
        cur = _read(h, params + 0x38, 16)  # CURDIR.DosPath (UNICODE_STRING)
        length, addr = int.from_bytes(cur[0:2], 'little'), int.from_bytes(cur[8:16], 'little')
        if not length or not addr:
            return None
        path = _read(h, addr, length).decode('utf-16-le')
        return path.rstrip('\\') if len(path) > 3 else path
    except OSError:
        return None
    finally:
        k32.CloseHandle(h)


# ---------- 열린 파일 (Restart Manager) ----------

class RM_UNIQUE_PROCESS(ctypes.Structure):
    _fields_ = [('dwProcessId', W.DWORD), ('ProcessStartTime', W.FILETIME)]


class RM_PROCESS_INFO(ctypes.Structure):
    _fields_ = [('Process', RM_UNIQUE_PROCESS), ('strAppName', W.WCHAR * 256), ('strServiceShortName', W.WCHAR * 64),
                ('ApplicationType', ctypes.c_int), ('AppStatus', W.ULONG), ('TSSessionId', W.DWORD), ('bRestartable', W.BOOL)]


rm.RmStartSession.argtypes = [ctypes.POINTER(W.DWORD), W.DWORD, W.LPWSTR]
rm.RmEndSession.argtypes = [W.DWORD]
rm.RmRegisterResources.argtypes = [W.DWORD, W.UINT, ctypes.POINTER(W.LPCWSTR), W.UINT, ctypes.c_void_p, W.UINT, ctypes.c_void_p]
rm.RmGetList.argtypes = [W.DWORD, ctypes.POINTER(W.UINT), ctypes.POINTER(W.UINT), ctypes.POINTER(RM_PROCESS_INFO), ctypes.POINTER(W.DWORD)]
ERROR_MORE_DATA = 234


def _holders(paths):
    """이 파일들 중 하나라도 열어 둔 프로그램 번호들 (Restart Manager 세션 하나로 묻는다)."""
    h, key = W.DWORD(), ctypes.create_unicode_buffer(33)  # RmStartSession 이 세션 키(32자 + NUL)를 여기에 써 넣는다
    if rm.RmStartSession(ctypes.byref(h), 0, key) != 0:
        return []
    try:
        files = (W.LPCWSTR * len(paths))(*paths)
        if rm.RmRegisterResources(h, len(paths), files, 0, None, 0, None) != 0:
            return []
        need, n, reasons = W.UINT(0), W.UINT(0), W.DWORD(0)
        for _ in range(3):  # 그 사이 늘어나면 다시 받는다
            info = (RM_PROCESS_INFO * max(need.value, 1))()
            n.value = len(info)
            r = rm.RmGetList(h, ctypes.byref(need), ctypes.byref(n), info, ctypes.byref(reasons))
            if r == 0:
                return [info[i].Process.dwProcessId for i in range(n.value)]
            if r != ERROR_MORE_DATA:
                return []
        return []
    finally:
        rm.RmEndSession(h)


_HELD = set()  # 지난번에 누가 열어 두었던 파일


def held_by(paths):
    """lsof -Fpn 대신: {pid: [이 프로그램이 열어 둔 파일]} (주어진 파일 중에서만).
    파일마다 물으면 느려서(파일당 ~20ms), 지난번에 열려 있던 파일만 하나씩 다시 보고,
    나머지는 한 번에 물은 뒤 누가 잡고 있는 묶음만 반으로 나눠 좁힌다. 보통은 (열린 파일 수 + 1)번만 묻는다."""
    out, found = {}, set()

    def leaf(path):
        pids = _holders([path])
        for pid in pids:
            out.setdefault(pid, []).append(path)
        if pids:
            found.add(path)

    def probe(group):
        if not group or not _holders(group):
            return
        if len(group) == 1:
            leaf(group[0])
            return
        mid = len(group) // 2
        probe(group[:mid])
        probe(group[mid:])
    paths = list(dict.fromkeys(paths))
    for path in paths:
        if path in _HELD:
            leaf(path)
    probe([path for path in paths if path not in _HELD])
    _HELD.clear()
    _HELD.update(found)
    return out


# ---------- 창 앞으로 ----------

WNDENUMPROC = ctypes.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
u32.EnumWindows.argtypes = [WNDENUMPROC, W.LPARAM]
u32.GetWindowThreadProcessId.argtypes = [W.HWND, ctypes.POINTER(W.DWORD)]
u32.IsWindowVisible.argtypes = [W.HWND]
u32.GetWindow.restype = W.HWND
u32.GetWindow.argtypes = [W.HWND, W.UINT]
u32.GetWindowTextLengthW.argtypes = [W.HWND]
u32.IsIconic.argtypes = [W.HWND]
u32.ShowWindow.argtypes = [W.HWND, ctypes.c_int]
u32.SetForegroundWindow.argtypes = [W.HWND]
u32.keybd_event.argtypes = [W.BYTE, W.BYTE, W.DWORD, ctypes.c_size_t]
u32.GetForegroundWindow.restype = W.HWND
u32.AttachThreadInput.argtypes = [W.DWORD, W.DWORD, W.BOOL]
u32.BringWindowToTop.argtypes = [W.HWND]
k32.GetCurrentThreadId.restype = W.DWORD


def force_foreground(hwnd):
    """창을 맨 앞으로. 성공하면 True.
    보드 서버·트레이는 백그라운드 프로그램이라 Windows 가 다른 창을 앞으로 못 올리게 막는다(SetForegroundWindow 가
    성공이라 답해도 작업 표시줄만 깜빡이고 그대로일 때가 있다). 지금 맨 앞 창의 입력 줄에 잠깐 붙어서(AttachThreadInput)
    올리고, Alt 를 한 번 눌렀다 떼서(그래야 허용된다) 같이 시도한 뒤, 실제로 맨 앞이 됐는지 확인한다."""
    if u32.IsIconic(hwnd):
        u32.ShowWindow(hwnd, 9)  # SW_RESTORE
    fg = u32.GetForegroundWindow()
    mine = k32.GetCurrentThreadId()
    theirs = u32.GetWindowThreadProcessId(fg, None) if fg else 0
    attached = bool(theirs and theirs != mine and u32.AttachThreadInput(mine, theirs, True))
    try:
        u32.keybd_event(0x12, 0, 0, 0)
        u32.keybd_event(0x12, 0, 2, 0)
        u32.BringWindowToTop(hwnd)
        u32.SetForegroundWindow(hwnd)
    finally:
        if attached:
            u32.AttachThreadInput(mine, theirs, False)
    return u32.GetForegroundWindow() == hwnd


def _top_windows():
    """{pid: 그 프로그램의 첫 번째 보이는 최상위 창}"""
    out = {}

    def cb(hwnd, _):
        if u32.IsWindowVisible(hwnd) and not u32.GetWindow(hwnd, 4) and u32.GetWindowTextLengthW(hwnd):  # 4 = GW_OWNER
            pid = W.DWORD()
            u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            out.setdefault(pid.value, hwnd)
        return True
    u32.EnumWindows(WNDENUMPROC(cb), 0)
    return out


def focus(pid):
    """세션이 도는 창(가장 가까운 창 있는 조상)을 앞으로. 탭까지는 못 고른다 → 'app' 또는 ''."""
    _, hwnd = window_host(pid)
    return 'app' if hwnd and force_foreground(hwnd) else ''


def focus_desktop_app():
    """Claude 데스크톱 앱 창을 앞으로. 'app' 또는 ''."""
    for pid, hwnd in _top_windows().items():
        if is_desktop_app(exe_path(pid)):
            return 'app' if force_foreground(hwnd) else ''
    return ''


def open_claude_session(session_id):
    """Claude 앱에서 그 Code 탭 세션을 연다 (앱의 딥링크 claude://code/continue?session=<앱 세션 번호>, 예: local_…).
    앱이 claude:// 를 받지 않으면 False."""
    import winreg
    from urllib.parse import quote
    if not session_id:
        return False
    try:
        winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, 'claude'))
    except OSError:
        return False
    try:
        u32.AllowSetForegroundWindow(0xFFFFFFFF)  # 앱이 그 창을 앞으로 가져올 수 있게
        os.startfile('claude://code/continue?session=' + quote(session_id, safe=''))
        return True
    except OSError:
        return False


def focus_codex_app():
    """Codex 데스크톱 앱 창을 앞으로. 이 앱은 OpenAI.Codex 패키지 안의 ChatGPT.exe 다. 'app' 또는 ''."""
    for pid, hwnd in _top_windows().items():
        path = exe_path(pid)
        if os.path.basename(path).lower() == 'chatgpt.exe' or '\\OpenAI.Codex_' in path:
            return 'app' if force_foreground(hwnd) else ''
    return ''


# ---------- 그 밖 ----------

def lang_code():
    """시스템 표시 언어의 앞 두 글자 (ko-KR → ko)."""
    buf = ctypes.create_unicode_buffer(85)
    if k32.GetUserDefaultLocaleName(buf, 85):
        return buf.value.split('-')[0].lower()
    return ''


def self_usage():
    """(이 프로그램이 쓴 CPU 초, 메모리 MB)"""
    h = k32.GetCurrentProcess()
    c, e, k, u = W.FILETIME(), W.FILETIME(), W.FILETIME(), W.FILETIME()
    cpu = 0.0
    if k32.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(k), ctypes.byref(u)):
        cpu = (((k.dwHighDateTime << 32) | k.dwLowDateTime) + ((u.dwHighDateTime << 32) | u.dwLowDateTime)) / 1e7

    class PMC(ctypes.Structure):
        _fields_ = [('cb', W.DWORD), ('PageFaultCount', W.DWORD)] + [(n, ctypes.c_size_t) for n in (
            'PeakWorkingSetSize', 'WorkingSetSize', 'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage',
            'QuotaPeakNonPagedPoolUsage', 'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage')]
    m = PMC()
    m.cb = ctypes.sizeof(m)
    ok = k32.K32GetProcessMemoryInfo(h, ctypes.byref(m), m.cb)
    return cpu, (m.WorkingSetSize / 1048576 if ok else 0)


def npm_shim(path):
    """npm 으로 깐 CLI 는 .cmd 다. .cmd 는 줄바꿈이 든 인자(요약 지시문)를 망가뜨려서, 안의 node 스크립트를 직접 부른다."""
    if not path or not path.lower().endswith('.cmd'):
        return [path]
    try:
        with open(path, encoding='utf-8', errors='ignore') as f:
            m = re.search(r'"%dp0%\\([^"]+\.js)"', f.read())
    except OSError:
        m = None
    if not m:
        return [path]
    js = os.path.join(os.path.dirname(path), m.group(1))
    node = os.path.join(os.path.dirname(path), 'node.exe')
    import shutil
    return [node if os.path.exists(node) else (shutil.which('node') or 'node'), js]


def console_python():
    """감시 프로그램은 python.exe 로 띄운다(창은 숨김). pythonw.exe 로 띄우면 콘솔이 없어서,
    보드가 부르는 claude·codex 가 부를 때마다 검은 창을 띄운다."""
    exe = sys.executable
    if os.path.basename(exe).lower() == 'pythonw.exe':
        alt = os.path.join(os.path.dirname(exe), 'python.exe')
        if os.path.exists(alt):
            return alt
    return exe


def python_cmd():
    """감시를 띄우는 명령 앞부분. Windows 파이썬의 기본 파일 인코딩은 cp949 라서, 한글 경로·요약이 깨지지 않게 UTF-8 모드로 띄운다."""
    return [console_python(), '-X', 'utf8']


def windowed_python():
    """로그인 때 쓰는 pythonw.exe (콘솔 창을 띄우지 않는다)."""
    exe = sys.executable
    alt = os.path.join(os.path.dirname(exe), 'pythonw.exe')
    return alt if os.path.exists(alt) else exe


TRAY_CLASS = 'SpyhopTray'  # 트레이의 숨은 창 이름 (tray.py)
WM_OPEN_BOARD = 0x8000 + 2  # WM_APP + 2: 떠 있는 트레이에 「보드 창 열어」 (시작 메뉴 아이콘 · 패널의 Open full board)
u32.FindWindowW.restype = W.HWND
u32.FindWindowW.argtypes = [W.LPCWSTR, W.LPCWSTR]
u32.PostMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
u32.AllowSetForegroundWindow.argtypes = [W.DWORD]


def ask_tray_to_open_board():
    """떠 있는 트레이에게 보드 창을 열라고 전한다. 트레이가 없으면 False."""
    hwnd = u32.FindWindowW(TRAY_CLASS, None)
    if not hwnd:
        return False
    u32.AllowSetForegroundWindow(0xFFFFFFFF)  # ASFW_ANY: 방금 사용자가 누른 쪽이 앞으로 가져오기 권한을 넘겨준다
    return bool(u32.PostMessageW(hwnd, WM_OPEN_BOARD, 0, 0))


def _powershell(script):
    """PowerShell 스크립트를 돌리고 출력 줄들을 돌려준다. 한글 경로가 안 깨지게 UTF-16 으로 인코딩해 넘긴다."""
    import base64
    enc = base64.b64encode(('[Console]::OutputEncoding = [Text.Encoding]::UTF8\n' + script).encode('utf-16-le')).decode()
    r = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-EncodedCommand', enc],
                       capture_output=True, timeout=60, creationflags=CREATE_NO_WINDOW)
    if r.returncode:
        raise OSError(r.stderr.decode('utf-8', 'ignore').strip()[:300])
    return [x for x in r.stdout.decode('utf-8', 'ignore').splitlines() if x.strip()]


def _ps(s):
    return "'" + s.replace("'", "''") + "'"


def make_shortcuts(name, target, args, icon, workdir, description, places=('Programs', 'Desktop')):
    """시작 메뉴(Programs)와 바탕 화면(Desktop)에 바로가기를 만든다. places 에는 폴더 경로도 된다(시험용). 만든 경로들을 돌려준다."""
    script = ''.join(
        "$f = %s; if (-not [IO.Path]::IsPathRooted($f)) { $f = [Environment]::GetFolderPath($f) }\n"
        "$p = Join-Path $f %s\n"
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($p)\n"
        "$s.TargetPath = %s; $s.Arguments = %s; $s.IconLocation = %s; $s.WorkingDirectory = %s; $s.Description = %s\n"
        "$s.Save(); $p\n" % (_ps(place), _ps(name + '.lnk'), _ps(target), _ps(args), _ps(icon + ',0'), _ps(workdir), _ps(description))
        for place in places)
    return _powershell(script)


def remove_shortcuts(name, places=('Programs', 'Desktop')):
    """make_shortcuts 로 만든 바로가기를 지운다. 지운 경로들을 돌려준다."""
    script = ''.join(
        "$f = %s; if (-not [IO.Path]::IsPathRooted($f)) { $f = [Environment]::GetFolderPath($f) }\n"
        "$p = Join-Path $f %s\n"
        "if (Test-Path -LiteralPath $p) { Remove-Item -LiteralPath $p; $p }\n" % (_ps(place), _ps(name + '.lnk'))
        for place in places)
    return _powershell(script)


RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
RUN_NAME = 'Spyhop'


def autostart_on():
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, RUN_NAME)
            return True
    except OSError:
        return False


def set_autostart(on, board):
    """로그인 때 트레이 아이콘을 띄우고 보드도 켠다 (현재 사용자 Run 키). 끌 때는 값만 지우고 지금 돌고 있는 보드는 둔다."""
    import winreg
    tray = os.path.join(os.path.dirname(board), 'tray.py')
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
        if on:
            winreg.SetValueEx(k, RUN_NAME, 0, winreg.REG_SZ, '"%s" -X utf8 "%s" --start-board' % (windowed_python(), tray))
        else:
            try:
                winreg.DeleteValue(k, RUN_NAME)
            except OSError:
                pass


def lock(fh):
    """fcntl.flock(LOCK_EX | LOCK_NB) 대신. 이미 잠겨 있으면 OSError."""
    import msvcrt
    fh.seek(0)
    msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)


def spawn_detached(args, stdout=None, stderr=None):
    """맥의 start_new_session=True 대신: 부른 창이 닫혀도 계속 돌고, 콘솔 창은 숨긴다."""
    return subprocess.Popen(args, stdout=stdout, stderr=stderr, stdin=subprocess.DEVNULL,
                            creationflags=CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP, close_fds=True)
