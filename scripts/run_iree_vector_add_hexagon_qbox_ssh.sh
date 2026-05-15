#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
host=${QBOX_SSH_HOST:-127.0.0.1}
port=${QBOX_SSH_PORT:-2222}
user=${QBOX_SSH_USER:-root}
timeout_s=${QBOX_SSH_TIMEOUT:-90}
guest_cmd=${QBOX_IREE_VECTOR_ADD_GUEST_CMD:-/opt/qbox/iree/vector-add/run_vector_add_hexagon_guest.sh}
expected=${QBOX_IREE_VECTOR_ADD_EXPECTED:-'4xf32=11 22 33 44'}
log_dir=${QBOX_VERIFICATION_DIR:-"${repo_root}/build/verification"}
stamp=${QBOX_IREE_VECTOR_ADD_SSH_STAMP:-$(date +%Y%m%d-%H%M%S)}
log_path=${QBOX_IREE_VECTOR_ADD_SSH_LOG:-"${log_dir}/qbox-iree-vector-add-hexagon-ssh-${stamp}.log"}
qbox_log=${QBOX_TMUX_LOG:-${QBOX_BOOT_LOG:-}}
identity_file=${QBOX_SSH_IDENTITY:-}
auto_auth=1
wait_for_ssh=1
print_command=0

usage() {
  cat <<EOF_USAGE
Usage: $(basename "$0") [options]

Run the staged IREE vector-add model inside a booted QBox Linux guest over SSH.
The default target matches scripts/run_qbox_buildroot_boot.sh user networking:
  ssh ${user}@${host} -p ${port}

Options:
  --host HOST          SSH host, default ${host}
  --port PORT          SSH port, default ${port}
  --user USER          SSH user, default ${user}
  --cmd PATH           guest script, default ${guest_cmd}
  --timeout SECONDS    TCP wait timeout, default ${timeout_s}
  --log PATH           host-side log path
  --identity PATH      SSH private key path
  --no-wait            skip waiting for the SSH TCP port
  --interactive-auth   let ssh prompt on the tmux pane instead of askpass
  --print-command      print the SSH command summary and exit
  -h, --help           show this help

Environment:
  QBOX_SSH_PASSWORD    password used by askpass; default is empty
  QBOX_TMUX_LOG        optional QBox UART/SystemC log for host-side markers

Default Buildroot images from this repo allow root SSH with an empty password.
EOF_USAGE
}

