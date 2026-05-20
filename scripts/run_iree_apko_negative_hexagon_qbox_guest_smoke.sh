#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
log_dir=${QBOX_VERIFICATION_DIR:-"${repo_root}/build/verification"}
stamp=${QBOX_APKO_NEGATIVE_HEXAGON_GUEST_SMOKE_STAMP:-$(date +%Y%m%d-%H%M%S)}
log_path=${QBOX_APKO_NEGATIVE_HEXAGON_GUEST_SMOKE_LOG:-"${log_dir}/qbox-iree-apko-negative-hexagon-guest-${stamp}.log"}
boot_log=${QBOX_BOOT_LOG:-"${log_dir}/qbox-iree-apko-negative-hexagon-guest-boot-${stamp}.log"}
cmd='/opt/qbox/iree/vector-add/run_apko_negative_hexagon_guest.sh'

mkdir -p "${log_dir}"

set +e
(
  sleep "${QBOX_IREE_LOGIN_DELAY:-24}"
  printf 'root\r'
  sleep "${QBOX_IREE_COMMAND_DELAY:-3}"
  printf '%s\r' "${cmd}"
  sleep "${QBOX_IREE_AFTER_COMMAND_DELAY:-10}"
) | QBOX_BOOT_TIMEOUT=${QBOX_BOOT_TIMEOUT:-45} \
    QBOX_BOOT_LOG="${boot_log}" \
    "${repo_root}/scripts/run_qbox_buildroot_boot.sh" \
    > >(tee "${log_path}") 2>&1
rc=$?
set -e

if [[ ${rc} -ne 0 && ${rc} -ne 124 ]]; then
  echo "QBox APKO negative guest smoke exited unexpectedly: rc=${rc}" >&2
  exit "${rc}"
fi

for marker in \
  'Run /sbin/init as init process' \
  'apollo-qbox login:' \
  'userspace submit ABI ready at /dev/accel/accel*' \
  'APKO negative: drm-accel device=/dev/accel/accel' \
  'APKO negative: generic_abi_version=1 executable_formats=0x00000002' \
  'PASS: bad context ABI version rejected errno=Invalid argument' \
  'PASS: context create/destroy ok' \
  'PASS: destroyed context handle rejected errno=No such file or directory' \
  'PASS: bad BO size rejected errno=Invalid argument' \
  'PASS: BO create/destroy ok' \
  'PASS: destroyed BO handle rejected errno=Invalid argument' \
  'PASS: bad BO bind size rejected errno=Invalid argument' \
  'PASS: bad BO bind context rejected errno=No such file or directory' \
  'PASS: bad BO bind handle rejected errno=No such file or directory' \
  'PASS: unaligned BO bind length rejected errno=Invalid argument' \
	  'PASS: bad BO unbind size rejected errno=Invalid argument' \
	  'PASS: BO bind/unbind ok bind=' \
	  'PASS: destroyed BO bind handle rejected errno=No such file or directory' \
	  'PASS: command BO bad LOAD_EXECUTABLE fault ok' \
	  'PASS: command BO invalid IOVA fault ok' \
	  'PASS: bad WAIT size rejected errno=Invalid argument' \
  'PASS: zero WAIT fence rejected errno=Invalid argument' \
  'PASS: bad WAIT queue rejected errno=Invalid argument' \
  'PASS: WAIT completed fence=' \
  'PASS: future WAIT fence rejected errno=Connection timed out' \
  'PASS: bad APKO magic rejected errno=Invalid argument' \
  'PASS: bad APKO ABI version rejected errno=Invalid argument' \
  'PASS: bad APKO entry kind rejected errno=Invalid argument' \
  'PASS: bad APKO input byte count rejected errno=Invalid argument' \
  'PASS: nonzero APKO reserved field rejected errno=Invalid argument' \
  'PASS: wrong input byte count rejected errno=Invalid argument' \
  'PASS: wrong output byte count rejected errno=Invalid argument' \
  'PASS: wrong queue id rejected errno=Invalid argument' \
  'PASS: invalid input pointer rejected errno=Bad address' \
  'PASS: destroyed executable handle rejected errno=No such file or directory' \
  'PASS: empty fault record rejected errno=No data available' \
  'PASS: bad fault request size rejected errno=Invalid argument' \
  'PASS: APKO negative ioctl coverage completed'; do
  if ! grep -F "${marker}" "${log_path}" >/dev/null; then
    echo "missing APKO negative marker: ${marker}" >&2
    echo "log: ${log_path}" >&2
    exit 1
  fi
done

cat <<EOF
PASS: QBox guest APKO negative ioctl coverage matched
Log: ${log_path}
Boot log: ${boot_log}
EOF
