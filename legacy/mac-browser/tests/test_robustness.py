"""동시 저장·잘못된 요약·설정 요청의 재현 시험. 사용자 파일과 모델은 사용하지 않는다."""
import concurrent.futures
import copy
import http.server
import json
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))
import board as B
import demo_screens as D

VALID = {'title': 'QA task', 'summary': 'Summary', 'last_reply': 'Reply',
         'steps': [{'label': 'Check', 'state': 'done', 'detail': ''}], 'items': []}


class RobustnessTest(unittest.TestCase):
    def setUp(self):
        self.saved = dict(vars(B))
        self.tmp = tempfile.TemporaryDirectory(prefix='spyhop-robustness-')
        self.root = Path(self.tmp.name)
        self.server = None
        for key, name in [('BASE', ''), ('AUTO', 'auto'), ('OUT', 'board.html'),
                          ('STATE', 'state.json'), ('CONFIG', 'config.json'),
                          ('GROUPS_FILE', 'groups.json'), ('MOVED_FILE', 'moved.json'),
                          ('TRACE', 'trace.json')]:
            setattr(B, key, str(self.root / name))
        Path(B.AUTO).mkdir()
        B.token = lambda: 'qa'
        B._GROUPING = {'busy': False, 'at': 0, 'pruned': time.time()}
        B._SYSLANG = {'code': 'en', 'at': 9e18}
        self.log = self.root / 'qa.jsonl'
        self.log.write_text(json.dumps({'type': 'user', 'message': {'content': 'QA request'}}) + '\n')
        B.save_json(B.STATE, {'sessions': [{'handle': 'qa%d' % i, 'log': 'log%d' % i} for i in range(20)]})
        B.save_json(B.CONFIG, {'refresh': 10})
        B.save_groups({'groups': [], 'assign': {}})

    def tearDown(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        vars(B).update(self.saved)
        self.tmp.cleanup()

    def serve(self):
        real = http.server.ThreadingHTTPServer

        def server(address, handler):
            self.server = real(('127.0.0.1', 0), handler)
            return self.server
        with patch('http.server.ThreadingHTTPServer', server):
            B.serve()
        self.url = 'http://127.0.0.1:%d' % self.server.server_port

    def request(self, route, data=None):
        req = urllib.request.Request(self.url + route, data=data)
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as response:
            return response.code, response.read()

    def move(self, i):
        return self.request('/move?k=qa', json.dumps({'h': 'qa%d' % i, 'wid': 'group:Manual %d' % i}).encode())

    def test_concurrent_http_moves_preserve_every_assignment(self):
        self.serve()
        for count in (2, 5, 20):
            for _ in range(10):
                B.save_groups({'groups': [], 'assign': {}})
                barrier = threading.Barrier(count)

                def move(i):
                    barrier.wait(timeout=5)
                    return self.move(i)[0]
                with concurrent.futures.ThreadPoolExecutor(count) as pool:
                    self.assertEqual(list(pool.map(move, range(count))), [200] * count)
                current = B.load_groups()['assign']
                self.assertEqual(len(current), count)
                for i in range(count):
                    self.assertEqual(current['log%d' % i], {'g': 'Manual %d' % i, 'manual': True})

    def test_manual_move_waits_for_ai_merge_and_survives(self):
        self.serve()
        read, release = threading.Event(), threading.Event()
        local = threading.local()
        original = B.load_groups

        def load():
            result = original()
            if getattr(local, 'ai', False):
                read.set()
                if not release.wait(5):
                    raise RuntimeError('test did not release AI merge')
            return result

        def model(*args):
            local.ai = True
            return '{"assign":{"s1":"AI topic"}}'
        with patch.object(B, 'load_groups', load), patch.object(B, 'llm', model):
            B.assign_groups([('new', 'New task', 'Summary')])
            self.assertTrue(read.wait(5))
            with concurrent.futures.ThreadPoolExecutor(1) as pool:
                pending = pool.submit(self.move, 0)
                try:
                    with self.assertRaises(concurrent.futures.TimeoutError):
                        pending.result(timeout=.2)
                finally:
                    release.set()
                self.assertEqual(pending.result(timeout=5)[0], 200)
            self.wait_for_grouping()
        current = B.load_groups()['assign']
        self.assertEqual(current['log0'], {'g': 'Manual 0', 'manual': True})
        self.assertEqual(current['new']['g'], 'AI topic')

    def wait_for_grouping(self):
        deadline = time.monotonic() + 5
        while B._GROUPING['busy'] and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertFalse(B._GROUPING['busy'])

    def test_manual_move_does_not_wait_for_model_network_call(self):
        self.serve()
        entered, release = threading.Event(), threading.Event()

        def model(*args):
            entered.set()
            if not release.wait(5):
                raise RuntimeError('model not released')
            return '{"assign":{"s1":"AI topic"}}'
        with patch.object(B, 'llm', model):
            B.assign_groups([('log0', 'New task', 'Summary')])
            self.assertTrue(entered.wait(5))
            try:
                self.assertEqual(self.move(0)[0], 200)
            finally:
                release.set()
            self.wait_for_grouping()
        self.assertEqual(B.load_groups()['assign']['log0'], {'g': 'Manual 0', 'manual': True})

    def test_prune_reloads_snapshot_and_other_writers_keep_manual(self):
        stale = B.load_groups()
        B.save_groups({'groups': ['Manual'], 'assign': {'handle': {'g': 'Manual', 'manual': True}}})
        B.prune_groups(stale, {'handle'})
        B.adopt_keys([{'handle': 'handle', 'log': 'transcript'}])
        B.regroup_all()
        self.assertEqual(B.load_groups(), {'groups': ['Manual'], 'assign': {
            'transcript': {'g': 'Manual', 'manual': True}}})

    def test_invalid_responses_preserve_last_good_and_back_off(self):
        variants = [(key, value) for key in ('title', 'summary', 'last_reply')
                    for value in ({'bad': 'type'}, 7, ['bad'])]
        variants += [('steps', None), ('steps', {}), ('items', None),
                     ('items', ['bad']), ('steps', [{'label': {}, 'state': 'now'}])]
        cache = Path(B.AUTO) / (self.log.name + '.json')
        for key, value in variants:
            with self.subTest(key=key, value=value):
                old = dict(copy.deepcopy(VALID), size=0, pos=0, at=0, ok_at=123, lang='en')
                B.save_json(str(cache), old)
                answer = dict(copy.deepcopy(VALID), **{key: value})
                with patch.object(B, 'llm', return_value=json.dumps(answer)) as model, patch.object(
                        B, 'current_summarizer', return_value='qa'):
                    result = B.summarize(str(self.log))
                    B.summarize(str(self.log))
                self.assertTrue(result['fail'])
                self.assertEqual(result['title'], old['title'])
                self.assertEqual(result['ok_at'], 123)
                model.assert_called_once()
                self.assertEqual(B.cached_summary(str(self.log))['title'], old['title'])

    def test_invalid_existing_cache_is_ignored_and_repaired(self):
        cache = Path(B.AUTO) / (self.log.name + '.json')
        B.save_json(str(cache), dict(VALID, title={'bad': 'type'}, size=self.log.stat().st_size, at=time.time()))
        self.assertIsNone(B.cached_summary(str(self.log)))
        with patch.object(B, 'llm', return_value=json.dumps(VALID)) as model, patch.object(
                B, 'current_summarizer', return_value='qa'):
            result = B.summarize(str(self.log))
        model.assert_called_once()
        self.assertEqual(result['title'], VALID['title'])
        self.assertNotIn('fail', result)
        self.assertEqual(B.cached_summary(str(self.log)), result)

    def test_one_bad_summary_does_not_stop_board_rebuild(self):
        saved, demo = dict(vars(B)), D.TMP
        try:
            D.TMP = str(self.root)
            D.patch('location')
            for name in ('BASE', 'AUTO', 'OUT', 'STATE', 'CONFIG', 'GROUPS_FILE', 'MOVED_FILE', 'TRACE'):
                setattr(B, name, saved[name])
            for i in range(len(D.SESSIONS) + 1):
                log = str(self.root / ('session-%d.jsonl' % i))
                B.save_json(str(Path(B.AUTO) / (Path(log).name + '.json')), B.cached_summary(log))
            B.cached_summary = saved['cached_summary']
            B.build()
            before = len(json.loads(Path(B.STATE).read_text())['sessions'])
            cache = Path(B.AUTO) / 'session-0.jsonl.json'
            B.save_json(str(cache), dict(VALID, title={'bad': 'type'}))
            for _ in range(3):
                B.build()
                self.assertEqual(len(json.loads(Path(B.STATE).read_text())['sessions']), before)
                self.assertEqual(Path(B.OUT).read_text().count('class="card '), before)
            B.save_json(str(cache), VALID)
            B.build()
            self.assertIn(VALID['title'], Path(B.OUT).read_text())
        finally:
            vars(B).update(saved)
            D.TMP = demo

    def test_bad_config_returns_400_without_changes_and_server_recovers(self):
        self.serve()
        original = Path(B.CONFIG).read_bytes()
        for body in (b'{bad', b'[]', b'null', b'7', b'"text"'):
            self.assertEqual(self.request('/config?k=qa', body)[0], 400)
            self.assertEqual(Path(B.CONFIG).read_bytes(), original)
        self.assertEqual(self.request('/state.json')[0], 200)
        with patch.object(B, 'build'):
            self.assertEqual(self.request('/config?k=qa', b'{"refresh":30}')[0], 200)
        self.assertEqual(B.load_config()['refresh'], 30)

    def test_corrupt_update_ack_does_not_break_server_and_valid_ack_persists(self):
        B.UPDATE_FILE = str(self.root / 'update.json')
        self.serve()
        for value in ([], None, {'at': 'bad'}):
            B.save_json(B.UPDATE_FILE, value)
            self.assertEqual(self.request('/update-seen?k=qa', b'')[0], 200)
        B.save_json(B.UPDATE_FILE, {'from': '0.5.0', 'to': '0.6.0', 'at': time.time(), 'seen': False})
        self.assertEqual(self.request('/update-seen?k=qa', b'')[0], 200)
        self.assertTrue(json.loads(Path(B.UPDATE_FILE).read_text())['seen'])

    def test_unknown_and_stale_external_sessions_cannot_signal_processes(self):
        self.serve()
        B.save_json(B.STATE, {'sessions': [{'handle': 'proc_123'}]})
        with patch.object(B, 'agent_procs', return_value={}), patch.object(
                B.os, 'kill') as kill, patch.object(B, 'focus_outside') as focus:
            self.assertEqual(self.request('/switch?h=proc_999')[0], 404)
            self.assertEqual(self.request('/close?k=qa', b'proc_999')[0], 404)
            self.assertEqual(self.request('/close?k=qa', b'proc_123')[0], 404)
            kill.assert_not_called()
            focus.assert_not_called()

    def test_ghostty_ambiguous_folder_does_not_focus_another_session(self):
        a = {'cwd': '/qa/shared'}
        rows = 'first\tTask A\t/qa/shared\nsecond\tTask B\t/qa/shared\n'
        with patch.object(B.subprocess, 'run', return_value=B.subprocess.CompletedProcess(
                [], 0, stdout=rows)), patch.object(B, '_session_title', return_value=''), patch.object(
                B, '_osa') as focus:
            self.assertFalse(B._ghostty_focus(a))
            focus.assert_not_called()
        with patch.object(B.subprocess, 'run', return_value=B.subprocess.CompletedProcess(
                [], 0, stdout=rows)), patch.object(B, '_session_title', return_value='Task B'), patch.object(
                B, '_osa', return_value=True) as focus:
            self.assertTrue(B._ghostty_focus(a))
            self.assertIn('if id of s is "second"', focus.call_args.args[0])


if __name__ == '__main__':
    unittest.main()
