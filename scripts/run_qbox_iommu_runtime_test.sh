#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
log_dir=${QBOX_VERIFICATION_DIR:-"${repo_root}/build/verification"}
stamp=${QBOX_IOMMU_RUNTIME_TEST_STAMP:-$(date +%Y%m%d-%H%M%S)}
log_path=${QBOX_IOMMU_RUNTIME_TEST_LOG:-"${log_dir}/qbox-iommu-runtime-test-${stamp}.log"}
boot_log=${QBOX_BOOT_LOG:-"${log_dir}/qbox-iommu-runtime-test-boot-${stamp}.log"}

mkdir -p "${log_dir}"

set +e
QBOX_BOOT_TIMEOUT=${QBOX_BOOT_TIMEOUT:-45} \
  QBOX_BOOT_LOG="${boot_log}" \
  "${repo_root}/scripts/run_qbox_buildroot_boot.sh" \
  > >(tee "${log_path}") 2>&1
rc=$?
set -e

if [[ ${rc} -ne 0 && ${rc} -ne 124 ]]; then
  echo "QBox IOMMU runtime test exited unexpectedly: rc=${rc}" >&2
  exit "${rc}"
fi

for marker in \
  'Run /sbin/init as init process' \
  'apollo-qbox login:' \
  'arm-smmu-v3 1c200000.iommu' \
  'IOMMU runtime selftest ok' \
  'domain-type=0x' \
  'coherent=' \
  'streaming=' \
  'dataplane=stream-id=0x3' \
  'APOLLO_HEXAGON_DMA: path=smmu-translated stream-id=0x3' \
  'APOLLO_SMMU_TBU: stream-id=0x3 translate read' \
  'APOLLO_SMMU_TBU: stream-id=0x3 translate write' \
  'runtime IOMMU sysfs ready: result, run'; do
  if ! grep -F "${marker}" "${log_path}" >/dev/null; then
    echo "missing IOMMU runtime marker: ${marker}" >&2
    echo "log: ${log_path}" >&2
    exit 1
  fi
done

cat <<EOF
PASS: QBox IOMMU runtime driver selftest passed
Log: ${log_path}
Boot log: ${boot_log}
EOF
