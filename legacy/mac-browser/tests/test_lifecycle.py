"""감시 재시작이 다른 프로세스를 끝내지 않는지 실제 자식 프로세스로 확인한다."""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import board as B


class WatcherIdentityTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='spyhop-identity-')
        self.root = Path(self.tmp.name)
        self.script = self.root / 'board.py'
        self.script.write_text('import time\ntime.sleep(60)\n')
        self.pidfile = self.root / 'watch.pid'
        self.processes = []
        self.paths = patch.multiple(B, PIDFILE=str(self.pidfile), UPDATE_FILE=str(self.root / 'update.json'))
        self.paths.start()

    def tearDown(self):
        for p in self.processes:
            if p.poll() is None:
                p.terminate()
            p.wait(timeout=5)
        self.paths.stop()
        self.tmp.cleanup()

    def start(self, argv=None):
        p = subprocess.Popen(argv or [sys.executable, str(self.script), '--watch'])
        self.processes.append(p)
        self.pidfile.write_text('%d %s' % (p.pid, self.script))
        for _ in range(100):
            record = B.watcher_record()
            if record:
                return p, record
            time.sleep(.01)
        return p, None

    def test_live_legacy_board_is_recognized(self):
        p, record = self.start()
        self.assertIsNotNone(record)
        self.assertEqual(record[0], p.pid)
        self.assertTrue(B.watching())

    def test_path_with_spaces_is_recognized(self):
        spaced = self.root / 'My Apps' / 'Spyhop 2.app' / 'board.py'
        spaced.parent.mkdir(parents=True)
        spaced.write_text(self.script.read_text())
        self.script = spaced
        p, record = self.start()
        self.assertIsNotNone(record)
        self.pidfile.write_text('%d %s %s' % (p.pid, spaced, record[2]))
        self.assertEqual(B.watcher_record()[1], str(spaced))

    def test_matching_birth_is_recognized_but_reused_birth_is_not(self):
        p, record = self.start()
        self.assertIsNotNone(record)
        self.pidfile.write_text('%d %s %s' % (p.pid, self.script, record[2]))
        self.assertTrue(B.watching())
        self.pidfile.write_text('%d %s %s' % (p.pid, self.script, record[2] - 1))
        B.stop_if_outdated()
        self.assertFalse(B.watching())
        self.assertIsNone(p.poll())

    def test_board_started_through_symlink_is_recognized(self):
        alias = self.root / 'alias.py'
        alias.symlink_to(self.script)
        _, record = self.start([sys.executable, str(alias), '--watch'])
        self.assertIsNotNone(record)

    def test_running_brew_opt_board_survives_link_retarget_and_can_be_replaced(self):
        old = self.root / 'brew/Cellar/spyhop/0.5.0/libexec/board.py'
        new = self.root / 'brew/Cellar/spyhop/0.6.0/libexec/board.py'
        for path in (old, new):
            path.parent.mkdir(parents=True)
            path.write_bytes(self.script.read_bytes())
        opt = self.root / 'brew/opt/spyhop'
        opt.parent.mkdir(parents=True)
        opt.symlink_to(old.parent.parent)
        p = subprocess.Popen([sys.executable, str(opt / 'libexec/board.py'), '--watch'])
        self.processes.append(p)
        self.pidfile.write_text('%d %s' % (p.pid, old))
        for _ in range(100):
            record = B.watcher_record()
            if record:
                break
            time.sleep(.01)
        self.assertIsNotNone(record)
        opt.unlink()
        opt.symlink_to(new.parent.parent)
        self.assertTrue(B.watching())  # 0.5.0의 두 항목 기록
        self.pidfile.write_text('%d %s %s' % (p.pid, old, record[2]))
        self.assertTrue(B.watching())  # 새 형식의 시작 시각도 그대로 검증
        threading.Thread(target=p.wait, daemon=True).start()
        B.stop_if_outdated()
        self.assertEqual(p.wait(timeout=5), -15)

    def test_retargeted_arbitrary_symlink_is_not_trusted(self):
        alias = self.root / 'alias.py'
        alias.symlink_to(self.script)
        p, record = self.start([sys.executable, str(alias), '--watch'])
        self.assertIsNotNone(record)
        other = self.root / 'other.py'
        other.write_bytes(self.script.read_bytes())
        alias.unlink()
        alias.symlink_to(other)
        B.stop_if_outdated()
        self.assertFalse(B.watching())
        self.assertIsNone(p.poll())

    def test_unrelated_live_pid_is_not_signalled(self):
        p = subprocess.Popen(['/bin/sleep', '60'])
        self.processes.append(p)
        self.pidfile.write_text('%d %s' % (p.pid, self.script))
        self.assertFalse(B.watching())
        B.stop_if_outdated()
        self.assertIsNone(p.poll())

    def test_python_without_watch_argument_is_not_signalled(self):
        p, _ = self.start([sys.executable, str(self.script)])
        B.stop_if_outdated()
        self.assertFalse(B.watching())
        self.assertIsNone(p.poll())

    def test_real_old_board_is_stopped(self):
        p, record = self.start()
        self.assertIsNotNone(record)
        threading.Thread(target=p.wait, daemon=True).start()
        B.stop_if_outdated()
        self.assertEqual(p.wait(timeout=5), -15)

    def test_brew_and_app_do_not_stop_each_other(self):
        app = self.root / 'Spyhop.app/Contents/Resources/spyhop/board.py'
        app.parent.mkdir(parents=True)
        app.write_text(self.script.read_text())
        self.script = app
        p, record = self.start()
        self.assertIsNotNone(record)
        with patch.object(B, 'ME', '/opt/homebrew/Cellar/spyhop/9.9.9/libexec/board.py'):
            B.stop_if_outdated()
        self.assertIsNone(p.poll())

    def test_missing_and_invalid_records_are_ignored(self):
        self.assertFalse(B.watching())
        for value in ('', 'not-a-pid', '-1 /fake/board.py', '1 /fake/board.py bad'):
            self.pidfile.write_text(value)
            B.stop_if_outdated()
            self.assertFalse(B.watching(), value)


class UpdateRecoveryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='spyhop-update-')
        self.journal = Path(self.tmp.name) / 'update.json'
        self.paths = patch.multiple(B, UPDATE_FILE=str(self.journal), VERSION='0.6.0')
        self.paths.start()

    def tearDown(self):
        self.paths.stop()
        self.tmp.cleanup()

    def test_invalid_journal_does_not_break_version_rendering(self):
        good = dict(to='0.6.0', **{'from': '0.5.0'}, at=time.time(), seen=False)
        for value in ([], None, 'text', {}, dict(good, at='bad'), dict(good, at=True),
                      dict(good, at=float('nan')), dict(good, at=float('inf')),
                      dict(good, at=10 ** 1000), dict(good, at=-1), dict(good, seen=[])):
            self.journal.write_text(json.dumps(value))
            self.assertEqual(B.load_update(), {})
            self.assertNotIn('ver new', B.version_badge())
        self.journal.write_text('{')
        self.assertNotIn('ver new', B.version_badge())

    def test_valid_unseen_update_highlights_until_seen_or_expired(self):
        good = dict(to='0.6.0', **{'from': '0.5.0'}, at=time.time(), seen=False)
        self.journal.write_text(json.dumps(good))
        self.assertIn('ver new', B.version_badge())
        for value in (dict(good, seen=True), dict(good, at=time.time() - 86401)):
            self.journal.write_text(json.dumps(value))
            self.assertNotIn('ver new', B.version_badge())

    def test_same_target_is_retried_at_next_watch_check(self):
        with patch.object(B, 'installed_board', return_value='/new/board.py'), patch.object(B.subprocess, 'Popen') as start:
            B.switch_if_upgraded()
            B.switch_if_upgraded()
            self.assertEqual(start.call_count, 2)

    def test_failed_spawn_does_not_stop_old_board_or_block_next_check(self):
        with patch.object(B, 'installed_board', return_value='/new/board.py'), patch.object(B.subprocess, 'Popen', side_effect=[OSError('QA failure'), object()]) as start:
            B.switch_if_upgraded()
            B.switch_if_upgraded()
            self.assertEqual(start.call_count, 2)


if __name__ == '__main__':
    unittest.main()
