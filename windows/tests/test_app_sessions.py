"""Claude 앱 기록(Code 탭 · Cowork)으로 찾는 세션을 가짜 앱 폴더로 확인한다. 실제 앱 기록은 읽지 않는다."""
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import board as B

NOW = time.time()


class AppSessionsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='spyhop-app-')
        self.root = Path(self.tmp.name)
        self.app = self.root / 'Claude'
        self.home = self.root / 'home'
        self.env = patch.multiple(B, CLAUDE_APP_DIR=str(self.app), ENDED_FILE=str(self.root / 'ended.json'))
        self.env.start()
        self.user = patch.dict(os.environ, {'HOME': str(self.home), 'USERPROFILE': str(self.home)})
        self.user.start()

    def tearDown(self):
        self.user.stop()
        self.env.stop()
        self.tmp.cleanup()

    def code(self, sid, cli, cwd, ago=60, archived=False, transcript=True):
        rec = self.app / 'claude-code-sessions' / 'acct' / 'org' / ('local_%s.json' % sid)
        rec.parent.mkdir(parents=True, exist_ok=True)
        rec.write_text(json.dumps({'sessionId': 'local_' + sid, 'cliSessionId': cli, 'cwd': cwd, 'isArchived': archived,
                                   'lastActivityAt': (NOW - ago) * 1000, 'title': 'T ' + sid}), encoding='utf-8')
        os.utime(rec, (NOW - ago, NOW - ago))
        if transcript:
            log = self.home / '.claude' / 'projects' / 'p' / (cli + '.jsonl')
            log.parent.mkdir(parents=True, exist_ok=True)
            log.write_text('{}\n', encoding='utf-8')
        return rec

    def cowork(self, sid, cli, last_type, folders=(), audit_ago=5):
        org = self.app / 'local-agent-mode-sessions' / 'acct' / 'org'
        folder = org / sid[:8]
        (folder / 'outputs').mkdir(parents=True, exist_ok=True)
        rec = org / ('local_%s.json' % sid)
        rec.write_text(json.dumps({'sessionId': 'local_' + sid, 'cliSessionId': cli, 'cwd': str(folder / 'outputs'),
                                   'userSelectedFolders': list(folders), 'isArchived': False,
                                   'lastActivityAt': (NOW - 30) * 1000, 'title': 'Cowork ' + sid}), encoding='utf-8')
        log = folder / '.claude' / 'projects' / 'session' / (cli + '.jsonl')
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text('{}\n', encoding='utf-8')
        audit = folder / 'audit.jsonl'
        audit.write_text(json.dumps({'type': 'user'}) + '\n' + json.dumps({'type': last_type}) + '\n', encoding='utf-8')
        os.utime(audit, (NOW - audit_ago, NOW - audit_ago))
        return folder

    def test_recent_unarchived_code_tab_sessions_only(self):
        self.code('aaaa1111', 'cli-recent', '/w/automation')
        self.code('bbbb2222', 'cli-old', '/w/automation', ago=B.APP_RECENT + 60)
        self.code('cccc3333', 'cli-archived', '/w/automation', archived=True)
        self.code('dddd4444', 'cli-no-log', '/w/automation', transcript=False)
        found = B.app_sessions(now=NOW)
        self.assertEqual([s['cli'] for s in found], ['cli-recent'])
        self.assertEqual(found[0]['kind'], 'code')
        self.assertFalse(found[0]['busy'])  # 프로그램이 없는 Code 탭 세션은 일하는 중일 수 없다

    def test_running_sessions_are_not_listed_twice(self):
        self.code('aaaa1111', 'cli-live', '/w/automation')
        self.assertEqual(B.app_sessions(live_ids={'cli-live'}, now=NOW), [])

    def test_cowork_status_comes_from_audit(self):
        self.cowork('eeee5555-1', 'cli-working', 'assistant', folders=['/w/reports'])
        self.cowork('ffff6666-1', 'cli-done', 'result')
        self.cowork('9999aaaa-1', 'cli-stalled', 'assistant', audit_ago=B.COWORK_BUSY_QUIET + 60)
        found = {s['cli']: s for s in B.app_sessions(now=NOW)}
        self.assertEqual(set(found), {'cli-working', 'cli-done', 'cli-stalled'})
        self.assertTrue(found['cli-working']['busy'])
        self.assertFalse(found['cli-done']['busy'])
        self.assertFalse(found['cli-stalled']['busy'])
        self.assertEqual(found['cli-working']['cwd'], '/w/reports')  # 고른 폴더가 있으면 그 폴더 칸으로
        self.assertEqual(found['cli-done']['cwd'], '')
        self.assertTrue(found['cli-done']['log'].endswith('cli-done.jsonl'))

    def test_outside_terms_show_app_sessions_in_app_columns(self):
        self.code('aaaa1111', 'cli-code', '/w/automation')
        self.cowork('eeee5555-1', 'cli-cowork', 'result')
        with patch.object(B, 'agent_procs', return_value={}):
            terms, wts = B.outside_terms()
        cols = sorted(wts[t['worktreeId']]['displayName'] for t in terms)
        self.assertEqual(cols, ['Cowork', 'automation · Claude app'])
        for t in terms:
            self.assertTrue(t['handle'].startswith('proc_app_'))
            self.assertTrue(t['_proc']['log'])
            self.assertEqual(t['agent']['state'], 'done')

    def codex_db(self, rows):
        """가짜 Codex 앱 상태 DB. rows: (id, source, thread_source, originator, archived, ago, busy)"""
        import sqlite3
        home = self.root / 'codex'
        (home / 'sessions').mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(str(home / 'state_5.sqlite'))
        db.execute('create table threads (id text, rollout_path text, cwd text, updated_at integer, source text, '
                   'thread_source text, originator text, title text, archived integer)')
        for tid, source, tsrc, origin, archived, ago, busy in rows:
            log = home / 'sessions' / ('rollout-x-%s.jsonl' % tid)
            log.write_text('{"type":"task_started"}\n' + ('' if busy else '{"type":"task_complete"}\n'), encoding='utf-8')
            db.execute('insert into threads values (?,?,?,?,?,?,?,?,?)',
                       (tid, str(log), '/w/automation', int(NOW - ago), source, tsrc, origin, 'T', archived))
        db.commit()
        db.close()
        return str(home)

    def test_codex_app_threads_opened_by_the_user_only(self):
        home = self.codex_db([
            ('t-user', 'vscode', 'user', 'Codex Desktop', 0, 60, True),
            ('t-old-version', 'vscode', None, None, 0, 60, False),
            ('t-imported', 'vscode', None, 'Codex Desktop', 0, 60, False),
            ('t-archived', 'vscode', 'user', 'Codex Desktop', 1, 60, False),
            ('t-stale', 'vscode', 'user', 'Codex Desktop', 0, B.APP_RECENT + 60, False),
            ('t-exec', 'exec', 'user', 'codex_exec', 0, 60, False),
            ('t-tui', 'cli', 'user', 'codex-tui', 0, 60, False),
        ])
        found = {s['id']: s for s in B.codex_app_sessions(now=NOW, home=home)}
        self.assertEqual(set(found), {'t-user', 't-old-version'})
        self.assertTrue(found['t-user']['busy'])  # 마지막 턴이 아직 안 끝났다
        self.assertFalse(found['t-old-version']['busy'])
        self.assertEqual(found['t-user']['kind'], 'codex-app')

    def test_codex_app_threads_held_by_a_program_are_not_listed_twice(self):
        home = self.codex_db([('t-user', 'vscode', 'user', 'Codex Desktop', 0, 60, False)])
        self.assertEqual(B.codex_app_sessions(live_ids={'rollout-x-t-user'}, now=NOW, home=home), [])
        self.assertEqual(B.codex_app_sessions(now=NOW, home=str(self.root / 'no-codex')), [])

    def test_session_ended_on_the_board_stays_off_until_used_again(self):
        self.code('aaaa1111', 'cli-ended', '/w/automation')
        log = self.home / '.claude' / 'projects' / 'p' / 'cli-ended.jsonl'
        os.utime(log, (NOW - 120, NOW - 120))
        B.mark_ended(str(log), now=NOW - 60)
        self.assertEqual(B.app_sessions(now=NOW), [])  # 끝낸 뒤 새 대화가 없다
        os.utime(log, (NOW - 60 + B.ENDED_GRACE + 5, NOW - 60 + B.ENDED_GRACE + 5))  # 앱에서 다시 썼다
        self.assertEqual([s['cli'] for s in B.app_sessions(now=NOW)], ['cli-ended'])

    def test_codex_thread_ended_on_the_board_stays_off(self):
        home = self.codex_db([('t-user', 'vscode', 'user', 'Codex Desktop', 0, 60, False)])
        log = os.path.join(home, 'sessions', 'rollout-x-t-user.jsonl')
        os.utime(log, (NOW - 120, NOW - 120))
        B.mark_ended(log, now=NOW - 60)
        self.assertEqual(B.codex_app_sessions(now=NOW, home=home), [])

    def test_ended_list_forgets_old_entries(self):
        B.mark_ended('/x/old.jsonl', now=NOW - B.APP_RECENT - 2 * 86400)
        B.mark_ended('/x/new.jsonl', now=NOW)
        self.assertEqual(set(B.load_ended()), {'new'})

    def test_broken_records_are_skipped(self):
        bad = self.app / 'claude-code-sessions' / 'acct' / 'org' / 'local_bad.json'
        bad.parent.mkdir(parents=True)
        bad.write_text('{not json', encoding='utf-8')
        (bad.parent / 'local_list.json').write_text('[]', encoding='utf-8')
        self.code('aaaa1111', 'cli-ok', '/w/automation')
        self.assertEqual([s['cli'] for s in B.app_sessions(now=NOW)], ['cli-ok'])


if __name__ == '__main__':
    unittest.main()
