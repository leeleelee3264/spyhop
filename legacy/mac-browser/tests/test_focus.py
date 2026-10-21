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
        with patch.object(B, 'agent_procs', return_value={42: agent}), patch.object(B, 'find_bin', return_value='/qa/wezterm'), patch.object(B, '_open_app', return_value=True), patch.object(B, '_osa', return_value=raised), patch.object(B.subprocess, 'run', side_effect=replies):
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


if __name__ == '__main__':
    unittest.main()
