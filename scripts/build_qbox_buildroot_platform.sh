#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
qbox_root=${QBOX_ROOT:-"${repo_root}/sources/qbox"}
ccache_bin=${QBOX_CCACHE:-$(command -v ccache || true)}
use_ccache=${QBOX_USE_CCACHE:-1}
ccache_dir=${QBOX_QBOX_CCACHE_DIR:-"${repo_root}/build/ccache/qbox"}

if [[ ! -f "${qbox_root}/CMakePresets.json" ]]; then
  echo "QBox source missing: ${qbox_root}" >&2
  echo "Run: git submodule update --init --recursive sources/qbox" >&2
  exit 1
fi

cmake_args=(-DLIBQEMU_TARGETS=aarch64)
if [[ "${use_ccache}" != "0" ]]; then
  if [[ -z "${ccache_bin}" ]]; then
    echo "ccache requested but not found. Install ccache or set QBOX_USE_CCACHE=0." >&2
    exit 1
  fi
  mkdir -p "${ccache_dir}"
  export CCACHE_DIR="${ccache_dir}"
  export CCACHE_BASEDIR="${qbox_root}"
  cmake_args+=(
    -DCMAKE_C_COMPILER_LAUNCHER="${ccache_bin}"
    -DCMAKE_CXX_COMPILER_LAUNCHER="${ccache_bin}"
  )
fi

(cd "${qbox_root}" && cmake --preset gcc "${cmake_args[@]}")

if [[ "${1:-}" == "--config-only" ]]; then
  echo "Configured QBox buildroot platform output: ${qbox_root}/build"
  if [[ "${use_ccache}" != "0" ]]; then
    echo "QBox ccache launcher: ${ccache_bin}"
    echo "QBox ccache dir: ${CCACHE_DIR}"
  fi
  exit 0
fi

targets=(
  platforms-vp
  loader
  cpu_arm_cortexA710
  arm_gicv3
  virtio_mmio_net
  qemu_gpex
  uart-pl011
  char_backend_stdio
  global_peripheral_initiator
  gs_memory
  router
)

(cd "${qbox_root}" && cmake --build --preset gcc --target "${targets[@]}" --parallel)

echo "QBox Buildroot platform runtime built in ${qbox_root}/build"
if [[ "${use_ccache}" != "0" ]]; then
  echo "QBox ccache launcher: ${ccache_bin}"
  echo "QBox ccache dir: ${CCACHE_DIR}"
fi