while (($#)); do
  case "$1" in
    --host)
      [[ $# -ge 2 ]] || { echo "--host requires a value" >&2; exit 2; }
      host=$2
      shift 2
      ;;
    --port)
      [[ $# -ge 2 ]] || { echo "--port requires a value" >&2; exit 2; }
      port=$2
      shift 2
      ;;
    --user)
      [[ $# -ge 2 ]] || { echo "--user requires a value" >&2; exit 2; }
      user=$2
      shift 2
      ;;
    --cmd)
      [[ $# -ge 2 ]] || { echo "--cmd requires a value" >&2; exit 2; }
      guest_cmd=$2
      shift 2
      ;;
    --timeout)
      [[ $# -ge 2 ]] || { echo "--timeout requires a value" >&2; exit 2; }
      timeout_s=$2
      shift 2
      ;;
    --log)
      [[ $# -ge 2 ]] || { echo "--log requires a value" >&2; exit 2; }
      log_path=$2
      shift 2
      ;;
    --identity)
      [[ $# -ge 2 ]] || { echo "--identity requires a value" >&2; exit 2; }
      identity_file=$2
      shift 2
      ;;
    --no-wait)
      wait_for_ssh=0
      shift
      ;;
    --interactive-auth)
      auto_auth=0
      shift
      ;;
    --print-command)
      print_command=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if ! [[ "${port}" =~ ^[0-9]+$ ]]; then
  echo "SSH port must be numeric: ${port}" >&2
  exit 2
fi
if ! [[ "${timeout_s}" =~ ^[0-9]+$ ]]; then
  echo "timeout must be numeric seconds: ${timeout_s}" >&2
  exit 2
fi
if ! command -v ssh >/dev/null 2>&1; then
  echo "ssh is required but was not found in PATH" >&2
  exit 1
fi

if [[ "${log_path}" != /* ]]; then
  log_path="${repo_root}/${log_path}"
fi
mkdir -p "$(dirname "${log_path}")"

shell_quote() {
  local value=$1
  printf "'%s'" "$(printf '%s' "${value}" | sed "s/'/'\\\\''/g")"
}

wait_for_tcp() {
  local deadline now
  deadline=$((SECONDS + timeout_s))

  while :; do
    if command -v nc >/dev/null 2>&1; then
      if nc -z "${host}" "${port}" >/dev/null 2>&1; then
        return 0
      fi
    elif timeout 1 bash -c ":</dev/tcp/${host}/${port}" >/dev/null 2>&1; then
      return 0
    fi

    now=${SECONDS}
    if (( now >= deadline )); then
      return 1
    fi
    sleep 1
  done
}

wait_for_ssh_ready() {
  local deadline now
  deadline=$((SECONDS + timeout_s))

  while :; do
    if "${ssh_base_cmd[@]}" true >/dev/null 2>&1; then
      return 0
    fi

    now=${SECONDS}
    if (( now >= deadline )); then
      return 1
    fi
    sleep 2
  done
}

make_askpass() {
  local askpass_dir askpass
  askpass_dir=$(mktemp -d "${TMPDIR:-/tmp}/qbox-ssh-askpass.XXXXXX")
  askpass="${askpass_dir}/askpass.sh"
  cat > "${askpass}" <<'EOF_ASKPASS'
#!/bin/sh
printf '%s\n' "${QBOX_SSH_PASSWORD:-}"
EOF_ASKPASS
  chmod 0700 "${askpass}"
  printf '%s\n' "${askpass_dir}"
}

ssh_opts=(
  -p "${port}"
  -o StrictHostKeyChecking=no
  -o UserKnownHostsFile=/dev/null
  -o LogLevel=ERROR
  -o ConnectTimeout=5
  -o ServerAliveInterval=5
  -o ServerAliveCountMax=1
  -o NumberOfPasswordPrompts=1
  -o PreferredAuthentications=publickey,password,keyboard-interactive
)
if [[ -n "${identity_file}" ]]; then
  ssh_opts+=(-i "${identity_file}")
fi

askpass_dir=""
ssh_base_cmd=(ssh "${ssh_opts[@]}" "${user}@${host}")
if (( auto_auth )); then
  if command -v setsid >/dev/null 2>&1; then
    askpass_dir=$(make_askpass)
    trap '[[ -n "${askpass_dir}" ]] && rm -rf "${askpass_dir}"' EXIT
    ssh_base_cmd=(
      setsid env
      DISPLAY="${DISPLAY:-qbox}"
      SSH_ASKPASS="${askpass_dir}/askpass.sh"
      SSH_ASKPASS_REQUIRE=force
      QBOX_SSH_PASSWORD="${QBOX_SSH_PASSWORD-}"
      "${ssh_base_cmd[@]}"
    )
  else
    echo "setsid not found; falling back to interactive SSH authentication" >&2
  fi
fi

quoted_guest_cmd=$(shell_quote "${guest_cmd}")
remote_cmd=$(cat <<EOF_REMOTE
set -eu
if [ ! -x ${quoted_guest_cmd} ]; then
  echo 'missing executable guest vector-add script: ${guest_cmd}' >&2
  echo 'expected staged artifacts under /opt/qbox/iree/vector-add' >&2
  exit 127
fi
printf 'REMOTE: '
uname -n -m
echo 'REMOTE: running ${guest_cmd}'
${quoted_guest_cmd}
echo 'REMOTE: dmesg vector-add/SMMU markers'
if command -v dmesg >/dev/null 2>&1; then
  dmesg | tail -n 240 | grep -E 'accelerator vector add ok|SMMUv3 page-table walker|dynamic SMMU map refreshed|async fence signaled' || true
fi
EOF_REMOTE
)

cat <<EOF_RUN
QBox IREE vector-add over SSH
  target: ${user}@${host}:${port}
  guest:  ${guest_cmd}
  log:    ${log_path}
EOF_RUN
if [[ -n "${qbox_log}" ]]; then
  printf '  qbox:   %s\n' "${qbox_log}"
fi

if (( print_command )); then
  printf 'ssh'
  printf ' %q' "${ssh_opts[@]}" "${user}@${host}" "${remote_cmd}"
  printf '\n'
  exit 0
fi

if (( wait_for_ssh )); then
  if ! wait_for_tcp; then
    cat >&2 <<EOF_WAIT
Timed out waiting for SSH TCP ${host}:${port}.

Check:
  - QBox is still running in the tmux UART pane.
  - The boot script kept host forwarding enabled: hostfwd=tcp::${port}-:22.
  - The Buildroot rootfs was rebuilt after enabling OpenSSH.
  - The guest network brought up eth0 through DHCP.
EOF_WAIT
    exit 1
  fi
  if (( auto_auth )) && [[ -n "${askpass_dir}" ]]; then
    if ! wait_for_ssh_ready; then
      cat >&2 <<EOF_WAIT
Timed out waiting for authenticated SSH on ${user}@${host}:${port}.

The TCP forward is open, but ssh did not complete a command before timeout.
Check the QBox UART log for network DHCP, sshd startup, and authentication
messages.
EOF_WAIT
      exit 1
    fi
  fi
fi

set +e
"${ssh_base_cmd[@]}" "${remote_cmd}" 2>&1 | tee "${log_path}"
ssh_rc=${PIPESTATUS[0]}
set -e

if [[ ${ssh_rc} -ne 0 ]]; then
  cat >&2 <<EOF_FAIL
SSH vector-add command failed: rc=${ssh_rc}
Log: ${log_path}

For the repo default empty root password, rerun with:
  QBOX_SSH_PASSWORD= scripts/run_iree_vector_add_hexagon_qbox_ssh.sh
or use --interactive-auth and press Enter at the password prompt.
EOF_FAIL
  exit "${ssh_rc}"
fi

for marker in \
  'IREE Apollo Hexagon HAL: upstream-style HAL registry' \
  'IREE Apollo Hexagon HAL: dynamically registered C HAL plugin=' \
  'IREE Apollo Hexagon HAL: offload complete' \
  'EXEC @vector_add_graph [apollo-hexagon]' \
  "${expected}" \
  'accelerator vector add ok'; do
  if ! grep -F "${marker}" "${log_path}" >/dev/null; then
    echo "missing SSH vector-add marker: ${marker}" >&2
    echo "log: ${log_path}" >&2
    exit 1
  fi
done

if [[ -n "${qbox_log}" && -f "${qbox_log}" ]]; then
  if ! grep -F 'APOLLO_HEXAGON_DMA: path=smmu-translated' "${qbox_log}" >/dev/null; then
    echo "warning: host QBox log lacks APOLLO_HEXAGON_DMA SMMU marker: ${qbox_log}" >&2
  fi
fi

cat <<EOF_PASS
PASS: QBox SSH IREE Hexagon vector-add output matched
Expected: ${expected}
Log: ${log_path}
EOF_PASS
