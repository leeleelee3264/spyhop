"""Windows 작업 표시줄 트레이 아이콘: 맥의 메뉴바 항목(menubar/spyhop.5s.py)과 같은 일을 한다 (표준 라이브러리 ctypes 만 쓴다).

  아이콘    내 차례인 세션 수. 보드가 꺼져 있으면 회색
  왼쪽 클릭  작은 보드 패널(/panel)을 연다
  오른쪽 클릭 세션 목록. 고르면 그 세션으로 간다
  감시      Claude·Codex 가 떠 있는데 보드가 꺼져 있으면 다시 켠다

  pythonw -X utf8 tray.py                  트레이만 띄운다
  pythonw -X utf8 tray.py --open-board     보드 창을 연다 (시작 메뉴 · 바탕 화면 아이콘, spyhop.cmd). 트레이가 이미 떠 있으면 그쪽에 전달
  pythonw -X utf8 tray.py --start-board    로그인 때: 보드도 바로 켠다 (창은 열지 않는다. 맥 앱도 로그인 때는 메뉴바에만)
  python  -X utf8 tray.py --install        시작 메뉴 · 바탕 화면에 Spyhop 아이콘을 만든다
  python  -X utf8 tray.py --uninstall      그 아이콘과 로그인 자동 시작을 지운다

보드 창과 패널은 Spyhop 전용 Edge 프로필(%LOCALAPPDATA%\\Spyhop\\window)의 앱 창(주소창 없음)으로 띄운다.
평소 쓰는 Edge 와 섞이지 않고, 작업 표시줄에도 따로 보인다.
"""
import ctypes
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from ctypes import wintypes as W
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import board as B  # noqa: E402
import winplat  # noqa: E402

PORT = B.PORT
BOARD_URL = 'http://127.0.0.1:%d/' % PORT
PANEL_URL = BOARD_URL + 'panel'
TICK_MS = 3000           # 아이콘을 다시 그리는 주기
ENSURE_EVERY = 5         # 보드가 꺼졌는지 보는 주기(초)
STALE = 120              # 보드가 이만큼 상태를 안 고쳤으면 꺼진 것으로 본다
MAX_ROWS = 15

u32 = ctypes.WinDLL('user32', use_last_error=True)
k32 = ctypes.WinDLL('kernel32', use_last_error=True)
gdi = ctypes.WinDLL('gdi32')
shell32 = ctypes.WinDLL('shell32')

LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, W.HWND, W.UINT, W.WPARAM, W.LPARAM)

WM_DESTROY, WM_COMMAND, WM_TIMER, WM_NULL = 0x0002, 0x0111, 0x0113, 0x0000
WM_LBUTTONUP, WM_RBUTTONUP, WM_CONTEXTMENU = 0x0202, 0x0205, 0x007B
WM_TRAY = 0x8000 + 1  # WM_APP + 1
NIM_ADD, NIM_MODIFY, NIM_DELETE = 0, 1, 2
NIF_MESSAGE, NIF_ICON, NIF_TIP, NIF_SHOWTIP = 0x1, 0x2, 0x4, 0x80
MF_STRING, MF_SEPARATOR, MF_GRAYED, MF_POPUP = 0x0, 0x800, 0x1, 0x10
TPM_RIGHTBUTTON, TPM_RETURNCMD, TPM_NONOTIFY = 0x2, 0x100, 0x80
ERROR_ALREADY_EXISTS = 183

ID_OPEN_BOARD, ID_OPEN_PANEL, ID_START, ID_QUIT, ID_SESSION = 1, 2, 3, 4, 100


class WNDCLASSW(ctypes.Structure):
    _fields_ = [('style', W.UINT), ('lpfnWndProc', WNDPROC), ('cbClsExtra', ctypes.c_int), ('cbWndExtra', ctypes.c_int),
                ('hInstance', W.HINSTANCE), ('hIcon', W.HICON), ('hCursor', W.HANDLE), ('hbrBackground', W.HBRUSH),
                ('lpszMenuName', W.LPCWSTR), ('lpszClassName', W.LPCWSTR)]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [('cbSize', W.DWORD), ('hWnd', W.HWND), ('uID', W.UINT), ('uFlags', W.UINT), ('uCallbackMessage', W.UINT),
                ('hIcon', W.HICON), ('szTip', W.WCHAR * 128), ('dwState', W.DWORD), ('dwStateMask', W.DWORD),
                ('szInfo', W.WCHAR * 256), ('uVersion', W.UINT), ('szInfoTitle', W.WCHAR * 64), ('dwInfoFlags', W.DWORD),
                ('guidItem', ctypes.c_byte * 16), ('hBalloonIcon', W.HICON)]


