#!/usr/bin/env python3
"""README 스크린샷용 데모 보드를 만든다. 실제 세션·대화 기록 대신 가짜 데이터로 board.py 를 그린다.

  python3 tools/demo_screens.py            # docs/screenshots/*.png 생성 (Google Chrome 필요)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import board as B  # noqa: E402

OUTDIR = os.path.join(ROOT, '..', '..', 'docs', 'screenshots')  # 레포 맨 위 docs
TMP = tempfile.mkdtemp(prefix='spyhop-demo-')
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
NOW = time.time()

WORKTREES = [('w1', 'payments-api', 3), ('w2', 'web-app', 2), ('w3', 'infra', 1)]

# (워크스페이스, 상태, 모델, 몇 분 전, 진전 없음, 제목, 요약, 마지막 답, 단계, TODO)
SESSIONS = [
    ('w1', 'busy', 'Opus 5.5', 4, False, 'Retry logic for failed card captures',
     'Reproduced the double-charge bug and added an idempotency key; now writing retry tests.',
     'Added the idempotency key to the capture call and started the retry test suite.',
     [('Reproduce failure', 'done', 'Replayed the 502 from the gateway log and saw two captures.'),
      ('Idempotency key', 'done', 'Capture requests now send a key derived from the order id.'),
      ('Retry tests', 'now', 'Covering timeout, 502 and duplicate-response cases.'),
      ('Open PR', 'left', 'PR with the fix and tests, then ask for review.')],
     [('Fix double capture', 'done'), ('Retry tests', 'now')]),
    ('w1', 'wait', 'GPT-6.1-Sol medium', 12, False, 'Refund webhook signature check',
     'Signature verification is in place; waiting on whether to reject or log unsigned events.',
     'Asked whether unsigned webhook events should be rejected or only logged for a week.',
     [('Read provider docs', 'done', 'HMAC-SHA256 over the raw body with a timestamp header.'),
      ('Verify signature', 'done', 'Middleware rejects bad signatures with 401.'),
      ('Unsigned events policy', 'now', 'Waiting for a decision: reject now or log for a week.'),
      ('Rollout', 'left', 'Enable in staging, then production.')],
     [('Webhook signature', 'done'), ('Unsigned policy', 'open')]),
    ('w2', 'wait', 'Sonnet 5.5', 25, False, 'Checkout page dark mode',
     'Dark theme tokens are wired up; a quick hotfix for the cart badge was handled on the way.',
     'Dark mode is ready for review; screenshots attached for light and dark.',
     [('Theme tokens', 'done', 'Colors moved to CSS variables.'),
      ('Cart badge hotfix', 'side', 'Fixed the badge overlap reported in the middle of the task.'),
      ('Dark styles', 'done', 'Checkout, cart and payment form.'),
      ('Review', 'now', 'Screenshots shared, waiting for feedback.')],
     [('Dark mode', 'done'), ('Cart badge hotfix', 'done')]),
    ('w2', 'busy', 'Opus 5.5', 9, True, 'Upgrade React Router to v7',
     'Codemods ran on 40 routes; the build is running the full test suite.',
     'Running the full test suite after the codemod.',
     [('Codemod', 'done', 'Converted 40 route files.'),
      ('Fix loaders', 'done', 'Moved data loading into route loaders.'),
      ('Full test run', 'now', 'Long-running suite, about 10 minutes.'),
      ('Remove v6 shims', 'left', 'Delete the compatibility layer.')],
     [('Router upgrade', 'now')]),
    ('w3', 'wait', 'Haiku 4.5', 63, False, 'Shrink staging EKS node pool',
     'Staging nodes are mostly idle at night; proposed a smaller pool and a schedule.',
     'Proposed going from 6 to 3 nodes with a night schedule; waiting for approval.',
     [('Usage check', 'done', 'Average CPU 12% overnight.'),
      ('Proposal', 'now', '6 to 3 nodes plus a night schedule.'),
      ('Apply', 'left', 'Change the node group after approval.')],
     [('Right-size staging', 'open')]),
    ('w3', 'busy', 'Fable 5.1', 2, False, 'Rotate expiring TLS certificates',
     'Two certificates expire this month; renewing and swapping them one at a time.',
     'Renewed the first certificate and swapped it on the load balancer.',
     [('Find expiring certs', 'done', '2 certificates expire within 30 days.'),
      ('Renew first', 'done', 'api.example.com renewed and attached.'),
      ('Renew second', 'now', 'www.example.com renewal in progress.'),
      ('Verify', 'left', 'Check the chain from outside.')],
     [('Cert rotation', 'now')]),
]

# 오르카 밖 터미널에서 돌리는 세션 하나 (칸 = 폴더 · 터미널)
OUTSIDE = ('scripts', 'iTerm2', 'wait', 'GPT-6.1-Sol medium', 6, 'Nightly backup check script',
           'Wrote a script that checks last night\'s backups and posts a summary.',
           'The script is ready; asked whether to run it from cron or a CI schedule.',
           [('Read backup logs', 'done', 'Backups land in one bucket per database.'),
            ('Write checker', 'done', 'Flags any database without a backup in 26 hours.'),
            ('Schedule', 'now', 'Waiting: cron on the bastion or a CI schedule.')],
           [('Backup checker', 'done'), ('Schedule', 'open')])

# 인증서 교체 세션이 오르카로 띄운 Codex 교차검증 창 하나 (카드 아래 도우미 한 줄, 상세 창의 Helpers)
HELPER = (5, 'Cross-check cert rotation', 'Cross-check passed',
          'The renewed certificate chains correctly from outside. The old one is still on the staging listener; remove it after the second swap.')

GROUPS = {0: 'Payments', 1: 'Payments', 2: 'Frontend', 3: 'Frontend', 4: 'Infra', 5: 'Infra', 6: 'Infra'}


def setup():
    terms, agents, steps = [], {}, {}
    for i, (wid, st, model, mins, stuck, title, summary, reply, flow, todo) in enumerate(SESSIONS):
        log = os.path.join(TMP, 'session-%d.jsonl' % i)
        open(log, 'w').write('{}\n')
        t_ago = NOW - mins * 60
        os.utime(log, (NOW - (600 if stuck else 5), NOW - (600 if stuck else 5)))
        h = 'term_demo%d' % i
        terms.append({'handle': h, 'tabId': 'tab%d' % i, 'leafId': 'leaf%d' % i, 'worktreeId': wid, 'title': title,
                      'ptyId': wid + '@@x', 'lastOutputAt': t_ago * 1000, 'log': log, '_model': model, '_mins': mins})
        agents['tab%d:leaf%d' % (i, i)] = {'state': 'working' if st == 'busy' else 'done', 'stateStartedAt': t_ago * 1000}
        steps[log] = {'size': os.path.getsize(log), 'pos': 1, 'at': NOW, 'ok_at': NOW, 'title': title, 'summary': summary,
                      'last_reply': reply,
                      'steps': [{'label': a, 'state': b, 'detail': c} for a, b, c in flow],
                      'items': [{'label': a, 'state': b, 'detail': ''} for a, b in todo]}
    i, title, _, _ = HELPER
    if i < len(SESSIONS):  # 시험이 세션 목록을 줄여 쓰면 도우미를 붙일 세션이 없다
        log = os.path.join(TMP, 'helper.jsonl')
        open(log, 'w').write('{}\n')
        terms.append({'handle': 'term_demoh', 'tabId': 'tab%d' % i, 'leafId': 'leafh', 'worktreeId': SESSIONS[i][0], 'title': title,
                      'ptyId': SESSIONS[i][0] + '@@x', 'lastOutputAt': (NOW - 60) * 1000, 'log': log, '_model': 'GPT-6.1-Sol', '_mins': 3})
        agents['tab%d:leafh' % i] = {'state': 'done', 'agentType': 'codex', 'stateStartedAt': (NOW - 180) * 1000}
    folder, app, st, model, mins, title, summary, reply, flow, todo = OUTSIDE
    log = os.path.join(TMP, 'session-%d.jsonl' % len(SESSIONS))
    open(log, 'w').write('{}\n')
    wid = 'term:%s:/demo/%s' % (app, folder)
    outside = {'handle': 'proc_9001', 'tabId': 'proc', 'leafId': '9001', 'worktreeId': wid, 'worktreePath': '/demo/' + folder,
               'title': title, 'ptyId': '', 'lastOutputAt': (NOW - mins * 60) * 1000, 'log': log, '_model': model, '_mins': mins,
               '_ext': app, '_proc': {'pid': 9001, 'kind': 'codex', 'start': NOW - mins * 60}, '_pkind': 'codex',
               'agent': {'state': 'done', 'stateStartedAt': (NOW - mins * 60) * 1000}}
    steps[log] = {'size': 3, 'pos': 1, 'at': NOW, 'ok_at': NOW, 'title': title, 'summary': summary, 'last_reply': reply,
                  'steps': [{'label': a, 'state': b, 'detail': c} for a, b, c in flow],
                  'items': [{'label': a, 'state': b, 'detail': ''} for a, b in todo]}
    owt = {wid: {'id': wid, 'displayName': '%s · %s' % (folder, app), 'path': '/demo/' + folder, 'sortOrder': -1}}
    return terms, agents, steps, outside, owt


def patch(mode):
    terms, agents, steps, outside, owt = setup()
    by_log = {t['log']: t for t in terms + [outside]}

    def fake_orca(*args):
        if args[:2] == ('worktree', 'list'):
            return {'worktrees': [{'id': w, 'displayName': n, 'path': '/demo/' + n, 'sortOrder': o} for w, n, o in WORKTREES]}
        if args[:2] == ('terminal', 'list'):
            return {'terminals': [dict(t) for t in terms]}
        if args[:2] == ('orchestration', 'run-list'):
            return {'runs': [{'id': 'run1', 'coordinator_pane_key': 'tab%d:leaf%d' % (HELPER[0], HELPER[0])}]}
        if args[:2] == ('orchestration', 'inbox'):
            return {'messages': [{'sender_pane_key': 'tab%d:leafh' % HELPER[0], 'run_id': 'run1', 'type': 'worker_done',
                                  'subject': HELPER[2], 'body': HELPER[3], 'created_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(NOW - 60))}]}
        return {}
    B.orca = fake_orca
    B.agent_procs = lambda: {}             # 이 맥에서 실제로 도는 세션이 데모 화면에 섞이지 않게
    B.outside_terms = lambda: ([dict(outside)], dict(owt))
    B.orca_agents = lambda: agents
    B.layout_handles = lambda: {t['handle'] for t in terms}
    B.match_sessions = lambda ts, ws: [t.update(log=by_log_title[t['title']]) for t in ts]
    by_log_title = {t['title']: t['log'] for t in terms + [outside]}
    B.summarize = lambda log: steps[log]
    B.cached_summary = lambda log: steps.get(log)  # 보드는 저장된 요약을 읽는다
    B.summarize_later = lambda logs: None
    B.read_tail = lambda h: []
    B.model_of = lambda log: by_log[log]['_model'] if log in by_log else ''
    B.turn_times = lambda log: ((NOW - by_log[log]['_mins'] * 60), (NOW - by_log[log]['_mins'] * 60)) if log in by_log else (None, None)
    B.current_theme = lambda: 'classic'
    # 요약 모델은 누구나 고를 수 있는 Claude CLI 로 보여 준다 (이 맥의 설정이 사진에 찍히지 않게)
    B.summarizers = lambda: [{'id': 'claude', 'label': 'Claude (claude CLI)', 'models': [{'id': 'claude:claude-haiku-4-5', 'name': 'Haiku 4.5'}, {'id': 'claude:claude-sonnet-5-5', 'name': 'Sonnet 5.5'}]},
                             {'id': 'codex', 'label': 'Codex (codex CLI)', 'models': [{'id': 'codex:gpt-6.1-sol', 'name': 'GPT-6.1-Sol'}]}]
    B.current_summarizer = lambda: 'claude:claude-haiku-4-5'
    B.orcas_on = lambda: True
    B.group_mode = lambda: mode
    B.assign_groups = lambda items: None
    B.group_of = lambda key, groups=None: GROUPS[int(os.path.basename(key).split('-')[1].split('.')[0])]
    B.load_groups = lambda: {'groups': ['Payments', 'Frontend', 'Infra'], 'assign': {}}
    B.OUT = os.path.join(TMP, 'board-%s.html' % mode)
    B.STATE = os.path.join(TMP, 'state-%s.json' % mode)


def shot(html, name, w, h, hash_='#x', css=''):
    page = os.path.join(TMP, name + '.html')
    s = open(html, encoding='utf-8').read()
    s = s.replace('location.reload()', '0')   # 데모 화면은 새로고침하지 않는다
    s = s.replace("fetch('http://127.0.0.1:47613/gen'", "(function(){return new Promise(function(){})})(''")  # 실제 보드에 묻지 않게
    s = s.replace('</head>', '<style>%s</style></head>' % css)
    open(page, 'w', encoding='utf-8').write(s)
    out = os.path.join(OUTDIR, name + '.png')
    subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--window-size=%d,%d' % (w, h),
                    '--force-device-scale-factor=2', '--virtual-time-budget=1500', '--screenshot=' + out,
                    'file://' + page + hash_], capture_output=True)
    print('wrote', out)


FROZEN_ORCAS = ('.orca{animation:none!important;transform:translateY(6%)!important}')


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    # 레포에서 돌리면 제목 옆 버전이 dev 로 찍힌다. 사진에는 마지막 릴리즈 번호를 쓴다
    tag = subprocess.run(['git', '-C', ROOT, 'describe', '--tags', '--abbrev=0'], capture_output=True, text=True).stdout.strip()
    if tag:
        B.VERSION = tag.lstrip('v')
    patch('orca')
    B.build()
    board = B.OUT
    html = open(board, encoding='utf-8').read()
    # 범고래는 멈춘 모습으로 두 마리
    html = html.replace('setTimeout(pop,300+Math.random()*1500);', 'pop();pop();')
    open(board, 'w', encoding='utf-8').write(html)
    shot(board, 'board', 1280, 560, css=FROZEN_ORCAS)
    shot(board, 'settings', 1280, 980, hash_='#settings', css=FROZEN_ORCAS + '#mcpu,#mmem{visibility:hidden}')
    first = html.split('class="modal ', 1)[1].split('id="', 1)[1].split('"', 1)[0]
    # 상세 창이 열리는 효과 중간에 찍히면 반투명하게 나온다. 효과를 끄고 다 열린 모습으로 찍는다
    shot(board, 'detail', 1280, 640, hash_='#' + first, css=FROZEN_ORCAS + '.modal,.modal *{animation:none!important;transition:none!important}')
    patch('ai')
    B.build()
    shot(B.OUT, 'ai-groups', 1280, 560)
    # 메뉴바 패널: 데모 상태를 바로 그리게 한다
    panel = open(os.path.join(ROOT, 'panel.html'), encoding='utf-8').read().replace(
        '__LOGO__', B.orca_art.tile(uid='pl').replace('<svg ', '<svg width="22" height="22" ', 1))
    state = open(os.path.join(TMP, 'state-orca.json'), encoding='utf-8').read()
    panel = panel.replace("function load(){fetch('/state.json',{cache:'no-store'}).then(function(r){return r.json()}).then(render).catch(function(){})}",
                          'function load(){render(%s)}' % state)
    p = os.path.join(TMP, 'panel-demo.html')
    open(p, 'w', encoding='utf-8').write(panel)
    # 헤드리스 크롬은 아주 좁은 창을 실제보다 넓게 그려서, 패널 폭(380px) 그대로 iframe 에 담아 찍는다
    frame = os.path.join(TMP, 'panel-frame.html')
    open(frame, 'w').write('<html><body style="margin:0;background:#f7f8fa"><iframe src="file://%s" '
                           'style="width:380px;height:560px;border:0;display:block"></iframe></body></html>' % p)
    out = os.path.join(OUTDIR, 'panel.png')
    subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--window-size=380,560',
                    '--force-device-scale-factor=2', '--virtual-time-budget=1500', '--screenshot=' + out, 'file://' + frame],
                   capture_output=True)
    print('wrote', out)
    shutil.rmtree(TMP, ignore_errors=True)


if __name__ == '__main__':
    main()
