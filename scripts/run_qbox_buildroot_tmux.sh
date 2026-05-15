#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
session=${QBOX_TMUX_SESSION:-qbox-buildroot}
socket_name=${QBOX_TMUX_SOCKET:-"${session}"}
log_dir=${QBOX_VERIFICATION_DIR:-"${repo_root}/build/verification"}
stamp=$(date +%Y%m%d-%H%M%S)
log_path=${QBOX_TMUX_LOG:-"${log_dir}/qbox-buildroot-tmux-${stamp}.log"}
boot_timeout=${QBOX_BOOT_TIMEOUT:-0}
kill_key_primary=${QBOX_TMUX_KILL_KEY:-F12}
kill_key_secondary=${QBOX_TMUX_KILL_KEY_ALT:-C-g}
attach=1

usage() {
  cat <<EOF_USAGE
Usage: $(basename "$0") [--no-attach] [--session NAME] [--socket NAME] [--log PATH]

Launch QBox Buildroot in an isolated tmux server with this layout:
  top 70%: left UART/guest shell 70%, right Hexagon/SMMU log 30%
  bottom 30%: host shell

Hotkeys inside the tmux session:
  ${kill_key_primary} or ${kill_key_secondary}: terminate the tmux session and QBox
  tmux prefix + Q: terminate the tmux session and QBox
  mouse: enabled for pane selection, resize, and scrollback

Environment:
  QBOX_BOOT_TIMEOUT       forwarded to run_qbox_buildroot_boot.sh, default 0
  QBOX_TMUX_SESSION      tmux session name, default qbox-buildroot
  QBOX_TMUX_SOCKET       isolated tmux socket name, default session name
  QBOX_TMUX_LOG          shared QBox log path
  QBOX_TMUX_HEXAGON_FILTER
                          grep -E filter for the right pane
  QBOX_TMUX_KILL_KEY     primary tmux root-table kill key, default F12
  QBOX_TMUX_KILL_KEY_ALT secondary tmux root-table kill key, default C-g
EOF_USAGE
}

