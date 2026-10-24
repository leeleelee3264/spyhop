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
        self.assertEqual(B._term_label({'term_program': 'ghostty', 'cmux_panel_id': 'P1'}), 'cmux')
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

    def test_panel_without_workspace_falls_back_to_app(self):
        agent = {'pid': 42, 'tty': 'ttys001', 'cmux_panel_id': 'P1'}
        with patch.object(B, 'agent_procs', return_value={42: agent}), patch.object(B, '_open_app', return_value=True), patch.object(B.subprocess, 'run') as sp:
            self.assertEqual(B.focus_outside(42), 'app')
        sp.assert_not_called()

    def test_workspace_without_panel_is_plain_terminal(self):
        agent = {'pid': 42, 'tty': 'ttys001', 'cmux_workspace_id': 'W1'}
        self.assertEqual(B._term_label(agent), 'Terminal')
        with patch.object(B, 'agent_procs', return_value={42: agent}), patch.object(B.subprocess, 'run') as sp:
            self.assertEqual(B.focus_outside(42), '')
        sp.assert_not_called()

    def test_focus_panel_ok_but_app_fails(self):
        with patch.object(B, 'agent_procs', return_value={42: self.AGENT}), patch.object(B, 'find_bin', return_value='/qa/cmux'), patch.object(B, '_open_app', return_value=False), patch.object(B.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='OK surface:1')):
            self.assertEqual(B.focus_outside(42), '')

    def test_cmux_identity_wins_over_embedded_ghostty(self):
        agent = dict(self.AGENT, term_program='ghostty')
        with patch.object(B, 'agent_procs', return_value={42: agent}), patch.object(B, '_ghostty_focus', return_value=True) as gf, patch.object(B, '_cmux_focus') as cf:
            self.assertEqual(B.focus_outside(42), 'tab')
        gf.assert_not_called()
        cf.assert_called_once()

    def test_surface_id_without_legacy_panel_id_is_supported(self):
        agent = {'pid': 42, 'tty': 'ttys001', 'term_program': 'ghostty', 'cmux_surface_id': 'S1', 'cmux_workspace_id': 'W1'}
        self.assertEqual(B._term_label(agent), 'cmux')
        with patch.object(B, 'find_bin', return_value='/qa/cmux'), patch.object(B, '_open_app', return_value=True), patch.object(B.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='OK surface:1')) as run:
            self.assertTrue(B._cmux_focus(agent))
        self.assertEqual(run.call_args.args[0], ['/qa/cmux', 'focus-panel', '--panel', 'S1', '--workspace', 'W1'])

    def test_other_real_terminal_still_wins_over_inherited_cmux_env(self):
        self.assertEqual(B._term_label(dict(self.AGENT, term_program='WezTerm')), 'WezTerm')

    def test_orca_and_tmux_keep_their_identity_with_inherited_cmux_env(self):
        for term in ('Orca', 'tmux'):
            self.assertEqual(B._term_label(dict(self.AGENT, term_program=term)), term)

    def test_watcher_record_ps_runs_with_c_locale(self):
        with patch.object(B, 'read_pidfile', return_value=(42, '/x/board.py', None)), patch.object(B.subprocess, 'run', return_value=SimpleNamespace(stdout='')) as sp:
            B.watcher_record('/x/pid')
        self.assertEqual(sp.call_args_list[0][1]['env']['LC_ALL'], 'C')


if __name__ == '__main__':
    unittest.main()
