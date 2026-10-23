"""Windows 에서 ps · lsof 대신 쓰는 것들(winplat)을 실제 자식 프로세스로 확인한다. 맥에서는 건너뛴다."""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import board as B

if B.WIN:
    import winplat as W

HOLD = 'import sys, time\nf = open(sys.argv[1])\nprint("ready", flush=True)\ntime.sleep(60)\n'


@unittest.skipUnless(B.WIN, 'Windows only')
class WinPlatTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='spyhop win ')  # 경로에 빈칸이 있어도 되는지 같이 본다
        self.root = Path(self.tmp.name)
        self.children = []

    def tearDown(self):
        for p in self.children:
            if p.poll() is None:
                p.kill()
            p.wait(timeout=5)
        self.tmp.cleanup()

    def hold(self, path):
        """path 를 열어 둔 채 기다리는 자식 프로세스."""
        p = subprocess.Popen([sys.executable, '-c', HOLD, str(path)], stdout=subprocess.PIPE, text=True)
        self.children.append(p)
        self.assertEqual(p.stdout.readline().strip(), 'ready')
        return p

    def test_alive_does_not_signal(self):
        p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
        self.children.append(p)
        self.assertTrue(W.alive(p.pid))
        B.check_alive(p.pid)  # os.kill(pid, 0) 과 달리 Ctrl+C 를 보내지 않는다
        time.sleep(.3)
        self.assertIsNone(p.poll())
        p.kill()
        p.wait(timeout=5)
        self.assertFalse(W.alive(p.pid))
        with self.assertRaises(ProcessLookupError):
            B.check_alive(p.pid)
        self.assertFalse(W.alive(0))
        self.assertFalse(W.alive('not-a-pid'))

    def test_start_time_and_argv_with_spaces(self):
        script = self.root / 'board.py'
        script.write_text('import time\ntime.sleep(60)\n')
        p = subprocess.Popen([sys.executable, str(script), '--watch'])
        self.children.append(p)
        self.assertLess(abs(W.start_time(p.pid) - time.time()), 30)
        argv = W.argv(p.pid)
        self.assertEqual(argv[-2:], [str(script), '--watch'])
        self.assertEqual(Path(argv[0]).name.lower(), Path(sys.executable).name.lower())

    def test_held_by_finds_the_holder_and_forgets_it(self):
        files = [self.root / ('rollout-%d.jsonl' % i) for i in range(9)]
        for f in files:
            f.write_text('{}\n')
        p = self.hold(files[5])
        paths = [str(f) for f in files]
        for _ in range(2):  # 두 번째는 지난번에 열려 있던 파일부터 본다
            self.assertEqual(W.held_by(paths), {p.pid: [str(files[5])]})
        p.kill()
        p.wait(timeout=5)
        self.assertEqual(W.held_by(paths), {})

    def test_cwd_of_child(self):
        p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], cwd=str(self.root))
        self.children.append(p)
        time.sleep(.3)
        self.assertEqual(os.path.normcase(W.cwd_of(p.pid)), os.path.normcase(str(self.root)))

    def test_claude_desktop_app_is_not_a_session(self):
        app = self.root / 'Claude' / 'app'
        (app / 'resources').mkdir(parents=True)
        (app / 'resources' / 'app.asar').write_text('')
        cli = self.root / 'claude-code' / '2.1.0'
        cli.mkdir(parents=True)
        self.assertIsNone(B.proc_kind(str(app / 'claude.exe')))
        self.assertEqual(B.proc_kind(str(cli / 'claude.exe')), 'claude')
        self.assertEqual(B.proc_kind(r'C:\x\vendor\bin\codex.exe'), 'codex')
        # 실행 중에 자동 업데이트된 claude: 돌고 있는 파일 이름이 claude.exe.old.<시각> 으로 바뀐다
        self.assertEqual(B.proc_kind(str(cli / 'claude.exe.old.1792550068234')), 'claude')
        self.assertIsNone(B.proc_kind(r'C:\Windows\System32\cmd.exe'))

    def test_npm_shim_calls_the_node_script(self):
        npm = self.root / 'npm'
        npm.mkdir()
        cmd = npm / 'codex.cmd'
        cmd.write_text('@ECHO off\r\n"%_prog%"  "%dp0%\\node_modules\\@openai\\codex\\bin\\codex.js" %*\r\n')
        shim = W.npm_shim(str(cmd))
        self.assertEqual(shim[1], str(npm / 'node_modules' / '@openai' / 'codex' / 'bin' / 'codex.js'))
        self.assertEqual(W.npm_shim(r'C:\bin\claude.exe'), [r'C:\bin\claude.exe'])

    def test_tray_icon_and_state(self):
        import tray as T
        for text in ('·', '3', '99'):
            icon = T.make_icon(text, T.BLUE)
            self.assertTrue(icon, text)
            T.u32.DestroyIcon(icon)
        state = self.root / 'state.json'
        old = B.STATE
        try:
            B.STATE = str(state)
            self.assertEqual(T.read_state(), (False, []))  # 상태 파일이 없으면 보드가 꺼진 것
            sessions = [{'handle': 'proc_1', 'status': 'wait'}, {'handle': 'proc_2', 'status': 'busy'}]
            state.write_text(json.dumps({'at': time.time(), 'sessions': sessions}), encoding='utf-8')
            self.assertEqual(T.read_state(), (True, sessions))
            state.write_text(json.dumps({'at': time.time() - T.STALE - 5, 'sessions': sessions}), encoding='utf-8')
            self.assertEqual(T.read_state(), (False, []))  # 오래 안 고친 상태는 꺼진 보드
        finally:
            B.STATE = old
        self.assertEqual(T.waited(time.time()), 'now')
        self.assertEqual(T.waited(time.time() - 300), '5m')

    def test_app_icon_is_built_from_the_mac_icon(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
        import make_icon
        out = self.root / 'spyhop.ico'
        sizes = make_icon.build(ico_path=str(out))
        self.assertEqual(sizes, [16, 32, 64, 128, 256])
        data = out.read_bytes()
        self.assertEqual(data[:6], b'\x00\x00\x01\x00\x05\x00')  # ICO, 이미지 5개
        self.assertEqual(data[6], 16)  # 첫 항목은 16px
        # 저장소에 들어 있는 아이콘이 맥 아이콘에서 다시 만든 것과 같아야 한다 (맥 아이콘이 바뀌면 다시 만들 것)
        self.assertEqual((Path(__file__).resolve().parents[1] / 'spyhop.ico').read_bytes(), data)

    def test_shortcuts_are_made_and_removed(self):
        folder = str(self.root / 'menu')
        os.makedirs(folder)
        made = W.make_shortcuts('Spyhop Test', sys.executable, '-c "pass"', str(self.root / 'x.ico'), str(self.root),
                                'test', places=(folder,))
        self.assertEqual([os.path.normcase(p) for p in made], [os.path.normcase(os.path.join(folder, 'Spyhop Test.lnk'))])
        self.assertTrue(os.path.exists(made[0]))
        self.assertEqual(len(W.remove_shortcuts('Spyhop Test', places=(folder,))), 1)
        self.assertFalse(os.path.exists(made[0]))

    def test_app_window_uses_its_own_edge_profile(self):
        import tray as T
        self.assertTrue(T.APP_PROFILE.lower().startswith(os.environ['LOCALAPPDATA'].lower()))
        self.assertIsInstance(T.edge_windows(), list)  # 평소 Edge 창은 세지 않는다
        self.assertEqual(T.WM_OPEN_BOARD, W.WM_OPEN_BOARD)

    def test_process_rows_include_this_python(self):
        rows = {r[0]: r for r in W.process_rows()}
        self.assertIn(os.getpid(), rows)
        self.assertEqual(rows[os.getpid()][1], os.getppid())


if __name__ == '__main__':
    unittest.main()