while (($#)); do
  case "$1" in
    --no-attach)
      attach=0
      shift
      ;;
    --session)
      if (($# < 2)); then
        echo "--session requires a value" >&2
        exit 2
      fi
      session=$2
      if [[ -z "${QBOX_TMUX_SOCKET:-}" ]]; then
        socket_name=${session}
      fi
      shift 2
      ;;
    --socket)
      if (($# < 2)); then
        echo "--socket requires a value" >&2
        exit 2
      fi
      socket_name=$2
      shift 2
      ;;
    --log)
      if (($# < 2)); then
        echo "--log requires a value" >&2
        exit 2
      fi
      log_path=$2
      shift 2
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

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux is required but was not found in PATH" >&2
  exit 1
fi

if [[ "${log_path}" != /* ]]; then
  log_path="${repo_root}/${log_path}"
fi

run_dir="${repo_root}/build/qbox-tmux/${session}"
mkdir -p "${run_dir}" "$(dirname "${log_path}")"

tmux_cmd=(tmux -L "${socket_name}")
if "${tmux_cmd[@]}" has-session -t "${session}" 2>/dev/null; then
  cat >&2 <<EOF_EXISTS
tmux session already exists on socket '${socket_name}': ${session}
Attach with:
  tmux -L ${socket_name} attach-session -t ${session}
Terminate with:
  tmux -L ${socket_name} kill-session -t ${session}
EOF_EXISTS
  exit 1
fi

quote() {
  printf "%q" "$1"
}

hexagon_filter=${QBOX_TMUX_HEXAGON_FILTER:-'APOLLO_HEXAGON|APOLLO_SMMU_TBU|IREE Apollo Hexagon|apollo-hexagon|hexagon|Hexagon|SMMU|smmu'}

left_script="${run_dir}/left-uart.sh"
right_script="${run_dir}/right-hexagon-log.sh"
bottom_script="${run_dir}/bottom-host-shell.sh"

cat > "${left_script}" <<'EOF_LEFT'
#!/usr/bin/env bash
set -euo pipefail

cd "${QBOX_TMUX_REPO_ROOT}"
clear
printf 'QBox UART + guest shell pane\n'
printf 'Log file: %s\n' "${QBOX_TMUX_LOG}"
printf 'Terminate tmux/QBox: %s or %s\n\n' \
  "${QBOX_TMUX_KILL_KEY_PRIMARY}" "${QBOX_TMUX_KILL_KEY_SECONDARY}"

set +e
QBOX_BOOT_LOG="${QBOX_TMUX_LOG}" \
QBOX_BOOT_TIMEOUT="${QBOX_TMUX_BOOT_TIMEOUT}" \
  "${QBOX_TMUX_REPO_ROOT}/scripts/run_qbox_buildroot_boot.sh"
rc=$?
set -e

printf '\nQBox exited with rc=%s. Dropping to a host shell in this pane.\n' "${rc}"
exec "${SHELL:-/bin/bash}" -l
EOF_LEFT

cat > "${right_script}" <<'EOF_RIGHT'
#!/usr/bin/env bash
set -euo pipefail

clear
touch "${QBOX_TMUX_LOG}"
printf 'Hexagon/SMMU log pane\n'
printf 'Following: %s\n' "${QBOX_TMUX_LOG}"
printf 'Filter: %s\n' "${QBOX_TMUX_HEXAGON_FILTER}"
printf 'Terminate tmux/QBox: %s or %s\n\n' \
  "${QBOX_TMUX_KILL_KEY_PRIMARY}" "${QBOX_TMUX_KILL_KEY_SECONDARY}"

tail -n +1 -F "${QBOX_TMUX_LOG}" \
  | grep --line-buffered -E "${QBOX_TMUX_HEXAGON_FILTER}" || true

exec "${SHELL:-/bin/bash}" -l
EOF_RIGHT

cat > "${bottom_script}" <<'EOF_BOTTOM'
#!/usr/bin/env bash
set -euo pipefail

cd "${QBOX_TMUX_REPO_ROOT}"
clear
cat <<EOF_SHELL
Host command pane
Repository: ${QBOX_TMUX_REPO_ROOT}
QBox log:   ${QBOX_TMUX_LOG}

Useful commands:
  scripts/run_iree_vector_add_hexagon_qbox_ssh.sh
  tail -F "${QBOX_TMUX_LOG}"
  grep -E 'apollo-hexagon|APOLLO_HEXAGON|APOLLO_SMMU_TBU|4xf32' "${QBOX_TMUX_LOG}"

Terminate tmux/QBox with ${QBOX_TMUX_KILL_KEY_PRIMARY}, ${QBOX_TMUX_KILL_KEY_SECONDARY}, or prefix + Q.
EOF_SHELL

exec "${SHELL:-/bin/bash}" -l
EOF_BOTTOM

chmod 0755 "${left_script}" "${right_script}" "${bottom_script}"

common_env=(
  QBOX_TMUX_REPO_ROOT="${repo_root}"
  QBOX_TMUX_LOG="${log_path}"
  QBOX_TMUX_BOOT_TIMEOUT="${boot_timeout}"
  QBOX_TMUX_HEXAGON_FILTER="${hexagon_filter}"
  QBOX_TMUX_KILL_KEY_PRIMARY="${kill_key_primary}"
  QBOX_TMUX_KILL_KEY_SECONDARY="${kill_key_secondary}"
)

env_prefix=""
for item in "${common_env[@]}"; do
  env_prefix+="$(quote "${item%%=*}")=$(quote "${item#*=}") "
done

left_pane=$("${tmux_cmd[@]}" new-session -d -s "${session}" -n qbox \
  -c "${repo_root}" -P -F "#{pane_id}")
window_id=$("${tmux_cmd[@]}" display-message -p -t "${left_pane}" "#{window_id}")
"${tmux_cmd[@]}" set-option -t "${session}" status-left "[${session}] "
"${tmux_cmd[@]}" set-option -t "${session}" status-right " ${kill_key_primary}/${kill_key_secondary}: kill "
"${tmux_cmd[@]}" set-option -t "${session}" mouse on
"${tmux_cmd[@]}" set-window-option -t "${window_id}" pane-border-status top
"${tmux_cmd[@]}" select-pane -t "${left_pane}" -T "UART + guest shell"
bottom_pane=$("${tmux_cmd[@]}" split-window -v -l 30% -t "${left_pane}" \
  -c "${repo_root}" -P -F "#{pane_id}")
"${tmux_cmd[@]}" select-pane -t "${bottom_pane}" -T "host shell"
right_pane=$("${tmux_cmd[@]}" split-window -h -l 30% -t "${left_pane}" \
  -c "${repo_root}" -P -F "#{pane_id}")
"${tmux_cmd[@]}" select-pane -t "${right_pane}" -T "Hexagon/SMMU log"
"${tmux_cmd[@]}" select-pane -t "${left_pane}"

"${tmux_cmd[@]}" bind-key -n "${kill_key_primary}" \
  confirm-before -p "Terminate QBox tmux session ${session}? (y/n)" \
  "kill-session -t ${session}"
"${tmux_cmd[@]}" bind-key -n "${kill_key_secondary}" \
  confirm-before -p "Terminate QBox tmux session ${session}? (y/n)" \
  "kill-session -t ${session}"
"${tmux_cmd[@]}" bind-key Q \
  confirm-before -p "Terminate QBox tmux session ${session}? (y/n)" \
  "kill-session -t ${session}"

"${tmux_cmd[@]}" send-keys -t "${right_pane}" "${env_prefix}$(quote "${right_script}")" C-m
"${tmux_cmd[@]}" send-keys -t "${bottom_pane}" "${env_prefix}$(quote "${bottom_script}")" C-m
"${tmux_cmd[@]}" send-keys -t "${left_pane}" "${env_prefix}$(quote "${left_script}")" C-m

cat <<EOF_STARTED
Started QBox tmux session.
  session: ${session}
  socket:  ${socket_name}
  log:     ${log_path}
  attach:  tmux -L ${socket_name} attach-session -t ${session}
  kill:    ${kill_key_primary}, ${kill_key_secondary}, or tmux -L ${socket_name} kill-session -t ${session}
EOF_STARTED

if (( attach )); then
  exec "${tmux_cmd[@]}" attach-session -t "${session}"
fi
