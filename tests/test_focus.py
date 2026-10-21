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


class CmuxFocusTest(unittest.TestCase):
    AGENT = {'pid': 42, 'tty': 'ttys001', 'cmux_panel_id': 'P1', 'cmux_workspace_id': 'W1'}

    def focus(self, reply):
        with patch.object(B, 'agent_procs', return_value={42: self.AGENT}), patch.object(B, 'find_bin', return_value='/qa/cmux'), patch.object(B, '_open_app', return_value=True) as app, patch.object(B.subprocess, 'run', side_effect=[reply]) as sp:
            return B.focus_outside(42), app, sp

    def test_label_from_cmux_env_without_term_program(self):
        self.assertEqual(B._term_label(self.AGENT), 'cmux')
        self.assertEqual(B._term_label({'term_program': 'ghostty', 'cmux_panel_id': 'P1'}), 'Ghostty')
        self.assertEqual(B._term_label({}), 'Terminal')

    def test_focus_panel_ok_reaches_tab(self):
        got, app, sp = self.focus(SimpleNamespace(returncode=0, stdout='OK surface:1 workspace:2'))
        self.assertEqual(got, 'tab')
        self.assertEqual(sp.call_args[0][0], ['/qa/cmux', 'focus-panel', '--panel', 'P1', '--workspace', 'W1'])
        app.assert_called_with('cmux')

    def test_focus_panel_failure_falls_back_to_app(self):
        self.assertEqual(self.focus(SimpleNamespace(returncode=1, stdout=''))[0], 'app')
        self.assertEqual(self.focus(SimpleNamespace(returncode=0, stdout='ERR'))[0], 'app')
        self.assertEqual(self.focus(OSError())[0], 'app')

    def test_ps_runs_with_c_locale(self):
        with patch.object(B.subprocess, 'run', return_value=SimpleNamespace(stdout='')) as sp:
            B._agent_rows()
        self.assertEqual(sp.call_args[1]['env']['LC_ALL'], 'C')


if __name__ == '__main__':
    unittest.main()
