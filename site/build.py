"""소개 페이지를 만든다. 원본은 src.html, 그림·영상은 assets/ (shots.py·frames.py 로 데모 데이터에서 다시 찍는다).
  python3 site/build.py  →  docs/index.html (GitHub Pages), site/share.html (사내 share 판, 커밋하지 않음)"""
import base64, os, re
os.chdir(os.path.dirname(os.path.abspath(__file__)))
s = open('src.html', encoding='utf-8').read()
def emb(m):
    n = m.group(1)
    if n.endswith('.mp4'):
        return 'data:video/mp4;base64,' + base64.b64encode(open('assets/' + n, 'rb').read()).decode()
    return 'data:image/png;base64,' + base64.b64encode(open('assets/%s.png' % n, 'rb').read()).decode()
s = re.sub(r'\{\{([a-z.0-9-]+)\}\}', emb, s)
open('share.html', 'w', encoding='utf-8').write(s.replace('여기 없는 질문은 <a', '여기 없는 질문은 #team-infra 의 Spyhop 스레드나 <a'))  # 사내판만 사내 채널 안내
# 공개판: 사내 제목 관례·사내 채널 언급을 뺀다
p = s.replace('<title>[devops] Spyhop 세션 보드</title>', '<title>Spyhop: AI 세션 보드</title>')
p = p.replace("'[devops] Spyhop 세션 보드'", "'Spyhop: AI 세션 보드'")
p = re.sub(r'<meta name="share-skeleton[^>]*>\n?', '', p)
p = p.replace('imwebShareTheme', 'spyhopTheme')
assert '#team-infra' not in p
open('../docs/index.html', 'w', encoding='utf-8').write(p)
print('ok', len(s), len(p))
