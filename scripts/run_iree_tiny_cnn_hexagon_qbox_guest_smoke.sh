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
  'userspace submit ABI ready at /dev/accel/accel*' \
  'userspace submit ABI ready at /dev/accel/accel* stream-id=0x2 primary=0' \
  'async doorbell irq ready irq=' \
  'dma path smmu-translated caps=0x7d stream-id=' \
  'smmuv3-translated=yes queues=2 async-fence=yes large-tensor=yes' \
  'arm-smmu-v3 dma-iommu map installed' \
  'SMMUv3 page-table walker/ATS/PRI/fault queue ready' \
  'SMMUv3 stream/context descriptor probe ok' \
  'SMMUv3 page-table walker/ATS/PRI/fault queue ready features=0x' \
  'SMMUv3 architected queue' \
  'SMMUv3 command invalidation selftest ok' \
  'SMMUv3 DPTI unsupported command selftest ok' \
  'cerror=1' \
  'SMMUv3 REC_CFG_ATS translation request selftest ok' \
  'SMMUv3 ATSCHK/EATS translation request selftest ok' \
  'APOLLO_SMMU_TBU: architected CMDQ invalidation op=ATC_INV' \
  'APOLLO_SMMU_TBU: architected CMDQ invalidation op=TLBI_NH_ALL' \
  'APOLLO_SMMU_TBU: map stream-id=0x1' \
  'APOLLO_SMMU_TBU: unmap stream-id=0x1' \
  'APOLLO_SMMU_TBU: architectural stream table walk stream-id=0x1' \
  'APOLLO_SMMU_TBU: architectural context descriptor walk stream-id=0x1' \
  'APOLLO_SMMU_TBU: architectural table walk stream-id=0x1 stage=1 granule=0x1000 level=0' \
  'APOLLO_SMMU_TBU: architectural table walk stream-id=0x1 stage=1 granule=0x1000 level=1' \
  'APOLLO_SMMU_TBU: architectural table walk stream-id=0x1 stage=1 granule=0x1000 level=2' \
  'APOLLO_SMMU_TBU: architectural descriptor walk stream-id=0x1' \
  'APOLLO_SMMU_TBU: architectural descriptor walk stream-id=0x1 stage=1 granule=0x1000 start-level=0' \
  'levels=4 desc-pa=' \
  'APOLLO_SMMU_TBU: architected ATS translation response stream-id=0x1' \
  'APOLLO_SMMU_TBU: architected PRI response stream-id=0x1' \
  'APOLLO_SMMU_TBU: architected fault replay queued stream-id=0x1' \
  'APOLLO_SMMU_TBU: page-table walk stream-id=0x1' \
  'APOLLO_SMMU_TBU: ATS cache fill stream-id=0x1' \
  'APOLLO_SMMU_TBU: PRI request resolved stream-id=0x1' \
  'APOLLO_SMMU_TBU: fault queue push stream-id=0x1' \
  'dynamic SMMU SG map refreshed bytes=131072 segments=8' \
  'IREE Apollo Hexagon HAL: drm-accel device=/dev/accel/accel' \
  'APOLLO_HEXAGON_DMA: firmware requested DMA src=0x' \
  'APOLLO_HEXAGON_DMA: path=smmu-translated stream-id=0x1 pasid-valid=1 pasid=0x3' \
  'APOLLO_SMMU_TBU: ATS cache fill stream-id=0x1' \
  'ssid=0x3' \
  'endpoint-ssid=0x3' \
  'APOLLO_HEXAGON_DMA: DMA copy complete src=0x' \
  'SMMUv3 RIL TLBI_NH_VA range selftest ok' \
  'APOLLO_HEXAGON_DMA: job status=0x1' \
  'APOLLO_HEXAGON_DMA: async irq pending queue=0' \
  'APOLLO_HEXAGON_DMA: async irq pending queue=1' \
  'async fence irq wait signaled queue=' \
  'SG DMA stress ok queue=0' \
  'bytes=131072 segments=8' \
  'accelerator tiny cnn ok' \
  'IREE Apollo Hexagon HAL: upstream-style HAL registry device=apollo-hexagon driver=apollo-hexagon-hal' \
  'IREE Apollo Hexagon HAL: dynamically registered C HAL plugin=' \
  'IREE Apollo Hexagon HAL: executable_plugin compatibility export=iree_hal_executable_plugin_query staged' \
  'IREE Apollo Hexagon HAL: queues=2 command-buffer=fixed fence=async-irq-poll' \
  'IREE Apollo Hexagon HAL: command buffer submitted' \
  'IREE Apollo Hexagon HAL: offload complete' \
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
