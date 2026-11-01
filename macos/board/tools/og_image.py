#!/usr/bin/env python3
"""링크 미리보기(og:image)용 docs/og.png 를 만든다. 홍보 썸네일과 같은 Very Peri 보라 스타일이다.

  python3 tools/og_image.py

og.png 는 디스코드·X·슬랙·GitHub 에 링크를 붙일 때 가장 먼저 보이는 한 장이다.
미리보기는 폭 400px 안팎으로 작게 보이므로 보드 전체 캡처 대신 큰 글자 두 줄 + 카드 3장으로 그린다.
GitHub Social preview 권장 크기(1280x640)를 2배로 찍는다.
"""
import os
import subprocess
import tempfile

from PIL import Image

import demo_screens as D

DOCS = os.path.join(D.ROOT, '..', '..', 'docs')
OUT = os.path.join(DOCS, 'og.png')
LOGO = open(os.path.join(DOCS, 'logo.svg')).read().replace('<svg ', '<svg width="34" height="34" ')

W, H = 1280, 640
PERI = '#6667ab'            # Pantone 2022 Very Peri
GREEN, PINK, YELLOW, PURPLE, GREY = '#2fa86f', '#e05a8f', '#e0a400', '#9b7bea', '#c3c8d4'
DOT = {'done': 'background:' + GREEN, 'now': 'background:' + YELLOW, 'intercept': 'background:' + PURPLE,
       'next': 'background:#fff;box-shadow:inset 0 0 0 2px ' + GREY}

# (칸 이름, 상태, 모델, 제목, 나이, [(단계, 상태)])
COLUMNS = [
    ('payments-api', 'My turn', 'GPT-6.1-Sol', 'Refund webhook signature check', '12m',
     [('Read provider docs', 'done'), ('Verify signature', 'done'), ('Unsigned events policy', 'done'), ('Rollout', 'next')]),
    ('web-app', 'Working', 'Opus 5.5', 'Upgrade React Router to v7', '9m',
     [('Codemod', 'done'), ('Fix loaders', 'done'), ('Full test run', 'now'), ('Remove v6 shims', 'next')]),
    ('infra', 'My turn', 'Sonnet 5.5', 'Checkout page dark mode', '25m',
     [('Theme tokens', 'done'), ('Cart badge hotfix', 'intercept'), ('Dark styles', 'done'), ('Review', 'now')]),
]

CSS = """*{box-sizing:border-box;margin:0}
body{width:%dpx;height:%dpx;overflow:hidden;position:relative;background:%s;color:#fff;font-family:-apple-system,'Helvetica Neue',sans-serif}
.big{position:absolute;left:70px;top:52px;font-size:80px;font-weight:800;letter-spacing:-.03em;line-height:1.02}
.big em{font-style:normal;color:rgba(255,255,255,.55)}
.brand{position:absolute;right:70px;top:66px;display:flex;align-items:center;gap:12px;font-size:24px;font-weight:700;opacity:.9}
.col{position:absolute;top:250px;width:370px;height:400px;border-radius:18px;background:rgba(255,255,255,.14);padding:22px 26px;font-size:22px;font-weight:700}
.card{position:absolute;top:308px;width:328px;background:#fff;border-radius:9px;border-left:5px solid var(--c);padding:12px 17px 16px;
  box-shadow:0 16px 40px rgba(20,15,60,.35);color:#1d2538}
.hd{display:flex;align-items:center;gap:8px;font-size:12px}
.hd b{color:var(--c)}
.hd span{background:#eef0f4;color:#4a5265;border-radius:5px;padding:2px 6px;font-size:10px}
.hd em{margin-left:auto;font-style:normal;color:#8a92a3;font-size:10px}
h3{font-size:16px;font-weight:700;margin:9px 0 11px;letter-spacing:-.01em}
ul{list-style:none;padding:0;position:relative}
ul:before{content:'';position:absolute;left:5px;top:8px;bottom:8px;width:2px;background:#e3e6ec}
li{position:relative;padding-left:22px;font-size:13px;line-height:23px;color:#3a4255}
li i{position:absolute;left:0;top:6px;width:12px;height:12px;border-radius:50%%}
li.now{font-weight:700;color:#1d2538}
li.next{color:#9aa1b1}
""" % (W, H, PERI)


def column(i, name, status, model, title, age, steps):
    left = 70 + i * 385
    lis = ''.join('<li class="%s"><i style="%s"></i>%s</li>' % (st, DOT[st], text) for text, st in steps)
    return ('<div class="col" style="left:%dpx">%s</div>'
            '<div class="card" style="left:%dpx;--c:%s"><div class="hd"><b>%s</b><span>%s</span><em>%s</em></div>'
            '<h3>%s</h3><ul>%s</ul></div>'
            % (left, name, left + 18, GREEN if status == 'My turn' else PINK, status, model, age, title, lis))


def main():
    body = ('<div class="big">Every session.<br><em>One board.</em></div><div class="brand">%s Spyhop</div>' % LOGO
            + ''.join(column(i, *c) for i, c in enumerate(COLUMNS)))
    tmp = tempfile.mkdtemp(prefix='spyhop-og-')
    page, png = os.path.join(tmp, 'og.html'), os.path.join(tmp, 'og.png')
    with open(page, 'w') as f:
        f.write('<!doctype html><html><head><meta charset="utf-8"><style>%s</style></head><body>%s</body></html>' % (CSS, body))
    # 헤드리스 창은 --window-size 보다 80px 짧게 그려져서 크게 찍고 자른다
    subprocess.run([D.CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--window-size=%d,%d' % (W, H + 80),
                    '--force-device-scale-factor=2', '--virtual-time-budget=1500', '--screenshot=' + png, 'file://' + page],
                   capture_output=True, timeout=60)
    Image.open(png).convert('RGB').crop((0, 0, W * 2, H * 2)).save(OUT, optimize=True)
    print(OUT)


if __name__ == '__main__':
    main()
