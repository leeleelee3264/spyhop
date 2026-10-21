#!/usr/bin/env python3
# <swiftbar.title>세션 보드</swiftbar.title>
# <swiftbar.hideRunInTerminal>true</swiftbar.hideRunInTerminal>
# <swiftbar.hideLastUpdated>true</swiftbar.hideLastUpdated>
# <swiftbar.hideDisappear>true</swiftbar.hideDisappear>
# <swiftbar.hideAbout>true</swiftbar.hideAbout>
"""메뉴바 항목: 오르카 세션 요약을 보여주고, 누르면 그 창으로 이동한다.
board.py 감시가 꺼져 있으면 Claude·Codex 가 떠 있을 때 다시 켠다."""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.realpath(__file__))
BOARD = os.path.join(os.path.dirname(HERE), 'board.py')
sys.path.insert(0, os.path.dirname(HERE))
import board
STATE = '/tmp/progress-board/state.json'
PIDFILE = '/tmp/progress-board/watch.pid'
ORCA = '/usr/local/bin/orca'


def watcher_alive():
    return board.watching(PIDFILE)


def agents_running():
    # 보드와 같은 수집기를 써서 OMP를 포함한 실제 세션만 감지한다.
    return bool(board.agent_pids())


def ensure_watcher():
    if not watcher_alive() and agents_running():
        os.makedirs('/tmp/progress-board', exist_ok=True)
        subprocess.Popen(['/usr/bin/python3', BOARD, '--ensure'], stdout=subprocess.DEVNULL,
                         stderr=open('/tmp/progress-board/watch.log', 'a'), start_new_session=True)


def server_up():
    import socket
    try:
        socket.create_connection(('127.0.0.1', 47613), timeout=0.3).close()
        return True
    except OSError:
        return False


def waited(sec):
    sec = max(0, int(time.time() - sec))
    return 'now' if sec < 60 else '%dm' % (sec // 60) if sec < 3600 else '%dh' % (sec // 3600)


def q(x):
    # 따옴표로 감싸는 값 안의 따옴표는 바꾼다
    return x.replace('"', "'")


def clean(x):
    return (x or '').replace('|', '/').replace('\n', ' ')


STEP_MARK = {'done': '✅', 'now': '🟠', 'blocked': '❗', 'left': '⚪'}
STEP_ICON = {'done': ('checkmark.circle.fill', '#22a06b'), 'now': ('circle.inset.filled', '#e2a300'),
             'blocked': ('exclamationmark.circle.fill', '#e2483d'), 'left': ('circle.dotted', '#8590a2')}
ORCA_ICON = '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'  # 앱 아이콘과 같은 파란 타일(색 그대로). 한 색 템플릿은 메뉴바에서 잘 안 보였다  # 스파이홉 범고래 (메뉴바 색에 맞춰 칠해지는 템플릿 이미지)
SWITCH = 'bash=%s param1=terminal param2=switch param3=--terminal param4=%%s terminal=false' % ORCA


def main():
    ensure_watcher()
    try:
        with open(STATE, encoding='utf-8') as f:
            state = json.load(f)
    except (OSError, ValueError):
        state = {'at': 0, 'sessions': []}
    stale = time.time() - state.get('at', 0) > 120
    ss = [] if stale else state['sessions']
    wait = [s for s in ss if s['status'] == 'wait']
    busy = [s for s in ss if s['status'] == 'busy']

    # 메뉴바: 칸반 모양 단색 아이콘 + 내 차례 수. 누르면 보드 패널(웹뷰)이 뜬다
    icon = 'rectangle.split.3x1.fill' if wait else 'rectangle.split.3x1'
    text = str(len(wait)) if wait else ('' if not ss else '·%d' % len(busy))
    if server_up():
        print('%s | image=%s width=20 height=20 href=http://127.0.0.1:47613/panel webview=true webvieww=380 webviewh=560' % (text, ORCA_ICON))
        return
    print('%s | image=%s width=20 height=20' % (text, ORCA_ICON))
    print('---')
    print('My turn %d · Working %d | size=13' % (len(wait), len(busy)))

    ws = None
    for s in ss:
        if s['ws'] != ws:
            ws = s['ws']
            print('---')
            print('📁  %s | size=12' % clean(ws))
        mark = '🔴' if s['status'] == 'wait' else '🔵'
        progress = '%d/%d' % (s['done'], s['total']) if s['total'] else '—'
        when = waited(s['since']) + (' waiting' if s['status'] == 'wait' else '')
        title = clean(s['title'])
        if len(title) > 30:
            title = title[:29] + '…'
        print('%s  %s    %s · %s | tooltip="%s"' % (mark, title, progress, when, q(clean(s.get('summary'))[:200] or title)))
        # 옆으로 펼치는 메뉴: 요약 → 단계 → 모델 → 이동
        if s.get('summary'):
            print('--%s | size=11 length=60 tooltip="%s"' % (clean(s['summary']), q(clean(s['summary']))))
            print('-----')
        for st in s.get('steps') or []:
            print('--%s  %s | size=13' % (STEP_MARK.get(st['state'], '⚪'), clean(st['label'])))
        print('-----')
        if s.get('model'):
            print('--🧠  %s | size=12' % clean(s['model']))
        print('--↗  Go to session | %s' % (SWITCH % s['handle']))

    print('---')
    print('🗂  Open board | bash=/usr/bin/open param1=/tmp/progress-board/index.html terminal=false')
    if stale:
        print('💤 Watcher off · starts automatically when Claude/Codex runs | size=11')


if __name__ == '__main__':
    main()
