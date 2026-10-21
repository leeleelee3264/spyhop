# 스파이홉(몸을 세우고 머리만 내민) 범고래 - 앱 아이콘·파비콘·메뉴바·헤더 애니메이션 공용
# 그림은 보드 애니메이션의 범고래(36x64)를 그대로 쓰고, 아이콘은 머리 쪽만 32x32 타일에 담는다
BODY = 'M22 3C28 3 30 9 29 17L28 36C28 47 25 55 21 59L28 62L19 61L11 63L16 57C10 48 7 37 8 24C8 13 12 6 18 4Q20 3 22 3Z'
FLIPPER = 'M24 29Q32 33 32 40Q27 39 22 33Z'
CHIN = 'M28 10Q30 14 28 23L26 39Q22 42 21 35L23 23Q27 18 28 10Z'
EYE = 'M15 12C12 13 12 17 15 18C18 19 21 16 21 13C20 11 17 11 15 12Z'
SADDLE = 'M9 40Q13 36 16 40L15 46Q11 44 9 40Z'
FIT = 'translate(1.5 2) scale(.82)'  # 36x64 그림의 머리 쪽을 32x32 타일 위쪽에
WAVE = 'M3 27.2 Q7 25.3 11 27.2 T19 27.2 T27 27.2'
BLUE = '#3182f6'


def whale(stroke='currentColor'):
    """애니메이션용 전신 범고래 (viewBox 0 0 36 64)."""
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 36 64" width="100%%" height="100%%" aria-hidden="true">'
            '<g stroke="%s" stroke-width=".7" stroke-linejoin="round"><path fill="#10131a" d="%s"/>'
            '<path fill="#fff" stroke="none" d="%s"/><path fill="#fff" stroke="none" d="%s"/>'
            '<path fill="#9299a5" stroke="none" d="%s"/><path fill="#10131a" d="%s"/><path fill="none" d="M25 10Q27 11 29 10"/>'
            '<circle cx="24" cy="16" r=".8" fill="#10131a" stroke="none"/></g></svg>') % (stroke, BODY, CHIN, EYE, SADDLE, FLIPPER)


def tile(bg=BLUE, uid='t'):
    """앱 아이콘·파비콘: 파란 타일, 물 위로 머리를 내민 범고래."""
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
            '<defs><clipPath id="%s"><rect width="32" height="26.2"/></clipPath></defs>'
            '<rect width="32" height="32" rx="8" fill="%s"/>'
            '<g clip-path="url(#%s)"><g transform="%s"><g stroke="#0b1220" stroke-width=".7" stroke-linejoin="round">'
            '<path fill="#10131a" d="%s"/><path fill="#fff" stroke="none" d="%s"/><path fill="#fff" stroke="none" d="%s"/>'
            '<path fill="#10131a" d="%s"/><circle cx="24" cy="16" r=".8" fill="#10131a" stroke="none"/></g></g></g>'
            '<path d="%s" fill="none" stroke="#fff" stroke-width="2.2" stroke-linecap="round"/></svg>') % (
            uid, bg, uid, FIT, BODY, CHIN, EYE, FLIPPER, WAVE)


def favicon():
    return tile()


MB_FIT = 'translate(-6 -3) scale(1.25)'  # 메뉴바(20pt)에서는 머리를 크게 채운다
MB_WAVE = 'M1 28.6 Q6 26.4 11 28.6 T21 28.6 T31 28.6'


def template():
    # 메뉴바용: 검은 실루엣 한 색, 흰 무늬는 뚫는다(macOS 가 다크/라이트에 맞춰 칠함)
    # 작게 보이니 같은 그림을 크게 담고, 가는 무늬(턱)는 두껍게 뚫고, 지느러미는 뺀다(뭉개져서 얼룩처럼 보인다)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
            '<mask id="m"><rect width="32" height="27" fill="#fff"/><g transform="%s" fill="#000">'
            '<path d="%s" stroke="#000" stroke-width="1.8" stroke-linejoin="round"/><path d="%s"/></g></mask>'
            '<g mask="url(#m)"><g transform="%s" fill="#000"><path d="%s"/></g></g>'
            '<path d="%s" fill="none" stroke="#000" stroke-width="2.8" stroke-linecap="round"/></svg>') % (
            MB_FIT, CHIN, EYE, MB_FIT, BODY, MB_WAVE)


def mono(bg=BLUE, fg='#ffffff'):
    # 한 색 타일: 바탕 위에 한 색 범고래(무늬는 뚫어서 바탕색이 보이게)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="8" fill="%s"/>'
            '<mask id="mm"><rect width="32" height="26.2" fill="#fff"/><g transform="%s" fill="#000"><path d="%s"/><path d="%s"/></g></mask>'
            '<g mask="url(#mm)"><g transform="%s" fill="%s"><path d="%s"/><path d="%s"/></g></g>'
            '<path d="%s" fill="none" stroke="%s" stroke-width="2" stroke-linecap="round"/></svg>') % (
            bg, FIT, CHIN, EYE, FIT, fg, BODY, FLIPPER, WAVE, fg)


if __name__ == '__main__':
    import sys
    out = sys.argv[1]
    open(out + '/fav.svg', 'w').write(favicon())
    open(out + '/tpl.svg', 'w').write(template())
