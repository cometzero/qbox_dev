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
  sleep "${QBOX_IREE_LOGIN_DELAY:-7}"
  printf 'root\r'
  sleep "${QBOX_IREE_COMMAND_DELAY:-2}"
  printf '%s\r' "${cmd}"
  sleep "${QBOX_IREE_AFTER_COMMAND_DELAY:-8}"
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
  'APOLLO_SMMU_TBU: map stream-id=0x1' \
  'APOLLO_SMMU_TBU: unmap stream-id=0x1' \
  'APOLLO_HEXAGON_DMA: job status=0x1' \
  'accelerator tiny cnn ok' \
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
