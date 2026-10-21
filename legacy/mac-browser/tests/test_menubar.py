"""메뉴바 자동 시작과 보드의 세션 감지 기준을 일치시킨다."""
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import mock_open, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import board as B

spec = importlib.util.spec_from_file_location('spyhop_menu', ROOT / 'menubar' / 'spyhop.5s.py')
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


class MenubarDetectionTest(unittest.TestCase):
    def test_registered_omp_wakes_board_but_unregistered_bun_does_not(self):
        rows = [(42, 1, 'ttys001', 123, '/bin/bun')]
        with patch.object(B, '_agent_rows', return_value=rows), patch.object(B, 'omp_sessions', return_value={42: {'start': 123}}):
            self.assertTrue(M.agents_running())
        with patch.object(B, '_agent_rows', return_value=rows), patch.object(B, 'omp_sessions', return_value={42: {'start': 122}}):
            self.assertTrue(M.agents_running())
        with patch.object(B, '_agent_rows', return_value=rows), patch.object(B, 'omp_sessions', return_value={42: {'start': 1}}):
            self.assertFalse(M.agents_running())
        with patch.object(B, '_agent_rows', return_value=rows), patch.object(B, 'omp_sessions', return_value={}):
            self.assertFalse(M.agents_running())

    def test_claude_and_codex_still_wake_board(self):
        for command in ('claude', '/opt/homebrew/bin/codex', '/tmp/claude/versions/2.1.303'):
            with patch.object(B, '_agent_rows', return_value=[(42, 1, 'ttys001', 123, command)]), patch.object(B, 'omp_sessions', return_value={}):
                self.assertTrue(M.agents_running())

    def test_invalid_watcher_record_does_not_suppress_auto_start(self):
        with patch.object(M, 'watcher_alive', return_value=False), patch.object(M, 'agents_running', return_value=True), patch.object(M.subprocess, 'Popen') as start, patch('builtins.open', mock_open()):
            M.ensure_watcher()
            self.assertEqual(start.call_count, 1)
        with patch.object(M, 'watcher_alive', return_value=True), patch.object(M.subprocess, 'Popen') as start:
            M.ensure_watcher()
            start.assert_not_called()


if __name__ == '__main__':
    unittest.main()