class ICONINFO(ctypes.Structure):
    _fields_ = [('fIcon', W.BOOL), ('xHotspot', W.DWORD), ('yHotspot', W.DWORD), ('hbmMask', W.HBITMAP), ('hbmColor', W.HBITMAP)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [('biSize', W.DWORD), ('biWidth', W.LONG), ('biHeight', W.LONG), ('biPlanes', W.WORD), ('biBitCount', W.WORD),
                ('biCompression', W.DWORD), ('biSizeImage', W.DWORD), ('biXPelsPerMeter', W.LONG), ('biYPelsPerMeter', W.LONG),
                ('biClrUsed', W.DWORD), ('biClrImportant', W.DWORD)]


u32.DefWindowProcW.restype = LRESULT
u32.DefWindowProcW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
u32.CreateWindowExW.restype = W.HWND
u32.CreateWindowExW.argtypes = [W.DWORD, W.LPCWSTR, W.LPCWSTR, W.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                W.HWND, W.HMENU, W.HINSTANCE, W.LPVOID]
u32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
u32.RegisterWindowMessageW.argtypes = [W.LPCWSTR]
u32.CreatePopupMenu.restype = W.HMENU
u32.AppendMenuW.argtypes = [W.HMENU, W.UINT, ctypes.c_size_t, W.LPCWSTR]
u32.TrackPopupMenu.argtypes = [W.HMENU, W.UINT, ctypes.c_int, ctypes.c_int, ctypes.c_int, W.HWND, W.LPVOID]
u32.DestroyMenu.argtypes = [W.HMENU]
u32.SetForegroundWindow.argtypes = [W.HWND]
u32.PostMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
u32.GetCursorPos.argtypes = [ctypes.POINTER(W.POINT)]
u32.SetTimer.argtypes = [W.HWND, ctypes.c_size_t, W.UINT, W.LPVOID]
u32.GetMessageW.argtypes = [ctypes.POINTER(W.MSG), W.HWND, W.UINT, W.UINT]
u32.TranslateMessage.argtypes = [ctypes.POINTER(W.MSG)]
u32.DispatchMessageW.argtypes = [ctypes.POINTER(W.MSG)]
u32.DestroyIcon.argtypes = [W.HICON]
u32.CreateIconIndirect.restype = W.HICON
u32.CreateIconIndirect.argtypes = [ctypes.POINTER(ICONINFO)]
u32.GetDC.restype = W.HDC
u32.GetDC.argtypes = [W.HWND]
u32.ReleaseDC.argtypes = [W.HWND, W.HDC]
u32.FillRect.argtypes = [W.HDC, ctypes.POINTER(W.RECT), W.HBRUSH]
u32.DrawTextW.argtypes = [W.HDC, W.LPCWSTR, ctypes.c_int, ctypes.POINTER(W.RECT), W.UINT]
u32.SystemParametersInfoW.argtypes = [W.UINT, W.UINT, W.LPVOID, W.UINT]
u32.AllowSetForegroundWindow.argtypes = [W.DWORD]
u32.GetWindowTextW.argtypes = [W.HWND, W.LPWSTR, ctypes.c_int]
u32.GetWindowRect.argtypes = [W.HWND, ctypes.POINTER(W.RECT)]
u32.DestroyWindow.argtypes = [W.HWND]
u32.FindWindowW.restype = W.HWND
u32.FindWindowW.argtypes = [W.LPCWSTR, W.LPCWSTR]
u32.keybd_event.argtypes = [W.BYTE, W.BYTE, W.DWORD, ctypes.c_size_t]
u32.GetWindowPlacement.argtypes = [W.HWND, ctypes.c_void_p]
u32.MonitorFromPoint.restype = W.HMONITOR
u32.MonitorFromPoint.argtypes = [W.POINT, W.DWORD]
u32.MonitorFromRect.restype = W.HMONITOR
u32.MonitorFromRect.argtypes = [ctypes.POINTER(W.RECT), W.DWORD]
u32.GetMonitorInfoW.argtypes = [W.HMONITOR, ctypes.c_void_p]
u32.GetDpiForWindow.argtypes = [W.HWND]
u32.SetWindowPos.argtypes = [W.HWND, W.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, W.UINT]
u32.GetForegroundWindow.restype = W.HWND
u32.AttachThreadInput.argtypes = [W.DWORD, W.DWORD, W.BOOL]
u32.BringWindowToTop.argtypes = [W.HWND]
u32.IsWindow.argtypes = [W.HWND]
u32.IsWindowVisible.argtypes = [W.HWND]
u32.IsIconic.argtypes = [W.HWND]
u32.ShowWindow.argtypes = [W.HWND, ctypes.c_int]
u32.GetWindow.restype = W.HWND
u32.GetWindow.argtypes = [W.HWND, W.UINT]
u32.GetWindowThreadProcessId.argtypes = [W.HWND, ctypes.POINTER(W.DWORD)]
u32.GetSystemMetrics.argtypes = [ctypes.c_int]
gdi.GetStockObject.argtypes = [ctypes.c_int]
shell32.Shell_NotifyIconW.argtypes = [W.DWORD, ctypes.POINTER(NOTIFYICONDATAW)]
k32.CreateMutexW.restype = W.HANDLE
k32.CreateMutexW.argtypes = [W.LPVOID, W.BOOL, W.LPCWSTR]
k32.GetModuleHandleW.restype = W.HMODULE
k32.GetModuleHandleW.argtypes = [W.LPCWSTR]
gdi.CreateCompatibleDC.restype = W.HDC
gdi.CreateCompatibleDC.argtypes = [W.HDC]
gdi.CreateDIBSection.restype = W.HBITMAP
gdi.CreateDIBSection.argtypes = [W.HDC, ctypes.c_void_p, W.UINT, ctypes.POINTER(ctypes.c_void_p), W.HANDLE, W.DWORD]
gdi.CreateBitmap.restype = W.HBITMAP
gdi.CreateBitmap.argtypes = [ctypes.c_int, ctypes.c_int, W.UINT, W.UINT, W.LPVOID]
gdi.SelectObject.restype = W.HGDIOBJ
gdi.SelectObject.argtypes = [W.HDC, W.HGDIOBJ]
gdi.DeleteObject.argtypes = [W.HGDIOBJ]
gdi.DeleteDC.argtypes = [W.HDC]
gdi.CreateSolidBrush.restype = W.HBRUSH
gdi.CreateSolidBrush.argtypes = [W.COLORREF]
gdi.GetStockObject.restype = W.HGDIOBJ
gdi.RoundRect.argtypes = [W.HDC] + [ctypes.c_int] * 6
gdi.SetBkMode.argtypes = [W.HDC, ctypes.c_int]
gdi.SetTextColor.argtypes = [W.HDC, W.COLORREF]
gdi.CreateFontW.restype = W.HFONT
gdi.CreateFontW.argtypes = [ctypes.c_int] * 5 + [W.DWORD] * 8 + [W.LPCWSTR]


def rgb(r, g, b):
    return r | (g << 8) | (b << 16)


BLUE, GRAY, WHITE = rgb(0x31, 0x82, 0xf6), rgb(0x8a, 0x93, 0xa3), rgb(0xff, 0xff, 0xff)


def make_icon(text, color):
    """둥근 사각형 위에 숫자 하나. 32비트 색 그림의 투명도는 0 이라, 모서리 투명은 흑백 마스크로 낸다."""
    size = max(16, u32.GetSystemMetrics(49))  # SM_CXSMICON (DPI 를 따른다)
    screen = u32.GetDC(None)
    dc = gdi.CreateCompatibleDC(screen)
    bmi = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), size, -size, 1, 32, 0, 0, 0, 0, 0, 0)
    bits = ctypes.c_void_p()
    color_bmp = gdi.CreateDIBSection(dc, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
    mask_bmp = gdi.CreateBitmap(size, size, 1, 1, None)
    radius = max(4, size // 4)
    try:
        # 마스크: 흰색(1) = 투명, 검은 둥근 사각형(0) = 보임
        old = gdi.SelectObject(dc, mask_bmp)
        full = W.RECT(0, 0, size, size)
        u32.FillRect(dc, ctypes.byref(full), gdi.GetStockObject(0))  # WHITE_BRUSH
        gdi.SelectObject(dc, gdi.GetStockObject(4))  # BLACK_BRUSH
        gdi.RoundRect(dc, 0, 0, size, size, radius, radius)
        # 색: 둥근 사각형 + 흰 숫자
        gdi.SelectObject(dc, color_bmp)
        u32.FillRect(dc, ctypes.byref(full), gdi.GetStockObject(4))
        brush = gdi.CreateSolidBrush(color)
        gdi.SelectObject(dc, brush)
        gdi.SelectObject(dc, gdi.GetStockObject(8))  # NULL_PEN
        gdi.RoundRect(dc, 0, 0, size + 1, size + 1, radius, radius)
        font = gdi.CreateFontW(-int(size * (0.72 if len(text) < 2 else 0.58)), 0, 0, 0, 700, 0, 0, 0, 1, 0, 0, 5, 0, 'Segoe UI')
        gdi.SelectObject(dc, font)
        gdi.SetBkMode(dc, 1)  # TRANSPARENT
        gdi.SetTextColor(dc, WHITE)
        u32.DrawTextW(dc, text, -1, ctypes.byref(full), 0x1 | 0x4 | 0x20)  # CENTER | VCENTER | SINGLELINE
        gdi.SelectObject(dc, old)
        info = ICONINFO(True, 0, 0, mask_bmp, color_bmp)
        icon = u32.CreateIconIndirect(ctypes.byref(info))
        gdi.DeleteObject(font)
        gdi.DeleteObject(brush)
        return icon
    finally:
        gdi.DeleteObject(color_bmp)
        gdi.DeleteObject(mask_bmp)
        gdi.DeleteDC(dc)
        u32.ReleaseDC(None, screen)


def read_state():
    """(보드가 살아 있나, 세션 목록). 보드가 STALE 초 넘게 상태를 안 고쳤으면 꺼진 것."""
    try:
        with open(B.STATE, encoding='utf-8') as f:
            state = json.load(f)
    except (OSError, ValueError):
        return False, []
    if time.time() - state.get('at', 0) > STALE:
        return False, []
    return True, state.get('sessions') or []


def waited(sec):
    sec = max(0, int(time.time() - (sec or time.time())))
    return 'now' if sec < 60 else '%dm' % (sec // 60) if sec < 3600 else '%dh' % (sec // 3600) if sec < 86400 else '%dd' % (sec // 86400)


def ensure_board():
    """Claude·Codex 가 떠 있는데 보드가 꺼져 있으면 다시 켠다 (맥 메뉴바 플러그인과 같은 일)."""
    try:
        if not B.watching() and B.agent_pids():
            winplat.spawn_detached(winplat.python_cmd() + [os.path.join(HERE, 'board.py'), '--ensure'],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:  # 트레이는 계속 떠 있어야 한다
        sys.stderr.write('tray ensure: %s\n' % e)


def start_board():
    winplat.spawn_detached(winplat.python_cmd() + [os.path.join(HERE, 'board.py'), '--ensure'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def edge():
    for p in (shutil.which('msedge'),
              os.path.join(os.environ.get('ProgramFiles(x86)', ''), 'Microsoft', 'Edge', 'Application', 'msedge.exe'),
              os.path.join(os.environ.get('ProgramFiles', ''), 'Microsoft', 'Edge', 'Application', 'msedge.exe')):
        if p and os.path.exists(p):
            return p
    return None


# 보드 창 · 패널은 Spyhop 전용 Edge 프로필로 띄운다. 평소 Edge 와 섞이지 않고, 이 프로필의 창만 골라 다시 쓸 수 있다
APP_PROFILE = os.path.join(os.environ.get('LOCALAPPDATA') or os.path.expanduser('~'), 'Spyhop', 'window')
BOARD_SIZE = (1280, 860)
PANEL_SIZE = (380, 560)
WM_OPEN_BOARD = winplat.WM_OPEN_BOARD


def edge_windows():
    """Spyhop 전용 프로필로 뜬 Edge 최상위 창들. Edge 는 창 여러 개를 한 프로그램이 다 가지고 있어서 창마다 센다."""
    out, ours = [], {}
    key = APP_PROFILE.lower()

    def cb(hwnd, _):
        if u32.IsWindowVisible(hwnd) and not u32.GetWindow(hwnd, 4):  # 4 = GW_OWNER
            pid = W.DWORD()
            u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value not in ours:
                ours[pid.value] = (os.path.basename(winplat.exe_path(pid.value)).lower() == 'msedge.exe'
                                   and key in winplat.command_line(pid.value).lower())
            if ours[pid.value]:
                out.append(hwnd)
        return True
    u32.EnumWindows(winplat.WNDENUMPROC(cb), 0)
    return out


def alive(hwnd):
    return bool(hwnd) and bool(u32.IsWindow(hwnd)) and bool(u32.IsWindowVisible(hwnd))


class WINDOWPLACEMENT(ctypes.Structure):
    _fields_ = [('length', W.UINT), ('flags', W.UINT), ('showCmd', W.UINT), ('ptMinPosition', W.POINT),
                ('ptMaxPosition', W.POINT), ('rcNormalPosition', W.RECT)]


class MONITORINFO(ctypes.Structure):
    _fields_ = [('cbSize', W.DWORD), ('rcMonitor', W.RECT), ('rcWork', W.RECT), ('dwFlags', W.DWORD)]


def normal_rect(hwnd):
    """최소화·최대화 전의 창 자리. 최소화된 창은 GetWindowRect 가 (-32000, -32000) 의 좁은 칸을 돌려줘서 패널로 잘못 본다."""
    wp = WINDOWPLACEMENT()
    wp.length = ctypes.sizeof(wp)
    u32.GetWindowPlacement(hwnd, ctypes.byref(wp))
    return wp.rcNormalPosition


def window_width(hwnd):
    r = normal_rect(hwnd)
    return r.right - r.left


def work_area():
    """마우스가 있는 화면(=방금 누른 트레이·시작 메뉴가 있는 화면)의 작업 영역. 실제 픽셀."""
    pt = W.POINT()
    u32.GetCursorPos(ctypes.byref(pt))
    mon = u32.MonitorFromPoint(pt, 2)  # MONITOR_DEFAULTTONEAREST
    mi = MONITORINFO()
    mi.cbSize = ctypes.sizeof(mi)
    u32.GetMonitorInfoW(mon, ctypes.byref(mi))
    return mi.rcWork


def scaled(hwnd, size):
    """Edge 가 쓰는 단위(배율 적용 전)의 크기를 그 창 화면의 실제 픽셀로. 배율 150% 면 380 → 570."""
    dpi = u32.GetDpiForWindow(hwnd) or 96
    return tuple(int(v * dpi / 96) for v in size)


def panel_rect(hwnd):
    w, h = scaled(hwnd, PANEL_SIZE)
    work, gap = work_area(), scaled(hwnd, (12, 12))[0]
    return work.right - w - gap, work.bottom - h - gap, w, h


def board_rect(hwnd):
    w, h = scaled(hwnd, BOARD_SIZE)
    work = work_area()
    w, h = min(w, int((work.right - work.left) * .92)), min(h, int((work.bottom - work.top) * .92))
    return work.left + (work.right - work.left - w) // 2, work.top + (work.bottom - work.top - h) // 2, w, h


PANEL_TITLE = 'Spyhop panel'  # panel.html 의 <title>. 보드는 'Spyhop'


def window_title(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    u32.GetWindowTextW(hwnd, buf, 256)
    return buf.value


def is_panel(hwnd):
    """패널 창인가. 페이지를 다 읽기 전에는 제목 자리에 주소가 보인다."""
    t = window_title(hwnd)
    return t == PANEL_TITLE or '/panel' in t


def too_small(hwnd):
    """보드 창이 보드로 쓰기에 너무 작은가 (보드 크기의 절반 폭보다 좁다)."""
    return window_width(hwnd) < scaled(hwnd, (BOARD_SIZE[0] // 2, 0))[0]


def off_screen(hwnd):
    r = normal_rect(hwnd)
    return not u32.MonitorFromRect(ctypes.byref(r), 0)  # MONITOR_DEFAULTTONULL: 어느 화면에도 안 걸친다


def bring_front(hwnd, rect=None):
    """창을 보이게 하고 맨 앞으로. rect=(x, y, w, h, 실제 픽셀)를 주면 그 자리로 옮긴다.
    트레이는 백그라운드 프로그램이라 Windows 가 다른 창을 앞으로 올리지 못하게 막는다. 지금 맨 앞 창의 입력 줄에
    잠깐 붙어서(AttachThreadInput) 올리고, Alt 를 한 번 눌렀다 떼서(그래야 허용된다) 한 번 더 시도한다."""
    if u32.IsIconic(hwnd):
        u32.ShowWindow(hwnd, 9)  # SW_RESTORE
    else:
        u32.ShowWindow(hwnd, 5)  # SW_SHOW
    if rect:
        u32.SetWindowPos(hwnd, None, rect[0], rect[1], rect[2], rect[3], 0x0004 | 0x0010)  # NOZORDER | NOACTIVATE
    fg = u32.GetForegroundWindow()
    mine, theirs = k32.GetCurrentThreadId(), u32.GetWindowThreadProcessId(fg, None) if fg else 0
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


def launch_window(url, size):
    """전용 프로필의 앱 창(주소창 없음)을 연다. 새로 생긴 창(없으면 None)을 돌려준다. Edge 가 없으면 기본 브라우저로.
    자리는 띄운 뒤 트레이가 실제 픽셀로 옮긴다: Edge 의 --window-position 은 배율 적용 전 단위라, 실제 픽셀을 넘기면
    배율 150% 화면에서 1.5배 오른쪽, 즉 화면 밖에 뜬다(실제로 겪음)."""
    exe = edge()
    if not exe:
        os.startfile(url)
        return None
    os.makedirs(APP_PROFILE, exist_ok=True)
    before = set(edge_windows())
    u32.AllowSetForegroundWindow(0xFFFFFFFF)  # ASFW_ANY: 새 창이 앞으로 나올 수 있게
    subprocess.Popen([exe, '--user-data-dir=' + APP_PROFILE, '--no-first-run', '--no-default-browser-check',
                      '--app=' + url, '--window-size=%d,%d' % size], creationflags=winplat.CREATE_NO_WINDOW)
    for _ in range(60):  # 창이 뜰 때까지 최대 6초 (전용 프로필을 처음 만들 때 조금 걸린다)
        time.sleep(.1)
        new = [x for x in edge_windows() if x not in before]
        if new:
            time.sleep(.3)  # Edge 가 지난번 자리를 먼저 되살린 뒤에 옮긴다
            return new[0]
    return None


def server_up(timeout=0.3):
    import socket
    try:
        socket.create_connection(('127.0.0.1', PORT), timeout=timeout).close()
        return True
    except OSError:
        return False


ask_tray_to_open_board = winplat.ask_tray_to_open_board


def go(handle):
    """보드에게 그 세션으로 가 달라고 한다. 방금 사용자가 누른 트레이가 앞으로 가져오기 권한을 보드에 넘겨준다."""
    u32.AllowSetForegroundWindow(0xFFFFFFFF)  # ASFW_ANY
    try:
        urllib.request.urlopen(BOARD_URL + 'switch?h=' + quote(handle, safe=''), timeout=8).read()
    except OSError:
        pass


class Tray:
    def __init__(self):
        self.nid = None  # 창을 만드는 동안 오는 메시지가 아래 값들을 찾지 않게 먼저 둔다
        self.hinst = k32.GetModuleHandleW(None)
        self.proc = WNDPROC(self.wndproc)  # 참조를 붙들어 둔다 (안 그러면 콜백이 사라진다)
        wc = WNDCLASSW(0, self.proc, 0, 0, self.hinst, None, None, None, None, 'SpyhopTray')
        u32.RegisterClassW(ctypes.byref(wc))
        self.taskbar_created = u32.RegisterWindowMessageW('TaskbarCreated')  # 탐색기가 다시 뜨면 아이콘을 다시 단다
        self.hwnd = u32.CreateWindowExW(0, 'SpyhopTray', 'Spyhop', 0, 0, 0, 0, 0, None, None, self.hinst, None)
        self.icon = None
        self.key = None
        self.sessions = []
        self.ensured = 0
        self.panel = None  # 트레이가 연 패널 창. 다시 누르면 새로 열지 않고 이 창을 앞으로
        self.board = None  # 트레이가 연 보드 창. 마찬가지
        self.nid = NOTIFYICONDATAW()
        self.nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        self.nid.hWnd = self.hwnd
        self.nid.uID = 1
        self.nid.uCallbackMessage = WM_TRAY
        self.refresh(add=True)
        u32.SetTimer(self.hwnd, 1, TICK_MS, None)

    def refresh(self, add=False):
        if time.time() - self.ensured > ENSURE_EVERY:
            self.ensured = time.time()
            ensure_board()
        up, ss = read_state()
        self.sessions = ss
        wait = sum(1 for s in ss if s.get('status') == 'wait')
        busy = sum(1 for s in ss if s.get('status') == 'busy')
        text = (str(wait) if wait < 100 else '99') if wait else '·'
        color = BLUE if up else GRAY
        tip = ('Spyhop · My turn %d · Working %d' % (wait, busy)) if up else 'Spyhop · board is off'
        key = (text, color, tip)
        if key == self.key and not add:
            return
        old, self.icon, self.key = self.icon, make_icon(text, color), key
        self.nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP | NIF_SHOWTIP
        self.nid.hIcon = self.icon
        self.nid.szTip = tip[:127]
        if not shell32.Shell_NotifyIconW(NIM_ADD if add else NIM_MODIFY, ctypes.byref(self.nid)):
            sys.stderr.write('tray: could not %s the icon\n' % ('add' if add else 'update'))
        if old:
            u32.DestroyIcon(old)

    def find(self, attr, panel):
        """기억한 창이 살아 있으면 그것, 아니면(트레이를 다시 띄운 경우) 전용 프로필 창 중 제목으로 고른 것.
        크기로 고르면 안 된다: 배율 150% 에서 패널은 570px 이고, 작게 뜬 보드 창도 그만할 수 있다(실제로 헷갈렸다)."""
        hwnd = getattr(self, attr)
        if alive(hwnd):
            return hwnd
        hwnd = next((x for x in edge_windows() if is_panel(x) == panel), None)
        setattr(self, attr, hwnd)
        return hwnd

    def open_panel(self):
        """작은 보드 패널을 오른쪽 아래(트레이 옆)에. 이미 열려 있으면 그 자리로 앞으로."""
        hwnd = self.find('panel', panel=True) or launch_window(PANEL_URL, PANEL_SIZE)
        self.panel = hwnd
        if hwnd:
            bring_front(hwnd, panel_rect(hwnd))

    def open_board(self):
        """보드 창을 연다. 이미 열려 있으면 앞으로. 보드가 꺼져 있으면 켜고 뜰 때까지 기다린다 (사람이 보드를 열면 켠다, 맥 앱과 같게).
        새로 연 창은 늘 보드 크기로 맞춘다(Edge 는 같은 프로필의 앱 창 크기를 되살려서 패널만 하게 뜰 수 있다).
        이미 열린 창은 사용자가 정한 크기를 두되, 화면 밖이거나 너무 작으면 맞춘다."""
        hwnd = self.find('board', panel=False)
        if hwnd:
            bring_front(hwnd, board_rect(hwnd) if off_screen(hwnd) or too_small(hwnd) else None)
            return
        if not server_up():
            start_board()
            for _ in range(50):  # 최대 10초
                if server_up():
                    break
                time.sleep(.2)
        hwnd = self.board = launch_window(BOARD_URL, BOARD_SIZE)
        if hwnd:
            bring_front(hwnd, board_rect(hwnd))

    def menu(self):
        up, ss = read_state()
        m = u32.CreatePopupMenu()
        if up:
            wait = [s for s in ss if s.get('status') == 'wait']
            u32.AppendMenuW(m, MF_STRING | MF_GRAYED, 0, 'My turn %d · Working %d' % (len(wait), len(ss) - len(wait)))
            u32.AppendMenuW(m, MF_SEPARATOR, 0, None)
            for i, s in enumerate(ss[:MAX_ROWS]):
                title = (s.get('title') or 'Session').replace('&', '&&').replace('\n', ' ')
                if len(title) > 40:
                    title = title[:39] + '…'
                mark = '●' if s.get('status') == 'wait' else '○'
                prog = '%d/%d' % (s['done'], s['total']) if s.get('total') else '—'
                u32.AppendMenuW(m, MF_STRING, ID_SESSION + i, '%s  %s\t%s · %s' % (mark, title, prog, waited(s.get('since'))))
            if len(ss) > MAX_ROWS:
                u32.AppendMenuW(m, MF_STRING | MF_GRAYED, 0, '… %d more on the board' % (len(ss) - MAX_ROWS))
            if not ss:
                u32.AppendMenuW(m, MF_STRING | MF_GRAYED, 0, 'No AI sessions open')
            u32.AppendMenuW(m, MF_SEPARATOR, 0, None)
            u32.AppendMenuW(m, MF_STRING, ID_OPEN_PANEL, 'Open panel')
            u32.AppendMenuW(m, MF_STRING, ID_OPEN_BOARD, 'Open full board')
        else:
            u32.AppendMenuW(m, MF_STRING | MF_GRAYED, 0, 'Board is off · starts when Claude or Codex runs')
            u32.AppendMenuW(m, MF_STRING, ID_START, 'Start the board now')
            u32.AppendMenuW(m, MF_STRING, ID_OPEN_BOARD, 'Open board')
        u32.AppendMenuW(m, MF_SEPARATOR, 0, None)
        u32.AppendMenuW(m, MF_STRING, ID_QUIT, 'Hide tray icon')
        pt = W.POINT()
        u32.GetCursorPos(ctypes.byref(pt))
        u32.SetForegroundWindow(self.hwnd)  # 이렇게 해야 바깥을 누르면 메뉴가 닫힌다
        cmd = u32.TrackPopupMenu(m, TPM_RIGHTBUTTON | TPM_RETURNCMD | TPM_NONOTIFY, pt.x, pt.y, 0, self.hwnd, None)
        u32.PostMessageW(self.hwnd, WM_NULL, 0, 0)
        u32.DestroyMenu(m)
        if cmd >= ID_SESSION and cmd - ID_SESSION < len(ss):
            go(ss[cmd - ID_SESSION]['handle'])
        elif cmd == ID_OPEN_PANEL:
            self.open_panel()
        elif cmd == ID_OPEN_BOARD:
            self.open_board()
        elif cmd == ID_START:
            start_board()
        elif cmd == ID_QUIT:
            u32.DestroyWindow(self.hwnd)

    def wndproc(self, hwnd, msg, wp, lp):
        try:
            if msg == WM_TRAY:
                if lp == WM_LBUTTONUP:
                    if read_state()[0]:
                        self.open_panel()
                    else:
                        self.menu()
                elif lp in (WM_RBUTTONUP, WM_CONTEXTMENU):
                    self.menu()
                return 0
            if msg == WM_TIMER:
                self.refresh()
                return 0
            if msg == WM_OPEN_BOARD:
                self.open_board()
                return 0
            if msg == self.taskbar_created:
                self.refresh(add=True)
                return 0
            if msg == WM_DESTROY:
                shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self.nid))
                u32.PostQuitMessage(0)
                return 0
        except Exception as e:  # 콜백에서 예외가 새면 트레이가 멈춘다
            sys.stderr.write('tray: %s\n' % e)
            return 0
        return u32.DefWindowProcW(hwnd, msg, wp, lp)

    def run(self):
        msg = W.MSG()
        while u32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            u32.TranslateMessage(ctypes.byref(msg))
            u32.DispatchMessageW(ctypes.byref(msg))


def install():
    """시작 메뉴 · 바탕 화면에 Spyhop 아이콘. 누르면 보드 창이 뜬다 (트레이도 같이)."""
    made = winplat.make_shortcuts('Spyhop', winplat.windowed_python(),
                                  '-X utf8 "%s" --open-board' % os.path.join(HERE, 'tray.py'),
                                  os.path.join(HERE, 'spyhop.ico'), HERE,
                                  'Every AI coding session on one board')
    for p in made:
        print('made: %s' % p)


def uninstall():
    for p in winplat.remove_shortcuts('Spyhop'):
        print('removed: %s' % p)
    B.set_autostart(False)
    print('Start at login: off')


def main():
    if '--install' in sys.argv:
        return install()
    if '--uninstall' in sys.argv:
        return uninstall()
    try:
        u32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))  # PER_MONITOR_AWARE_V2: 아이콘이 흐리지 않게
    except (AttributeError, OSError):
        pass
    # 트레이는 하나만 (아이콘을 여러 번 눌러도). 이미 떠 있으면 보드 창 열기만 그쪽에 전하고 끝낸다
    k32.CreateMutexW(None, False, 'Local\\SpyhopTray')
    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        if '--open-board' in sys.argv:
            for _ in range(30):  # 막 뜨는 중인 트레이면 창이 생길 때까지 잠깐 기다린다
                if ask_tray_to_open_board():
                    break
                time.sleep(.1)
        return
    if '--start-board' in sys.argv and not B.watching():
        start_board()
    tray = Tray()
    if '--open-board' in sys.argv:
        u32.PostMessageW(tray.hwnd, WM_OPEN_BOARD, 0, 0)  # 트레이를 띄운 뒤 메시지 처리 중에 연다
    tray.run()


if __name__ == '__main__':
    main()
