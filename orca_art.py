# 스파이홉(머리만 내민) 범고래 실루엣 - 파비콘·메뉴바·헤더 애니메이션 공용
BODY = 'M9.6 31 C9 23 9.8 15.6 12 10.2 C13.4 6.8 15.2 4.6 16.9 4.4 C18.7 4.3 20 6.2 20.8 9.2 C22 13.6 22.5 20 22.6 31 Z'
EYE = '<ellipse cx="18.4" cy="12.2" rx="1.25" ry="3.1" transform="rotate(-12 18.4 12.2)"/>'
CHIN = 'M12.4 9.6 C11.1 13.4 10.4 19 10.6 26 L14.6 26 C14 20.2 13.7 14.8 13.9 7.6 C13.3 8.2 12.8 8.9 12.4 9.6 Z'
WAVE = 'M0 25.5 Q4 23.6 8 25.5 T16 25.5 T24 25.5 T32 25.5 V32 H0 Z'


def orca(body='#1e293b', white='#ffffff', water=None):
    s = ('<path d="%s" fill="%s"/><ellipse cx="23.6" cy="24.2" rx="2.8" ry="1.1" transform="rotate(-28 23.6 24.2)" fill="%s"/>'
         '<g fill="%s">%s<path d="%s"/></g>') % (BODY, body, body, white, EYE, CHIN)
    if water:
        s += '<path d="%s" fill="%s"/>' % (WAVE, water)
    return s


def favicon():
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
            '<rect width="32" height="32" rx="8" fill="#e2e8f0"/>'
            '<clipPath id="c"><rect width="32" height="32" rx="8"/></clipPath><g clip-path="url(#c)">%s</g></svg>'
            % orca(water='#94a3b8'))


def template():
    # 메뉴바용: 검은 실루엣, 흰 무늬는 뚫는다(macOS 가 다크/라이트에 맞춰 칠함)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
            '<mask id="m"><rect width="32" height="32" fill="#fff"/><g fill="#000">%s<path d="%s"/></g>'
            '<path d="%s" fill="#000"/></mask>'
            '<g mask="url(#m)"><path d="%s" fill="#000"/></g>'
            '<path d="M1 27.2 Q5 25.3 9 27.2 T17 27.2 T25 27.2 T33 27.2" fill="none" stroke="#000" stroke-width="2.2" stroke-linecap="round"/></svg>'
            % (EYE, CHIN, WAVE, BODY))


if __name__ == '__main__':
    import sys
    out = sys.argv[1]
    open(out + '/fav.svg', 'w').write(favicon())
    open(out + '/tpl.svg', 'w').write(template())


def mono(bg='#1e293b', fg='#ffffff'):
    # 메뉴바 아이콘과 같은 한 색 실루엣. 짙은 바탕에 흰 범고래(무늬는 뚫어서 바탕색이 보이게)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
            '<rect width="32" height="32" rx="8" fill="%s"/>'
            '<mask id="mm"><rect width="32" height="32" fill="#fff"/><g fill="#000">%s<path d="%s"/></g>'
            '<path d="%s" fill="#000"/></mask>'
            '<g mask="url(#mm)" fill="%s"><path d="%s"/></g>'
            '<path d="M2 27.2 Q6 25.3 10 27.2 T18 27.2 T26 27.2 T34 27.2" fill="none" stroke="%s" stroke-width="2" stroke-linecap="round"/></svg>'
            % (bg, EYE, CHIN, WAVE, fg, BODY, fg))
