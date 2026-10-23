"""외부 터미널이 정확한 대상 전환을 확인하지 못하면 앱 수준으로만 보고한다."""
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import board as B


class TerminalFocusTest(unittest.TestCase):
    def focus(self, replies, raised=False):
        agent = {'pid': 42, 'tty': 'ttys001', 'term_program': 'WezTerm'}
        with patch.object(B, 'agent_procs', return_value={42: agent}), patch.object(B, 'find_bin', return_value='/qa/wezterm'), patch.object(B, '_open_app', return_value=True), patch.object(B, '_osa', return_value=raised), patch.object(B.os, 'open', side_effect=OSError('test tty')), patch.object(B.subprocess, 'run', side_effect=replies):
            return B.focus_outside(42)

    def pane(self):
        return SimpleNamespace(stdout=json.dumps([{'pane_id': 7, 'tty_name': '/dev/ttys001', 'title': 'QA target'}]))

    def test_accessibility_denied_or_ambiguous_does_not_claim_exact_tab(self):
        self.assertEqual(self.focus([self.pane(), SimpleNamespace(returncode=0), self.pane()]), 'app')

    def test_pane_gone_during_selection_falls_back_without_error(self):
        self.assertEqual(self.focus([self.pane(), SimpleNamespace(returncode=0), SimpleNamespace(stdout='[]')]), 'app')

    def test_bad_terminal_reply_does_not_break_go(self):
        self.assertEqual(self.focus([SimpleNamespace(stdout='not json')]), 'app')

    def test_cli_refusal_does_not_claim_exact_tab(self):
        self.assertEqual(self.focus([self.pane(), SimpleNamespace(returncode=1)]), 'app')


class WezTermRaiseTest(unittest.TestCase):
    def setUp(self):
        self.pane = {'tty_name': '/dev/ttys999', 'title': '동일한 제목', 'tab_title': 'Custom tab'}

    def test_custom_tab_title_is_not_used_as_window_title(self):
        with patch.object(B, '_osa', return_value=True) as osa, patch.object(B.os, 'open') as opened:
            self.assertTrue(B._wezterm_raise('/qa/wezterm', self.pane))
        self.assertIn('동일한 제목', osa.call_args[0][0])
        self.assertNotIn('Custom tab', osa.call_args[0][0])
        opened.assert_not_called()

    def test_duplicate_title_uses_unique_marker_and_restores_original(self):
        with patch.object(B, '_osa', side_effect=[False, True]) as osa, patch.object(B.os, 'open', return_value=9), patch.object(B.os, 'write') as write, patch.object(B.os, 'close') as close:
            self.assertTrue(B._wezterm_raise('/qa/wezterm', self.pane))
        marker = write.call_args_list[0].args[1]
        self.assertTrue(marker.startswith(b'\x1b]2;Spyhop-focus-'))
        self.assertIn(marker[4:-1].decode(), osa.call_args[0][0])
        self.assertEqual(write.call_args_list[1].args, (9, '\x1b]2;동일한 제목\x07'.encode()))
        close.assert_called_once_with(9)

    def test_failed_raise_still_restores_title_and_closes_tty(self):
        with patch.object(B, '_osa', side_effect=[False, False]), patch.object(B.os, 'open', return_value=9), patch.object(B.os, 'write') as write, patch.object(B.os, 'close') as close:
            self.assertFalse(B._wezterm_raise('/qa/wezterm', self.pane))
        self.assertEqual(write.call_args_list[-1].args, (9, '\x1b]2;동일한 제목\x07'.encode()))
        close.assert_called_once_with(9)

    def test_unwritable_tty_returns_failure(self):
        with patch.object(B, '_osa', return_value=False), patch.object(B.os, 'open', side_effect=OSError):
            self.assertFalse(B._wezterm_raise('/qa/wezterm', self.pane))

    def test_control_characters_are_not_written_back_to_terminal(self):
        self.pane['title'] = 'bad\x1b]52;clipboard\x07'
        with patch.object(B.os, 'open') as opened:
            self.assertFalse(B._wezterm_raise('/qa/wezterm', self.pane))
        opened.assert_not_called()

    def test_separate_mux_window_title_is_restored_too(self):
        self.pane.update(pane_id=7, window_title='My window')
        with patch.object(B, '_osa', side_effect=[False, True]), patch.object(B.os, 'open', return_value=9), patch.object(B.os, 'write'), patch.object(B.os, 'close'), patch.object(B.subprocess, 'run') as run:
            self.assertTrue(B._wezterm_raise('/qa/wezterm', self.pane))
        self.assertEqual(run.call_args.args[0], ['/qa/wezterm', 'cli', 'set-window-title', '--pane-id', '7', 'My window'])


if __name__ == '__main__':
    unittest.main()
