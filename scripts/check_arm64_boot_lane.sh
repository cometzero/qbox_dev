#!/usr/bin/env bash

set -euo pipefail

qbox_root="${QBOX_ROOT:-/build/qbox_dev/sources/qbox}"

if [[ ! -d "${qbox_root}" ]]; then
    fail "qbox repo root missing: ${qbox_root}"
fi

printf 'Checking qbox repo at %s\n' "${qbox_root}"

pass() {
    printf 'PASS: %s\n' "$1"
}

fail() {
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

require_file() {
    local path="$1"
    local label="$2"
    if [[ ! -f "$path" ]]; then
        fail "missing ${label}: ${path}"
    fi
    pass "${label} exists"
}

require_grep() {
    local pattern="$1"
    local path="$2"
    local label="$3"
    if ! grep -Eq "$pattern" "$path"; then
        fail "${label} not found in ${path}"
    fi
    pass "${label} present"
}

require_absent() {
    local path="$1"
    local label="$2"
    if [[ -e "$path" ]]; then
        fail "unexpected ${label}: ${path}"
    fi
    pass "${label} absent as expected"
}

require_file "${qbox_root}/platforms/CMakeLists.txt" "platforms CMake entry"
require_file "${qbox_root}/platforms/ubuntu/conf_aarch64.lua" "AArch64 platform config"
require_file "${qbox_root}/platforms/ubuntu/fw/build_linux_dist_image.sh" "Ubuntu image generator"
require_file "${qbox_root}/README.md" "repository README"
require_file "${qbox_root}/docs/platforms/ubuntu.md" "Ubuntu platform doc"
require_file "${qbox_root}/docs/networking.md" "networking doc"

require_grep 'conf_\$\{UBUNTU_ARCH\}\.lua' "${qbox_root}/platforms/CMakeLists.txt" \
    "ubuntu platform target selection"
require_grep 'UBUNTU_ARCH STREQUAL "riscv64"' "${qbox_root}/platforms/CMakeLists.txt" \
    "riscv64 selector branch"
require_grep 'AArch64' "${qbox_root}/README.md" "AArch64 quick-start guidance"
require_grep '\./build_linux_dist_image\.sh -s 4G -p xorg,pciutils -a aarch64' \
    "${qbox_root}/README.md" "AArch64 quick-start command"
require_grep 'AArch64 or RISC-V 64' "${qbox_root}/docs/platforms/ubuntu.md" \
    "ubuntu platform architecture scope"
require_grep '\./build_linux_dist_image\.sh -s 4G -p xorg,pciutils -a riscv64' \
    "${qbox_root}/docs/platforms/ubuntu.md" "riscv64 quick-start command"
require_grep 'Buildroot Configuration' "${qbox_root}/docs/networking.md" \
    "Buildroot networking guidance"
require_grep 'BR2_PACKAGE_OPENSSH' "${qbox_root}/docs/networking.md" \
    "Buildroot SSH package snippet"
require_grep '_KERNEL64_LOAD_ADDR' "${qbox_root}/platforms/ubuntu/conf_aarch64.lua" \
    "kernel load address"
require_grep '_DTB_LOAD_ADDR' "${qbox_root}/platforms/ubuntu/conf_aarch64.lua" \
    "DTB load address"
require_grep '_INITRD_LOAD_ADDR' "${qbox_root}/platforms/ubuntu/conf_aarch64.lua" \
    "initrd load address"
require_grep 'data=_bootloader_aarch64' "${qbox_root}/platforms/ubuntu/conf_aarch64.lua" \
    "AArch64 bootloader stub"
require_grep 'Image\.bin' "${qbox_root}/platforms/ubuntu/conf_aarch64.lua" \
    "kernel image input"
require_grep 'ubuntu\.dtb' "${qbox_root}/platforms/ubuntu/conf_aarch64.lua" \
    "device tree input"
require_grep 'image_ext4_initrd\.img' "${qbox_root}/platforms/ubuntu/conf_aarch64.lua" \
    "initrd input"
require_absent "${qbox_root}/configs/fw/8775/bsp/lnx/ubuntu/conf.lua" \
    "configs/fw/8775/bsp/lnx/ubuntu/conf.lua fallback"

printf '\nLane conclusion: current checkout exposes an Ubuntu-based AArch64 boot lane, not a repo-native Buildroot lane.\n'
printf 'The AArch64 path is anchored by platforms/ubuntu/conf_aarch64.lua plus platforms/ubuntu/fw/build_linux_dist_image.sh.\n'
