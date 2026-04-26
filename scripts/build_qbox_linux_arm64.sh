#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
linux_src=${QBOX_LINUX_SRC:-"${repo_root}/sources/linux"}
linux_output=${QBOX_LINUX_OUTPUT:-"${repo_root}/build/linux-a710"}
buildroot_output=${QBOX_BUILDROOT_OUTPUT:-"${repo_root}/build/buildroot-a710"}
toolchain_prefix=${QBOX_LINUX_CROSS_COMPILE:-"${buildroot_output}/host/bin/aarch64-buildroot-linux-gnu-"}
config_fragment=${QBOX_LINUX_CONFIG_FRAGMENT:-"${repo_root}/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/linux.config"}
ccache_bin=${QBOX_CCACHE:-$(command -v ccache || true)}
use_ccache=${QBOX_USE_CCACHE:-1}
ccache_dir=${QBOX_LINUX_CCACHE_DIR:-"${repo_root}/build/ccache/linux"}
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

linux_cross_compile="${toolchain_prefix}"
if [[ "${use_ccache}" != "0" ]]; then
  if [[ -z "${ccache_bin}" ]]; then
    echo "ccache requested but not found. Install ccache or set QBOX_USE_CCACHE=0." >&2
    exit 1
  fi
  mkdir -p "${ccache_dir}"
  export CCACHE_DIR="${ccache_dir}"
  export CCACHE_BASEDIR="${repo_root}"
  linux_cross_compile="${ccache_bin} ${toolchain_prefix}"
fi

mkdir -p "${linux_output}"

make -C "${linux_src}" \
  O="${linux_output}" \
  ARCH=arm64 \
  CROSS_COMPILE="${linux_cross_compile}" \
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
  CROSS_COMPILE="${linux_cross_compile}" \
  olddefconfig

if [[ "${1:-}" == "--config-only" ]]; then
  echo "Configured Linux output: ${linux_output}"
  if [[ "${use_ccache}" != "0" ]]; then
    echo "Linux ccache launcher: ${ccache_bin}"
    echo "Linux ccache dir: ${CCACHE_DIR}"
  fi
  exit 0
fi

make -C "${linux_src}" \
  O="${linux_output}" \
  ARCH=arm64 \
  CROSS_COMPILE="${linux_cross_compile}" \
  Image \
  -j"${jobs}"

image="${linux_output}/arch/arm64/boot/Image"
if [[ ! -s "${image}" ]]; then
  echo "missing Linux Image: ${image}" >&2
  exit 1
fi

echo "Linux Image: ${image}"
if [[ "${use_ccache}" != "0" ]]; then
  echo "Linux ccache launcher: ${ccache_bin}"
  echo "Linux ccache dir: ${CCACHE_DIR}"
fi
