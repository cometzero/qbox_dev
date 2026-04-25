#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
linux_src=${QBOX_LINUX_SRC:-"${repo_root}/sources/linux"}
linux_output=${QBOX_LINUX_OUTPUT:-"${repo_root}/build/linux-a710"}
buildroot_output=${QBOX_BUILDROOT_OUTPUT:-"${repo_root}/build/buildroot-a710"}
toolchain_prefix=${QBOX_LINUX_CROSS_COMPILE:-"${buildroot_output}/host/bin/aarch64-buildroot-linux-gnu-"}
config_fragment=${QBOX_LINUX_CONFIG_FRAGMENT:-"${repo_root}/buildroot/external/qbox_arm64/board/qbox/a710_soc/linux.config"}
jobs=${QBOX_LINUX_JOBS:-$(nproc)}

if [[ ! -f "${linux_src}/Makefile" ]]; then
  echo "Linux source missing: ${linux_src}" >&2
  echo "Run: git submodule update --init --recursive sources/linux" >&2
  exit 1
fi
if [[ ! -x "${toolchain_prefix}gcc" ]]; then
  echo "Buildroot cross compiler missing: ${toolchain_prefix}gcc" >&2
  echo "Run rootfs/toolchain build first: scripts/build_qbox_buildroot_arm64.sh" >&2
  exit 1
fi
if [[ ! -f "${config_fragment}" ]]; then
  echo "Linux config fragment missing: ${config_fragment}" >&2
  exit 1
fi

mkdir -p "${linux_output}"

make -C "${linux_src}" \
  O="${linux_output}" \
  ARCH=arm64 \
  CROSS_COMPILE="${toolchain_prefix}" \
  defconfig

KCONFIG_CONFIG="${linux_output}/.config" \
  "${linux_src}/scripts/kconfig/merge_config.sh" \
    -m \
    -O "${linux_output}" \
    "${linux_output}/.config" \
    "${config_fragment}"

make -C "${linux_src}" \
  O="${linux_output}" \
  ARCH=arm64 \
  CROSS_COMPILE="${toolchain_prefix}" \
  olddefconfig

if [[ "${1:-}" == "--config-only" ]]; then
  echo "Configured Linux output: ${linux_output}"
  exit 0
fi

make -C "${linux_src}" \
  O="${linux_output}" \
  ARCH=arm64 \
  CROSS_COMPILE="${toolchain_prefix}" \
  Image \
  -j"${jobs}"

image="${linux_output}/arch/arm64/boot/Image"
if [[ ! -s "${image}" ]]; then
  echo "missing Linux Image: ${image}" >&2
  exit 1
fi

echo "Linux Image: ${image}"
