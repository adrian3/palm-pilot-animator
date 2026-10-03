#!/bin/sh
set -eu
: "${PALM_TOOLCHAIN:?Set PALM_TOOLCHAIN to the unpacked compiler directory}"
: "${PALM_SDK:?Set PALM_SDK to the sdk-3.5 directory}"
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
asset_dir="${PALM_ASSET_DIR:-$project_dir/assets/generated}"
build_dir="${PALM_BUILD_DIR:-$project_dir/build}"
mkdir -p "$build_dir"
export GCC_EXEC_PREFIX="$PALM_TOOLCHAIN/lib/gcc-lib/"
export PATH="$PALM_TOOLCHAIN/bin:$PATH"
lib_dir="$PALM_TOOLCHAIN/m68k-palmos/lib"
m68k-palmos-gcc -I"$asset_dir" -nostdinc -O2 -Wall -Wno-unknown-pragmas -I"$PALM_SDK/include" -I"$PALM_SDK/include/Libraries" -I"$PALM_SDK/include/Core" -I"$PALM_SDK/include/Dynamic" -I"$PALM_SDK/include/Core/System" -I"$PALM_SDK/include/Core/UI" -I"$PALM_SDK/include/Core/Hardware" -B"$PALM_TOOLCHAIN/bin/" -B"$lib_dir/" -L"$lib_dir" "$project_dir/app/PalmAnimation.c" -o "$build_dir/PalmAnimation"
python3 "$project_dir/tools/make-icon.py" "$build_dir"

build-prc -o "$build_dir/PalmAnimation.prc" -t appl -c PAnm -n "Ade's App" "$build_dir/PalmAnimation" "$build_dir/tAIB03e8.bin" "$build_dir/tAIN03e8.bin" "$asset_dir"/Tbmp*.bin "$asset_dir"/ATim*.bin
