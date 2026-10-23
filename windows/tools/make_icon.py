"""맥 앱 아이콘(macos/app/Resources/AppIcon.icns)으로 Windows 아이콘(windows/spyhop.ico)을 만든다. 표준 라이브러리만 쓴다.

  python windows/tools/make_icon.py

icns 안의 PNG(32 · 64 · 128 · 256)는 그대로 넣고, 16px 은 icns 의 ARGB(채널별 PackBits 압축)를 풀어 PNG 로 만든다.
ICO 는 Windows Vista 부터 PNG 를 그대로 담을 수 있다.
"""
import os
import struct
import sys
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ICNS = os.path.join(ROOT, 'macos', 'app', 'Resources', 'AppIcon.icns')
ICO = os.path.join(ROOT, 'windows', 'spyhop.ico')
PNG_SIG = b'\x89PNG\r\n\x1a\n'


def icns_entries(data):
    """{종류: 내용}. 같은 크기가 둘이면(ic08 · ic13 같은 레티나 판) 먼저 나온 것."""
    if data[:4] != b'icns':
        raise ValueError('not an icns file')
    out, i = {}, 8
    while i + 8 <= len(data):
        kind, size = data[i:i + 4].decode('latin1'), struct.unpack('>I', data[i + 4:i + 8])[0]
        if size < 8:
            break
        out.setdefault(kind, data[i + 8:i + size])
        i += size
    return out


def png_size(png):
    return struct.unpack('>II', png[16:24])


def unpack_argb(body, side):
    """icns 의 ARGB(ic04 · ic05): 'ARGB' 다음에 A·R·G·B 채널이 차례로 PackBits 로 눌려 있다."""
    if body[:4] != b'ARGB':
        raise ValueError('not ARGB')
    data, i, channels = body[4:], 0, []
    for _ in range(4):
        ch = bytearray()
        while len(ch) < side * side:
            n = data[i]
            i += 1
            if n < 0x80:  # 다음 n+1 바이트를 그대로
                ch += data[i:i + n + 1]
                i += n + 1
            else:  # 다음 한 바이트를 n-125 번
                ch += bytes([data[i]]) * (n - 125)
                i += 1
        channels.append(ch[:side * side])
    a, r, g, b = channels
    return bytes(v for px in zip(r, g, b, a) for v in px)


def png(rgba, side):
    def chunk(tag, payload):
        return struct.pack('>I', len(payload)) + tag + payload + struct.pack('>I', zlib.crc32(tag + payload) & 0xffffffff)
    rows = b''.join(b'\x00' + rgba[y * side * 4:(y + 1) * side * 4] for y in range(side))
    return (PNG_SIG + chunk(b'IHDR', struct.pack('>IIBBBBB', side, side, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(rows, 9)) + chunk(b'IEND', b''))


def ico(pngs):
    """PNG 들을 크기 순으로 담은 ICO."""
    pngs = sorted(pngs, key=lambda p: png_size(p)[0])
    head = struct.pack('<HHH', 0, 1, len(pngs))
    offset, dirs = 6 + 16 * len(pngs), b''
    for p in pngs:
        w, h = png_size(p)
        dirs += struct.pack('<BBBBHHII', w % 256, h % 256, 0, 0, 1, 32, len(p), offset)  # 256 은 0 으로 적는다
        offset += len(p)
    return head + dirs + b''.join(pngs)


def build(icns_path=ICNS, ico_path=ICO):
    entries = icns_entries(open(icns_path, 'rb').read())
    by_size = {}
    for body in entries.values():
        if body[:8] == PNG_SIG:
            by_size.setdefault(png_size(body)[0], body)
    if 'ic04' in entries:  # 16px
        by_size.setdefault(16, png(unpack_argb(entries['ic04'], 16), 16))
    pngs = [by_size[s] for s in (16, 32, 64, 128, 256) if s in by_size]
    if not pngs:
        raise ValueError('no usable images in %s' % icns_path)
    with open(ico_path, 'wb') as f:
        f.write(ico(pngs))
    return sorted(png_size(p)[0] for p in pngs)


if __name__ == '__main__':
    sizes = build(*sys.argv[1:3])
    print('wrote %s (%s px)' % (ICO if len(sys.argv) < 3 else sys.argv[2], ', '.join(map(str, sizes))))
