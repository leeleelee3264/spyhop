"""OMP를 기존 수집·요약·카드 경로에 연결하는 회귀 시험."""
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import board as B


class OMPTest(unittest.TestCase):
    def setUp(self):
        self.saved = dict(vars(B))
        self.tmp = tempfile.TemporaryDirectory(prefix='spyhop-omp-test-')
        self.root = Path(self.tmp.name)
        B.OMP_STATE_DIR = str(self.root / 'status')
        B.MATCHES = str(self.root / 'matches.json')
        B._PROC_CACHE = {'at': 0, 'data': None}
        B._FILE_CACHE = {}
        B.TURN_CACHE = {}
        self.cwd = str(self.root)
        self.log = self.root / '2026-10-19T06-00-00Z_01a152dc-9f57-72b4-a9e9-bb45676429b5.jsonl'
        self.entries = [
            {'type': 'title', 'title': 'OMP QA'},
            {'type': 'session', 'version': 3, 'id': 'session-one', 'cwd': self.cwd},
            {'type': 'model_change', 'model': 'test/deepseek-flash'},
            {'type': 'message', 'timestamp': '2026-10-19T06:00:00Z', 'message': {
                'role': 'user', 'content': [{'type': 'text', 'text': 'QA request'}]}},
            {'type': 'message', 'timestamp': '2026-10-19T06:00:02Z', 'message': {
                'role': 'assistant', 'content': [{'type': 'thinking', 'thinking': 'private reasoning'},
                                                {'type': 'text', 'text': 'QA reply'}], 'stopReason': 'stop'}},
        ]
        self.write_log(self.log, self.entries)

    def tearDown(self):
        vars(B).update(self.saved)
        self.tmp.cleanup()

    def write_log(self, path, entries):
        path.write_text(''.join(json.dumps(e, separators=(',', ':')) + '\n' for e in entries))

    def register(self, pid=11, start=100, **extra):
        value = dict(pid=pid, start=start, busy=True, sid='session-one', cwd=self.cwd, log=str(self.log))
        value.update(extra)
        B.save_json(str(Path(B.OMP_STATE_DIR) / ('%s.json' % pid)), value)

    def processes(self, rows):
        with patch.object(B, '_agent_rows', return_value=rows), patch.object(
                B.subprocess, 'run', return_value=B.subprocess.CompletedProcess([], 0, stdout='')), patch.object(
                B, '_lsof', return_value=''):
            return B.agent_procs()

    def test_exact_pid_and_start_match_without_claiming_other_bun_processes(self):
        self.register()
        self.register(12, start=1)  # 같은 PID가 다시 쓰인 옛 등록
        procs = self.processes([(11, 1, 'ttys001', 100, 'bun'),
                               (12, 1, 'ttys002', 200, 'bun'),
                               (13, 1, 'ttys003', 100, 'bun')])
        self.assertEqual(set(procs), {11})
        self.assertEqual(procs[11]['kind'], 'omp')
        self.assertEqual(procs[11]['log'], str(self.log))
        self.assertTrue(procs[11]['busy'])

    def test_two_sessions_in_same_folder_keep_exact_records(self):
        second = self.root / 'second.jsonl'
        entries = copy.deepcopy(self.entries)
        entries[1]['id'] = 'session-two'
        self.write_log(second, entries)
        self.register(11)
        self.register(12, sid='session-two', log=str(second))
        procs = self.processes([(11, 1, 'ttys001', 100, 'bun'), (12, 1, 'ttys002', 100, 'bun')])
        self.assertEqual(procs[11]['log'], str(self.log))
        self.assertEqual(procs[12]['log'], str(second))

    def test_changed_session_registration_does_not_reuse_old_record(self):
        self.register(sid='different-session')
        procs = self.processes([(11, 1, 'ttys001', 100, 'bun')])
        self.assertNotIn('log', procs[11])

    def test_malformed_registration_does_not_break_other_sessions(self):
        self.register()
        for i, data in enumerate([[], None, {'pid': '12'}, {'pid': 12, 'start': 'bad'},
                                  {'pid': 12, 'start': 100, 'busy': 'true'},
                                  {'pid': True, 'start': 100, 'busy': True}]):
            B.save_json(str(Path(B.OMP_STATE_DIR) / ('bad%s.json' % i)), data)
        self.assertEqual(set(B.omp_sessions()), {11})

    def test_live_status_wins_over_stale_codex_state_in_both_directions(self):
        t = {'title': 'π > work', 'agent': {'agentType': 'codex', 'state': 'done'},
             'log': str(self.log), '_proc': {'kind': 'omp', 'busy': True}}
        self.assertEqual(B.status_of(t), 'busy')
        t['_proc']['busy'] = False
        t['agent']['state'] = 'working'
        self.assertEqual(B.status_of(t), 'wait')

    def test_omp_without_registration_never_adopts_cached_codex_log(self):
        for title in ('π > work', '⌥ OMP QA'):
            B.save_matches({'qa': '/old/rollout-codex.jsonl'})
            t = {'handle': 'qa', 'title': title, 'worktreeId': 'w', 'worktreePath': self.cwd,
                 'agent': {'agentType': 'codex', 'state': 'done'}}
            with patch.object(B, 'claude_index', return_value={}), patch.object(
                    B, 'live_claude_sessions', return_value=[]), patch.object(
                    B, 'codex_files', side_effect=AssertionError('must not guess a Codex record')):
                B.match_sessions([t], {'w': {'path': self.cwd}})
            self.assertNotIn('log', t)

    def test_registered_omp_uses_own_record_before_legacy_matching(self):
        B.save_matches({'qa': '/old/rollout-codex.jsonl'})
        t = {'handle': 'qa', 'title': 'old title', '_pkind': 'omp', '_plog': str(self.log),
             'worktreeId': 'w', 'worktreePath': self.cwd}
        with patch.object(B, 'claude_index', return_value={}), patch.object(
                B, 'live_claude_sessions', return_value=[]):
            B.match_sessions([t], {'w': {'path': self.cwd}})
        self.assertEqual(t['log'], str(self.log))

    def test_native_records_feed_existing_summary_detail_time_and_model_paths(self):
        self.assertEqual(B.last_turn(str(self.log)), ('QA request', 'QA reply'))
        text = B.transcript(str(self.log))
        self.assertIn('U: QA request', text)
        self.assertIn('A: QA reply', text)
        self.assertNotIn('private reasoning', text)
        ai, user = B.turn_times(str(self.log))
        self.assertEqual(ai - user, 2)
        self.assertEqual(B.model_of(str(self.log)), 'DeepSeek flash')
        self.assertEqual(B._session_title({'kind': 'omp', 'log': str(self.log)}), 'OMP QA')

    def test_installation_is_optional_repeatable_and_uses_existing_omp_directory(self):
        missing = self.root / 'not-installed'
        B.install_omp_extension(str(missing))
        self.assertFalse(missing.exists())
        agent = self.root / 'agent'
        agent.mkdir()
        B.install_omp_extension(str(agent))
        file = agent / 'extensions/spyhop-status.ts'
        self.assertEqual(file.read_text(), B.OMP_EXTENSION)
        stamp = file.stat().st_mtime_ns
        B.install_omp_extension(str(agent))
        self.assertEqual(file.stat().st_mtime_ns, stamp)

    def test_old_orca_cli_falls_back_to_default_layout_response(self):
        expected = {'terminals': [], 'visualLayouts': []}
        with patch.object(B, 'orca_or', side_effect=[{}, expected]) as call:
            self.assertEqual(B.terminal_layouts(), expected)
        self.assertIn('--include-visual-layouts', call.call_args_list[0].args)
        self.assertEqual(call.call_args_list[1].args[-2:], ('terminal', 'list'))

    @unittest.skipUnless(shutil.which('bun'), 'Bun required for the native OMP extension')
    def test_native_extension_tracks_switch_end_and_ignores_subagents(self):
        # 확장은 원문 그대로 실행하고 홈 위치만 임시 폴더로 주입한다.
        script = '''
const fs = require('node:fs'), path = require('node:path');
const source = CODE.replace(/^import .*;$/gm, '').replace('export default function', 'return function');
const factory = new Function('mkdirSync','writeFileSync','renameSync','rmSync','homedir','join',source)(
  fs.mkdirSync,fs.writeFileSync,fs.renameSync,fs.rmSync,()=>HOME,path.join);
const events = {}; factory({on:(name,fn)=>events[name]=fn});
const ctx = {agent:{kind:'main'},cwd:'/qa',isIdle:()=>true,
  sessionManager:{getSessionId:()=>'one',getSessionFile:()=>'/one.jsonl'}};
const file = path.join(HOME,'.spyhop','omp',process.pid+'.json');
events.session_start({},ctx);
events.agent_start({},ctx);
if(!JSON.parse(fs.readFileSync(file)).busy)throw Error('not busy');
events.agent_end({isTerminal:false},ctx);
if(!JSON.parse(fs.readFileSync(file)).busy)throw Error('ended a non-terminal run');
const sub = {...ctx,agent:{kind:'sub'},sessionManager:{getSessionId:()=>'child',getSessionFile:()=>'/child'}};
events.agent_start({},sub); events.session_shutdown({},sub);
if(JSON.parse(fs.readFileSync(file)).sid!=='one')throw Error('child replaced parent');
ctx.sessionManager.getSessionId=()=>'two';ctx.sessionManager.getSessionFile=()=>'/two.jsonl';
events.session_switch({},ctx);
if(JSON.parse(fs.readFileSync(file)).sid!=='two')throw Error('old session retained');
events.agent_end({},ctx);
if(JSON.parse(fs.readFileSync(file)).busy)throw Error('not idle');
events.session_shutdown({},ctx);
if(fs.existsSync(file))throw Error('registration retained');
'''.replace('CODE', json.dumps(B.OMP_EXTENSION)).replace('HOME', json.dumps(str(self.root)))
        subprocess.run([shutil.which('bun'), '-e', script], check=True, capture_output=True, text=True)


if __name__ == '__main__':
    unittest.main()
