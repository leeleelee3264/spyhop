#!/bin/bash
# Spyhop.app 을 만든다. Xcode 프로젝트 없이 swiftc 로 빌드하고 번들을 직접 조립한다.
#   macos/build.sh            → macos/build/Spyhop.app
#   macos/build.sh --dmg      → macos/build/Spyhop-<버전>.dmg 도
# 버전은 마지막 git 태그(v 뺌). 서명은 ad-hoc(애플 개발자 서명 없음): 처음 열 때 「그래도 열기」가 한 번 필요하다
set -euo pipefail
cd "$(dirname "$0")/.."
ver="${SPYHOP_VERSION:-$(git describe --tags --abbrev=0 2>/dev/null | sed 's/^v//')}"
ver="${ver:-0.0.0}"
out=macos/build
app="$out/Spyhop.app"
rm -rf "$app"
mkdir -p "$app/Contents/MacOS" "$app/Contents/Resources/spyhop"

for arch in arm64 x86_64; do
  swiftc -O -target "$arch-apple-macos13.0" macos/Sources/*.swift -o "$out/Spyhop-$arch"
done
lipo -create "$out/Spyhop-arm64" "$out/Spyhop-x86_64" -output "$app/Contents/MacOS/Spyhop"
rm -f "$out/Spyhop-arm64" "$out/Spyhop-x86_64"

# 보드 서버와 화면은 그대로 쓴다
cp board.py orca_art.py panel.html LICENSE "$app/Contents/Resources/spyhop/"
cp macos/Resources/AppIcon.icns macos/Resources/MenuBarIcon.png "$app/Contents/Resources/"
# 창이 여는 로더: 오르카 탭이 쓰는 것과 같은 페이지(board.py 의 LOADER_HTML)
/usr/bin/python3 -B -c 'import sys; sys.path.insert(0, "."); import board; sys.stdout.write(board.LOADER_HTML)' > "$app/Contents/Resources/loader.html"
sed "s/__VERSION__/$ver/g" macos/Info.plist > "$app/Contents/Info.plist"

codesign --force --sign - "$app"
echo "built: $app ($ver)"

if [ "${1:-}" = --dmg ]; then
  dmg="$out/Spyhop-$ver.dmg"
  stage="$out/dmg"
  rm -rf "$stage" "$dmg"
  mkdir -p "$stage"
  cp -R "$app" "$stage/"
  ln -s /Applications "$stage/Applications"
  hdiutil create -quiet -volname Spyhop -srcfolder "$stage" -ov -format UDZO "$dmg"
  rm -rf "$stage"
  echo "dmg: $dmg"
fi
