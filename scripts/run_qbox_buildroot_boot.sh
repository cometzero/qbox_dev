#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
qbox_root=${QBOX_ROOT:-"${repo_root}/sources/qbox"}
vp=${QBOX_PLATFORMS_VP:-"${qbox_root}/build/platforms-vp"}
log_dir=${QBOX_VERIFICATION_DIR:-"${repo_root}/build/verification"}
timeout_s=${QBOX_BOOT_TIMEOUT:-0}
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

run_cmd=("${vp}" -l platforms/buildroot/conf_aarch64.lua)
if [[ "${timeout_s}" != "0" ]]; then
  run_cmd=(timeout --signal=SIGQUIT "${timeout_s}s" "${run_cmd[@]}")
fi

if [[ "${timeout_s}" == "0" ]]; then
  timeout_msg="disabled; interactive run continues until Ctrl-C"
else
  timeout_msg="${timeout_s}s"
fi

cat >&2 <<EOF_MSG
Streaming QBox UART log to stdout.
Log file: ${log_path}
Timeout: ${timeout_msg}
At the Buildroot login prompt: user=root, no password.
Exit the shell with: exit  (or Ctrl-D). Stop QBox simulation with: Ctrl-C.
EOF_MSG

cd "${qbox_root}"

# Run through a pseudo-TTY by default so QBox/SystemC keeps stdio-backed UARTs
# alive and flushes guest output immediately while still recording the log. This
# matters even in non-interactive CI/Codex runs: without a PTY, QBox can observe
# stdin EOF and stop before the login prompt. Use the repo-local Python runner
# first because util-linux script(1) can propagate a transient stdin EOF/HUP to
# the child PTY on the first cold run after a rebuild. Set QBOX_BOOT_PTY=0 to
# force the plain line-buffered path.
pty_runner="${repo_root}/scripts/qbox_pty_runner.py"
if [[ "${QBOX_BOOT_PTY:-1}" != "0" ]] && command -v python3 >/dev/null 2>&1 && [[ -x "${pty_runner}" ]]; then
  python3 "${pty_runner}" --log "${log_path}" -- "${run_cmd[@]}"
elif [[ "${QBOX_BOOT_PTY:-1}" != "0" ]] && command -v script >/dev/null 2>&1; then
  quoted_cmd=$(printf '%q ' "${run_cmd[@]}")
  script -qefc "${quoted_cmd% }" "${log_path}"
else
  if command -v stdbuf >/dev/null 2>&1; then
    stdbuf -oL -eL "${run_cmd[@]}" 2>&1 | tee "${log_path}"
  else
    "${run_cmd[@]}" 2>&1 | tee "${log_path}"
  fi
fi
