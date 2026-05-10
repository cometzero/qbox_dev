#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
log_dir=${QBOX_VERIFICATION_DIR:-"${repo_root}/build/verification"}
stamp=${QBOX_HEXAGON_GUEST_SMOKE_STAMP:-$(date +%Y%m%d-%H%M%S)}
log_path=${QBOX_HEXAGON_GUEST_SMOKE_LOG:-"${log_dir}/qbox-iree-tiny-cnn-hexagon-guest-${stamp}.log"}
boot_log=${QBOX_BOOT_LOG:-"${log_dir}/qbox-iree-tiny-cnn-hexagon-guest-boot-${stamp}.log"}
expected='1x1x2x2xf32=[[[54 63][90 99]]]'
cmd='/opt/qbox/iree/tiny-cnn/run_tiny_cnn_hexagon_guest.sh'

mkdir -p "${log_dir}"

set +e
(
  sleep "${QBOX_IREE_LOGIN_DELAY:-24}"
  printf 'root\r'
  sleep "${QBOX_IREE_COMMAND_DELAY:-3}"
  printf '%s\r' "${cmd}"
  sleep "${QBOX_IREE_AFTER_COMMAND_DELAY:-20}"
) | QBOX_BOOT_TIMEOUT=${QBOX_BOOT_TIMEOUT:-55} \
    QBOX_BOOT_LOG="${boot_log}" \
    "${repo_root}/scripts/run_qbox_buildroot_boot.sh" \
    > >(tee "${log_path}") 2>&1
rc=$?
set -e

if [[ ${rc} -ne 0 && ${rc} -ne 124 ]]; then
  echo "QBox Hexagon guest smoke exited unexpectedly: rc=${rc}" >&2
  exit "${rc}"
fi

for marker in \
  'Run /sbin/init as init process' \
  'apollo-qbox login:' \
  'userspace submit ABI ready at /dev/apollo-hexagon' \
  'SMMUv3 page-table walker/ATS/PRI/fault queue ready' \
  'SMMUv3 architectural descriptor probe ok' \
  'SMMUv3 architectural descriptor probe ok 4-level' \
  'SMMUv3 stream/context descriptor probe ok' \
  'SMMUv3 negative fault replay ok' \
  'APOLLO_SMMU_TBU: map stream-id=0x1' \
  'APOLLO_SMMU_TBU: unmap stream-id=0x1' \
  'APOLLO_SMMU_TBU: architectural stream table walk stream-id=0x1' \
  'APOLLO_SMMU_TBU: architectural context descriptor walk stream-id=0x1' \
  'APOLLO_SMMU_TBU: architectural table walk stream-id=0x1 level=0' \
  'APOLLO_SMMU_TBU: architectural table walk stream-id=0x1 level=1' \
  'APOLLO_SMMU_TBU: architectural table walk stream-id=0x1 level=2' \
  'APOLLO_SMMU_TBU: architectural descriptor walk stream-id=0x1' \
  'APOLLO_SMMU_TBU: architectural descriptor walk stream-id=0x1 levels=4' \
  'APOLLO_SMMU_TBU: architected ATS translation response stream-id=0x1' \
  'APOLLO_SMMU_TBU: architected PRI response stream-id=0x1' \
  'APOLLO_SMMU_TBU: architected fault replay queued stream-id=0x1' \
  'APOLLO_SMMU_TBU: page-table walk stream-id=0x1' \
  'APOLLO_SMMU_TBU: ATS cache fill stream-id=0x1' \
  'APOLLO_SMMU_TBU: PRI request resolved stream-id=0x1' \
  'APOLLO_SMMU_TBU: fault queue push stream-id=0x1' \
  'dynamic SMMU SG map refreshed bytes=131072 segments=8' \
  'APOLLO_HEXAGON_DMA: firmware requested DMA src=0x10020000 dst=0x10080000 len=0x20000' \
  'APOLLO_HEXAGON_DMA: DMA copy complete src=0x10020000 dst=0x10080000 len=0x20000' \
  'APOLLO_HEXAGON_DMA: job status=0x1' \
  'APOLLO_HEXAGON_DMA: async irq pending queue=0' \
  'APOLLO_HEXAGON_DMA: async irq pending queue=1' \
  'SG DMA stress ok queue=0' \
  'bytes=131072 segments=8' \
  'accelerator tiny cnn ok' \
  'IREE Apollo Hexagon HAL: dynamic C HAL plugin=' \
  'IREE Apollo Hexagon HAL: upstream executable_plugin export=iree_hal_executable_plugin_query available' \
  'IREE Apollo Hexagon HAL: queues=2 command-buffer=fixed fence=async-irq-poll' \
  'IREE Apollo Hexagon HAL: command buffer submitted' \
  'IREE Apollo Hexagon HAL: offload complete' \
  'IREE Apollo Hexagon HAL: async fence signaled queue=0' \
  'IREE Apollo Hexagon HAL: async fence signaled queue=1' \
  'EXEC @tiny_cnn_graph [apollo-hexagon]'; do
  if ! grep -F "${marker}" "${log_path}" >/dev/null; then
    echo "missing Hexagon offload marker: ${marker}" >&2
    echo "log: ${log_path}" >&2
    exit 1
  fi
done

if ! grep -F "${expected}" "${log_path}" >/dev/null; then
  echo "Hexagon tiny-CNN output mismatch; expected: ${expected}" >&2
  echo "log: ${log_path}" >&2
  exit 1
fi

cat <<EOF
PASS: QBox guest IREE Hexagon tiny-CNN output matched
Expected: ${expected}
Log: ${log_path}
Boot log: ${boot_log}
EOF
