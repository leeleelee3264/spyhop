"""소개 페이지 그림을 데모 데이터로 다시 찍어 assets/ 에 넣는다 (컴퓨터용 png 1600px, 휴대폰용 webp 720px).
  python3 site/shots.py && python3 site/build.py"""
import os
import subprocess
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'macos', 'board', 'tools'))
import demo_screens as D  # noqa: E402

ASSETS = os.path.join(HERE, 'assets')
tag = subprocess.run(['git', '-C', HERE, 'describe', '--tags', '--abbrev=0'], capture_output=True, text=True).stdout.strip()
if tag:
    D.B.VERSION = tag.lstrip('v')
FROZEN = ('.orca{animation:none!important;transform:translateY(45%)!important}*{transition:none!important}'
          '.modal *,.card,.slot{animation:none!important}')


def shot(html, w, h, out, width, fmt, hash_='#x'):
    page = os.path.join(D.TMP, 'shot.html')
    s = open(html, encoding='utf-8').read().replace('location.reload()', '0').replace(
        "fetch('http://127.0.0.1:47613/gen'", "(function(){return new Promise(function(){})})(''")
    open(page, 'w', encoding='utf-8').write(s.replace('</head>', '<style>%s</style></head>' % FROZEN))
    url = 'file://' + page + hash_
    if w < 600:  # 헤드리스 크롬은 아주 좁은 창을 실제보다 넓게 그려서, 휴대폰 폭은 iframe 에 담아 찍는다
        frame = os.path.join(D.TMP, 'frame.html')
        open(frame, 'w').write('<html><body style="margin:0"><iframe src="%s" style="width:%dpx;height:%dpx;border:0;display:block">'
                               '</iframe></body></html>' % (url, w, h))
        url = 'file://' + frame
    raw = os.path.join(D.TMP, 'raw.png')
    subprocess.run([D.CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--window-size=%d,%d' % (w, h),
                    '--force-device-scale-factor=2', '--virtual-time-budget=3500', '--screenshot=' + raw, url],
                   capture_output=True)
    im = Image.open(raw).convert('RGB')
    im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    im.save(os.path.join(ASSETS, out), fmt, **({'quality': 82} if fmt == 'WEBP' else {'optimize': True}))
    print('wrote', out, im.size)


# (그림 이름, 컴퓨터 화면 높이, 휴대폰 화면 높이). 폭은 컴퓨터 1280, 휴대폰 460
for mode, name, h, mh in (('orca', 'board', 600, 442), ('orca', 'bars', 500, 351), ('ai', 'ai-groups', 600, 442)):
    D.patch(mode)
    D.B.build()
    shot(D.B.OUT, 1280, h, name + '.png', 1600, 'PNG')
    shot(D.B.OUT, 460, mh, 'm-%s.webp' % name, 720, 'WEBP')

# 한 판 섹션: My turn 탭만 고른 보드
_cfg = D.B.load_config
D.B.load_config = lambda: dict(_cfg(), filter='wait')
D.patch('orca')
D.B.build()
shot(D.B.OUT, 1280, 600, 'myturn.png', 1600, 'PNG')
shot(D.B.OUT, 460, 442, 'm-myturn.webp', 720, 'WEBP')
D.B.load_config = _cfg

# 상세 창: 교차검증 도우미가 붙은 인증서 교체 세션을 연 모습
D.patch('orca')
D.B.build()
html = open(D.B.OUT, encoding='utf-8').read()
parts = html.split('<div class="modal ')[1:]
modal = '#' + next(x for x in parts if 'Rotate expiring TLS' in x.split('<div class="modal', 1)[0]).split('id="', 1)[1].split('"', 1)[0]
shot(D.B.OUT, 1280, 680, 'detail.png', 1600, 'PNG', modal)
shot(D.B.OUT, 460, 748, 'm-detail.webp', 720, 'WEBP', modal)
