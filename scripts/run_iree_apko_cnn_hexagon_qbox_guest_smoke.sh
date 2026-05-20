#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
log_dir=${QBOX_VERIFICATION_DIR:-"${repo_root}/build/verification"}
stamp=${QBOX_APKO_CNN_HEXAGON_GUEST_SMOKE_STAMP:-$(date +%Y%m%d-%H%M%S)}
log_path=${QBOX_APKO_CNN_HEXAGON_GUEST_SMOKE_LOG:-"${log_dir}/qbox-iree-apko-cnn-hexagon-guest-${stamp}.log"}
boot_log=${QBOX_BOOT_LOG:-"${log_dir}/qbox-iree-apko-cnn-hexagon-guest-boot-${stamp}.log"}
expected='1x1x2x2xf32=[[[54 63][90 99]]]'
cmd='/opt/qbox/iree/tiny-cnn/run_tiny_cnn_apko_hexagon_guest.sh'

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
  echo "QBox APKO CNN guest smoke exited unexpectedly: rc=${rc}" >&2
  exit "${rc}"
fi

for marker in \
  'Run /sbin/init as init process' \
  'apollo-qbox login:' \
  'userspace submit ABI ready at /dev/accel/accel*' \
  'dma path smmu-translated caps=0x7d stream-id=' \
  'arm-smmu-v3 dma-iommu map installed' \
  'IREE Apollo Hexagon HAL: drm-accel device=/dev/accel/accel' \
  'IREE Apollo Hexagon HAL: executable_format=apollo-hexagon-apko-v0' \
  'IREE Apollo Hexagon HAL: queues=2 command-buffer=generic-submit' \
  'IREE Apollo Hexagon HAL: generic_abi_version=1 executable_formats=0x00000002' \
  'APOLLO_HEXAGON_DMA: command load payload slot=1 opcode=1' \
  'APOLLO_HEXAGON_DMA: command load code slot=1 offset=0 words=2 entry=65537' \
  'APOLLO_HEXAGON_DMA: APKO code program dispatch pc=0 opcode=1' \
  'APOLLO_HEXAGON_DMA: APKO code program end pc=1' \
  'code_words=2' \
  'code_entry=65537' \
  'code_end=131072' \
  'APOLLO_HEXAGON_DMA: command dispatch executable slot=1 kind=1' \
  'APOLLO_HEXAGON_DMA: command dispatch cnn' \
  'IREE Apollo Hexagon HAL: APKO CMD_SUBMIT CNN ok' \
  'IREE Apollo Hexagon HAL: command buffer submitted' \
  'IREE Apollo Hexagon HAL: offload complete' \
  'async fence signaled queue=' \
  'EXEC @tiny_cnn_graph [apollo-hexagon]'; do
  if ! grep -F "${marker}" "${log_path}" >/dev/null; then
    echo "missing APKO CNN marker: ${marker}" >&2
    echo "log: ${log_path}" >&2
    exit 1
  fi
done

if ! grep -F 'LOAD_EXECUTABLE slot=1 kind=1' "${log_path}" >/dev/null && \
   ! grep -F 'APOLLO_HEXAGON_DMA: command load executable slot=1 kind=1' \
      "${log_path}" >/dev/null; then
  echo "missing APKO CNN marker: LOAD_EXECUTABLE slot=1 kind=1" >&2
  echo "log: ${log_path}" >&2
  exit 1
fi

if ! grep -F 'LOAD_PAYLOAD slot=1 opcode=1' "${log_path}" >/dev/null && \
   ! grep -F 'APOLLO_HEXAGON_DMA: command load payload slot=1 opcode=1' \
      "${log_path}" >/dev/null; then
  echo "missing APKO CNN marker: LOAD_PAYLOAD slot=1 opcode=1" >&2
  echo "log: ${log_path}" >&2
  exit 1
fi

if ! grep -F 'LOAD_CODE slot=1 offset=0 words=2 entry_word=65537' \
      "${log_path}" >/dev/null && \
   ! grep -F 'APOLLO_HEXAGON_DMA: command load code slot=1 offset=0 words=2 entry=65537' \
      "${log_path}" >/dev/null; then
  echo "missing APKO CNN marker: LOAD_CODE slot=1 entry=65537" >&2
  echo "log: ${log_path}" >&2
  exit 1
fi

if ! grep -F "${expected}" "${log_path}" >/dev/null; then
  echo "APKO CNN output mismatch; expected: ${expected}" >&2
  echo "log: ${log_path}" >&2
  exit 1
fi

cat <<EOF
PASS: QBox guest APKO CNN output matched
Expected: ${expected}
Log: ${log_path}
Boot log: ${boot_log}
EOF
