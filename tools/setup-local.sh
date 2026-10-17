#!/bin/sh
# Restore project-local build tools; optionally include the direct-sync receiver.
set -eu
mode=${1:-direct}
case "$mode" in
 direct|--export-only) ;;
 *) echo 'Usage: sh tools/setup-local.sh [--export-only]' >&2; exit 2 ;;
esac
if [ "$#" -gt 1 ]; then
 echo 'Usage: sh tools/setup-local.sh [--export-only]' >&2
 exit 2
fi
if [ "$mode" = direct ]; then
 for tool in node npm; do
  command -v "$tool" >/dev/null 2>&1 || { echo "Missing $tool. Install Node.js 24, or use --export-only for external HotSync." >&2; exit 1; }
 done
fi
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
local_dir="$project_dir/.local"
mkdir -p "$local_dir"
if [ ! -f "$local_dir/toolchain/bin/m68k-palmos-gcc" ]; then
 curl -fL https://github.com/savaughn/prc-tools-remix/releases/download/macos-arm/prc-tools-remix-macos-arm64.tar.gz -o "$local_dir/prc-tools.tar.gz"
 actual_hash=$(shasum -a 256 "$local_dir/prc-tools.tar.gz" | cut -d ' ' -f 1)
 [ "$actual_hash" = a11d4ff69c30018ce0045e90e75fe93ec91f68655ad82092467c597e5bc47845 ] || { echo 'Compiler archive checksum mismatch' >&2; exit 1; }
 tar -xzf "$local_dir/prc-tools.tar.gz" -C "$local_dir"
 mv "$local_dir/prc-tools-remix-macos-arm64" "$local_dir/toolchain"
fi
if [ ! -d "$local_dir/sdk-3.5" ]; then
 git clone https://github.com/jichu4n/palm-os-sdk.git "$local_dir/sdk-source"
 git -C "$local_dir/sdk-source" checkout 1fa22066ca0f8b74949c14dd1d626294145d1c09
 cp -R "$local_dir/sdk-source/sdk-3.5" "$local_dir/sdk-3.5"
fi
if [ "$mode" = --export-only ]; then
 echo 'Build tools ready. Direct-sync dependencies were skipped; install the PRC with your preferred HotSync tool.'
 exit 0
fi
if [ ! -d "$local_dir/palm-sync" ]; then
 git clone https://github.com/jichu4n/palm-sync.git "$local_dir/palm-sync"
 git -C "$local_dir/palm-sync" checkout f4da46b8fc400c611fddba2cb4be5c236d03e2f2
fi
npm ci --prefix "$local_dir/palm-sync"
npm run build:tsc --prefix "$local_dir/palm-sync"
