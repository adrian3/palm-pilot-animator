#!/bin/sh
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
export PALM_TOOLCHAIN="$project_dir/.local/toolchain"
export PALM_SDK="$project_dir/.local/sdk-3.5"
# This historical GCC invokes unprefixed assembler/linker names.
ln -sf m68k-palmos-as "$PALM_TOOLCHAIN/bin/as"
ln -sf m68k-palmos-ld "$PALM_TOOLCHAIN/bin/ld"
exec sh "$project_dir/tools/build.sh"
