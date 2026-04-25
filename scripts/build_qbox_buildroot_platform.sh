#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
qbox_root=${QBOX_ROOT:-"${repo_root}/qbox"}

if [[ ! -f "${qbox_root}/CMakePresets.json" ]]; then
  echo "QBox source missing: ${qbox_root}" >&2
  echo "Run: git submodule update --init --recursive qbox" >&2
  exit 1
fi

if [[ ! -f "${qbox_root}/build/CMakeCache.txt" ]]; then
  (cd "${qbox_root}" && cmake --preset gcc -DLIBQEMU_TARGETS=aarch64)
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
