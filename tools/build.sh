#!/bin/sh
set -eu
: "${PALM_TOOLCHAIN:?Set PALM_TOOLCHAIN to the unpacked compiler directory}"
: "${PALM_SDK:?Set PALM_SDK to the sdk-3.5 directory}"
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
mkdir -p "$project_dir/build"
export GCC_EXEC_PREFIX="$PALM_TOOLCHAIN/lib/gcc-lib/"
export PATH="$PALM_TOOLCHAIN/bin:$PATH"
lib_dir="$PALM_TOOLCHAIN/m68k-palmos/lib"
m68k-palmos-gcc -I"$project_dir/assets/generated" -nostdinc -O2 -Wall -Wno-unknown-pragmas -I"$PALM_SDK/include" -I"$PALM_SDK/include/Libraries" -I"$PALM_SDK/include/Core" -I"$PALM_SDK/include/Dynamic" -I"$PALM_SDK/include/Core/System" -I"$PALM_SDK/include/Core/UI" -I"$PALM_SDK/include/Core/Hardware" -B"$PALM_TOOLCHAIN/bin/" -B"$lib_dir/" -L"$lib_dir" "$project_dir/app/PalmAnimation.c" -o "$project_dir/build/PalmAnimation"
python3 "$project_dir/tools/make-icon.py" "$project_dir/build"

build-prc -o "$project_dir/build/PalmAnimation.prc" -t appl -c PAnm -n "Ade's App" "$project_dir/build/PalmAnimation" "$project_dir/build/tAIB03e8.bin" "$project_dir/build/tAIN03e8.bin" "$project_dir/assets/generated"/Tbmp*.bin "$project_dir/assets/generated"/ATim*.bin
