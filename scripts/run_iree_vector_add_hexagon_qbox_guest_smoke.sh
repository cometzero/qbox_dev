#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
log_dir=${QBOX_VERIFICATION_DIR:-"${repo_root}/build/verification"}
stamp=${QBOX_VECTOR_ADD_HEXAGON_GUEST_SMOKE_STAMP:-$(date +%Y%m%d-%H%M%S)}
log_path=${QBOX_VECTOR_ADD_HEXAGON_GUEST_SMOKE_LOG:-"${log_dir}/qbox-iree-vector-add-hexagon-guest-${stamp}.log"}
boot_log=${QBOX_BOOT_LOG:-"${log_dir}/qbox-iree-vector-add-hexagon-guest-boot-${stamp}.log"}
expected='4xf32=11 22 33 44'
cmd='/opt/qbox/iree/vector-add/run_vector_add_hexagon_guest.sh'

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
  echo "QBox Hexagon vector-add guest smoke exited unexpectedly: rc=${rc}" >&2
  exit "${rc}"
fi

for marker in \
  'Run /sbin/init as init process' \
  'apollo-qbox login:' \
  'userspace submit ABI ready at /dev/apollo-hexagon' \
  'dma path smmu-translated caps=0x7d stream-id=' \
  'arm-smmu-v3 dma-iommu map installed' \
  'SMMUv3 page-table walker/ATS/PRI/fault queue ready' \
  'APOLLO_SMMU_TBU: map stream-id=0x1' \
  'APOLLO_HEXAGON_DMA: path=smmu-translated stream-id=0x1' \
  'IREE Apollo Hexagon HAL: upstream-style HAL registry device=apollo-hexagon' \
  'IREE Apollo Hexagon HAL: dynamically registered C HAL plugin=' \
  'IREE Apollo Hexagon HAL: command buffer submitted' \
  'IREE Apollo Hexagon HAL: offload complete' \
  'accelerator vector add ok' \
  'EXEC @vector_add_graph [apollo-hexagon]'; do
  if ! grep -F "${marker}" "${log_path}" >/dev/null; then
    echo "missing Hexagon vector-add marker: ${marker}" >&2
    echo "log: ${log_path}" >&2
    exit 1
  fi
done

if ! grep -F "${expected}" "${log_path}" >/dev/null; then
  echo "Hexagon vector-add output mismatch; expected: ${expected}" >&2
  echo "log: ${log_path}" >&2
  exit 1
fi

cat <<EOF
PASS: QBox guest IREE Hexagon vector-add output matched
Expected: ${expected}
Log: ${log_path}
Boot log: ${boot_log}
EOF
