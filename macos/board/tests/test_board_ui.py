"""실제 브라우저에서 갱신·좁은 화면 회귀를 확인한다. 실제 세션과 외부 API는 사용하지 않는다."""
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))
import board as B
import demo_screens as D

CHROME = os.environ.get('SPYHOP_CHROME') or shutil.which('chromium') or shutil.which('google-chrome') or D.CHROME


@unittest.skipUnless(Path(CHROME).is_file(), 'Chrome/Chromium required (or set SPYHOP_CHROME)')
class BoardUITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='spyhop-ui-')
        cls.root = Path(cls.tmp.name)
        saved, demo = dict(vars(B)), (D.TMP, D.SESSIONS, D.OUTSIDE)
        try:
            D.TMP = str(cls.root)
            D.SESSIONS = []
            for i in range(12):
                session = list(demo[1][0])
                session[1], session[3], session[5] = 'wait', i + 5, 'QA session %d' % i
                D.SESSIONS.append(tuple(session))
            cls.pages = {}
            sessions = D.SESSIONS
            for state in ('assigned', 'changed', 'short', 'pending', 'empty'):
                D.SESSIONS = sessions[:3] if state == 'short' else sessions
                D.OUTSIDE = list(demo[2])
                D.OUTSIDE[4] = 1 if state == 'changed' else 60
                D.patch('ai')
                for key, filename in [('BASE', ''), ('CONFIG', 'config.json'), ('GROUPS_FILE', 'groups.json'),
                                      ('MOVED_FILE', 'moved.json'), ('TRACE', 'trace.json')]:
                    setattr(B, key, str(cls.root / filename))
                B.load_config = lambda: {'sort': 'recent'}
                B.token = lambda: ''
                B.load_groups = lambda: {'groups': ['QA', 'Other'], 'assign': {}}
                outside_log = str(cls.root / ('session-%d.jsonl' % len(D.SESSIONS)))
                B.group_of = lambda key, groups=None: 'Other' if key == outside_log else 'QA'
                if state == 'pending':
                    B.group_of = lambda key, groups=None: B.UNSORTED
                if state == 'empty':
                    B.orca = lambda *args: {'worktrees': [], 'terminals': []}
                    B.outside_terms = lambda: ([], {})
                B.build()
                cls.pages[state] = Path(B.OUT).read_text()
        finally:
            vars(B).update(saved)
            D.TMP, D.SESSIONS, D.OUTSIDE = demo

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def browser(self, initial, script, width=1280):
        # 요청 응답만 대체하고 실제 보드의 live(), fit(), CSS를 실행한다.
        pages = json.dumps(self.pages).replace('</', '<\\/')
        stub = ('<script>window.__qaPages=' + pages + ';window.__qaNext=__qaPages.assigned;'
                'window.fetch=function(url){return String(url).includes("/?auto=1")?'
                'Promise.resolve({ok:true,text:()=>Promise.resolve(__qaNext)}):new Promise(()=>{})};'
                'window.setInterval=function(){return 0};</script>')
        run = ('<script>(async function(){try{const tick=()=>new Promise(r=>setTimeout(r,50));'
               + script + ';const p=document.createElement("pre");p.id="qa-result";'
               'p.textContent=JSON.stringify(result);document.body.appendChild(p);'
               'if(parent!==window)parent.postMessage({spyhopQA:result},"*")'
               '}catch(e){const p=document.createElement("pre");p.id="qa-result";'
               'p.textContent=JSON.stringify({error:String(e)});document.body.appendChild(p);'
               'if(parent!==window)parent.postMessage({spyhopQA:{error:String(e)}},"*")}})()</script>')
        document = self.pages[initial].replace('<head>', '<head>' + stub, 1)
        document = document.replace('</head>', '<style>*{animation:none!important;transition:none!important}</style></head>')
        document = document.replace('</body>', run + '</body>')
        page = self.root / (self._testMethodName + '.html')
        page.write_text(document)
        frame = self.root / (self._testMethodName + '-frame.html')
        frame.write_text('<script>addEventListener("message",function(e){if(!e.data.spyhopQA)return;'
                         'const p=document.createElement("pre");p.id="qa-result";'
                         'p.textContent=JSON.stringify(e.data.spyhopQA);document.body.appendChild(p)})</script>'
                         '<iframe src="%s" style="border:0;width:%dpx;height:700px"></iframe>' % (page.as_uri(), width))
        output = subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--disable-background-networking',
                                 '--no-first-run', '--no-default-browser-check',
                                 '--user-data-dir=' + str(self.root / self._testMethodName),
                                 '--window-size=1280,900', '--virtual-time-budget=5000', '--dump-dom',
                                 page.as_uri() if width == 1280 else frame.as_uri()],
                                capture_output=True, text=True, timeout=30, check=True)
        match = re.search(r'<pre id="qa-result">(.*?)</pre>', output.stdout, re.S)
        self.assertIsNotNone(match, output.stderr[-2000:])
        result = json.loads(html.unescape(match.group(1)))
        self.assertNotIn('error', result, result)
        return result

    def test_version_tooltip_gap_remains_inside_badge_hit_area(self):
        result = self.browser('assigned', '''
            // 앱 보드는 새 버전 알림이 있을 때만 제목 옆에 배지를 그린다. 없으면 그 자리에 붙여서 잰다
            let badge=document.getElementById('ver');if(!badge){badge=document.createElement('span');badge.id='ver';document.querySelector('.subbar h1').after(badge)}
            badge.className='ver new';
            badge.innerHTML='v0.6.0<span class="vtip"><b>Updated</b> from v0.5.0<a href="#">Release notes</a></span>';
            const tip=badge.querySelector('.vtip');tip.style.display='block';
            const b=badge.getBoundingClientRect(),t=tip.getBoundingClientRect();
            const x=b.left+b.width/2,y=(b.bottom+t.top)/2;
            const hit=document.elementFromPoint(x,y);
            const result={gap:t.top-b.bottom,connected:!!hit.closest('#ver')};
        ''')
        self.assertGreater(result['gap'], 0)
        self.assertTrue(result['connected'])

    def test_column_scroll_survives_refresh_and_reordering(self):
        result = self.browser('assigned', '''
            const column=()=>document.querySelector('[data-wid="group:QA"]');
            column().scrollTop=160;const before=column().scrollTop;
            const order=()=>Array.from(document.querySelectorAll('main .col'),c=>c.dataset.wid);
            const oldOrder=order();__qaNext=__qaPages.changed;await live();await tick();
            const result={before,after:column().scrollTop,oldOrder,newOrder:order()}
        ''')
        self.assertEqual(result['before'], 160)
        self.assertNotEqual(result['oldOrder'], result['newOrder'])
        self.assertEqual(result['after'], result['before'])

    def test_sorting_notice_tracks_live_transitions(self):
        result = self.browser('pending', '''
            const notice=()=>Array.from(document.querySelectorAll('.none')).filter(p=>
                p.textContent.includes('Sorting new sessions')&&p.getBoundingClientRect().height>0).length;
            const counts=[notice()];
            for(const state of ['assigned','empty','pending','assigned']){
                __qaNext=__qaPages[state];await live();await tick();counts.push(notice())}
            const result={counts,cards:document.querySelectorAll('main .card').length}
        ''')
        self.assertEqual(result['counts'], [1, 0, 0, 1, 0])
        self.assertEqual(result['cards'], 13)

    def test_column_scroll_clamps_when_cards_no_longer_overflow(self):
        result = self.browser('assigned', '''
            const column=()=>document.querySelector('[data-wid="group:QA"]');
            column().scrollTop=160;const before=column().scrollTop;
            __qaNext=__qaPages.short;await live();await tick();
            const result={before,after:column().scrollTop,height:column().clientHeight,total:column().scrollHeight}
        ''')
        self.assertEqual(result['before'], 160)
        self.assertEqual(result['after'], 0)
        self.assertLessEqual(result['total'], result['height'])

    def test_tabs_and_sort_fit_phone_width(self):
        result = self.browser('assigned', '''
            await tick();const tabs=Array.from(document.querySelectorAll('.tabs .tab'),b=>b.getBoundingClientRect());
            const sort=document.querySelector('.sortb').getBoundingClientRect();
            const result={width:innerWidth,ys:tabs.map(b=>Math.round(b.y)),right:Math.max(sort.right,...tabs.map(b=>b.right)),scroll:document.documentElement.scrollWidth}
        ''', width=390)
        self.assertEqual(result['width'], 390)
        self.assertEqual(len(set(result['ys'])), 1)  # 탭 셋이 한 줄
        self.assertLessEqual(result['right'], 390)   # 정렬 메뉴까지 화면 안
        self.assertLessEqual(result['scroll'], 390)  # 가로 스크롤 없음

if __name__ == '__main__':
    unittest.main()
