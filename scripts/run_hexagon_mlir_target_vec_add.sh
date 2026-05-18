#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
mode=${QBOX_HEXAGON_MLIR_EXEC_MODE:-device}
preflight_only=0
report=${QBOX_HEXAGON_MLIR_TARGET_REPORT:-"${repo_root}/build/verification/hexagon-mlir-target-execution-$(date +%Y%m%d-%H%M%S).json"}

usage() {
  cat <<'EOF'
usage: run_hexagon_mlir_target_vec_add.sh [--mode device|simulator] [--preflight-only] [--report PATH]

Runs the upstream Hexagon-MLIR vector-add smoke when the Qualcomm target
runtime is available. The QBox Apollo path is not a direct Hexagon-MLIR target;
use scripts/check_hexagon_mlir_target_execution.py for the QBox boundary report.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      mode=${2:?missing value for --mode}
      shift 2
      ;;
    --mode=*)
      mode=${1#--mode=}
      shift
      ;;
    --preflight-only)
      preflight_only=1
      shift
      ;;
    --report)
      report=${2:?missing value for --report}
      shift 2
      ;;
    --report=*)
      report=${1#--report=}
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
done

case "${mode}" in
  device|simulator)
    ;;
  *)
    echo "unsupported mode: ${mode}" >&2
    usage >&2
    exit 2
    ;;
esac

mkdir -p "$(dirname "${report}")"
"${repo_root}/scripts/check_hexagon_mlir_target_execution.py" \
  --repo "${repo_root}" \
  --json "${report}"

if [[ "${preflight_only}" == "1" ]]; then
  echo "Hexagon-MLIR target preflight report: ${report}"
  exit 0
fi

"${repo_root}/scripts/check_hexagon_mlir_target_execution.py" \
  --repo "${repo_root}" \
  --require "${mode}"

cd "${repo_root}/sources/hexagon-mlir"

if [[ -f scripts/set_local_env.sh ]]; then
  # shellcheck source=/dev/null
  source scripts/set_local_env.sh
fi

case "${mode}" in
  device)
    export RUN_ON_SIM=0
    ;;
  simulator)
    export RUN_ON_SIM=1
    ;;
esac

export TRITON_ALWAYS_COMPILE=${TRITON_ALWAYS_COMPILE:-1}
pytest -sv test/python/triton/test_vec_add.py
