#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
qbox_root=${QBOX_ROOT:-"${repo_root}/qbox"}
vp=${QBOX_PLATFORMS_VP:-"${qbox_root}/build/platforms-vp"}
log_dir=${QBOX_VERIFICATION_DIR:-"${repo_root}/build/verification"}
timeout_s=${QBOX_BOOT_TIMEOUT:-120}
log_path=${QBOX_BOOT_LOG:-"${log_dir}/qbox-a710-buildroot-boot.log"}
if [[ "${log_path}" != /* ]]; then
  log_path="${repo_root}/${log_path}"
fi

if [[ ! -x "${vp}" ]]; then
  echo "platforms-vp is missing or not executable: ${vp}" >&2
  echo "Build QBox first: scripts/build_qbox_buildroot_platform.sh" >&2
  exit 1
fi

required_modules=(
  loader.so
  cpu_arm_cortexA710.so
  arm_gicv3.so
  virtio_mmio_net.so
  qemu_gpex.so
  uart-pl011.so
  char_backend_stdio.so
  global_peripheral_initiator.so
  gs_memory.so
  router.so
)
for module in "${required_modules[@]}"; do
  if [[ ! -s "${qbox_root}/build/${module}" ]]; then
    echo "QBox dynamic module is missing: ${qbox_root}/build/${module}" >&2
    echo "Build QBox runtime modules first: scripts/build_qbox_buildroot_platform.sh" >&2
    exit 1
  fi
done

mkdir -p "$(dirname "${log_path}")"
cd "${qbox_root}"
timeout --signal=SIGQUIT "${timeout_s}s" \
  "${vp}" -l platforms/buildroot/conf_aarch64.lua \
  2>&1 | tee "${log_path}"
