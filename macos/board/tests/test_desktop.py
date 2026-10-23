"""Claude 데스크톱 앱(Code 탭) 세션은 tty 가 없어도 카드가 되고, Go to session 은 앱 딥링크로 간다."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import board as B


def desktop_agent(**extra):
    a = {'pid': 42, 'kind': 'claude', 'tty': '??', 'start': 1000, 'cwd': '/w/blog', 'busy': True,
         'desktop': True, 'host_sid': 'local_abc-123', 'name': 'blog cleanup', 'log': None, 'how': 'claude:desktop-app'}
    a.update(extra)
    return a


class DesktopCardTest(unittest.TestCase):
    def terms(self, agent):
        with patch.object(B, 'agent_procs', return_value={agent['pid']: agent}):
            return B.outside_terms()

    def test_desktop_session_without_tty_becomes_a_card(self):
        out, wts = self.terms(desktop_agent())
        self.assertEqual(len(out), 1)
        t = out[0]
        self.assertEqual(t['handle'], 'proc_42')
        self.assertEqual(t['worktreeId'], 'term:Claude App:/w/blog')
        self.assertEqual(wts[t['worktreeId']]['displayName'], 'blog · Claude App')
        self.assertEqual(t['agent'], {'state': 'working'})
        self.assertEqual(t['title'], 'blog cleanup')

    def test_idle_desktop_session_is_my_turn(self):
        out, _ = self.terms(desktop_agent(busy=False))
        self.assertEqual(out[0]['agent'], {'state': 'done'})

    def test_headless_claude_without_desktop_registration_is_still_skipped(self):
        out, wts = self.terms({'pid': 7, 'kind': 'claude', 'tty': '??', 'start': 1000, 'cwd': '/w/x'})
        self.assertEqual((out, wts), ([], {}))


class DesktopFocusTest(unittest.TestCase):
    def focus(self, agent, open_rc=0, app_ok=True):
        calls = []

        def run(cmd, **kw):
            calls.append(cmd)
            return SimpleNamespace(returncode=open_rc, stdout='')
        with patch.object(B, 'agent_procs', return_value={42: agent}), patch.object(B, '_open_app', return_value=app_ok) as oa, \
                patch.object(B.subprocess, 'run', side_effect=run):
            return B.focus_outside(42), calls, oa

    def test_go_to_session_opens_the_app_deep_link(self):
        res, calls, oa = self.focus(desktop_agent())
        self.assertEqual(res, 'tab')
        self.assertEqual(calls, [['open', 'claude://code/continue?session=local_abc-123']])
        oa.assert_called_once_with('Claude')

    def test_successful_url_does_not_claim_focus_when_app_activation_fails(self):
        res, _, _ = self.focus(desktop_agent(), app_ok=False)
        self.assertEqual(res, '')

    def test_failed_deep_link_falls_back_to_bringing_the_app_forward(self):
        res, _, oa = self.focus(desktop_agent(), open_rc=1)
        self.assertEqual(res, 'app')
        oa.assert_called_once_with('Claude')

    def test_missing_host_session_id_only_brings_the_app_forward(self):
        res, calls, oa = self.focus(desktop_agent(host_sid=None))
        self.assertEqual(res, 'app')
        self.assertEqual(calls, [])
        oa.assert_called_once_with('Claude')


if __name__ == '__main__':
    unittest.main()
