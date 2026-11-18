#!/bin/bash
set -euo pipefail
project_dir="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_dir/macos"
build_arch="${1:-$(node -p 'process.arch')}"
case "$build_arch" in arm64|x64) ;; *) echo 'Expected arm64 or x64'; exit 1 ;; esac
version="$(node -p "require('./package.json').version")"
export CSC_IDENTITY_AUTO_DISCOVERY=false
npx electron-builder --mac dir --"$build_arch" --publish never
if [ "$build_arch" = arm64 ]; then bundle_dir=mac-arm64; else bundle_dir=mac; fi
staging_dir="$(mktemp -d "${TMPDIR:-/tmp}/choir-dmg.XXXXXX")"
trap 'rm -rf "$staging_dir"' EXIT
cp -R "$project_dir/releases/macos/$bundle_dir/和声练习室.app" "$staging_dir/"
ln -s /Applications "$staging_dir/Applications"
hdiutil create -volname "和声练习室 $version" -srcfolder "$staging_dir" -ov -format UDZO \
  "$project_dir/releases/macos/ChoirStudio-$version-macOS-$build_arch.dmg"
