#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
log_dir=${QBOX_VERIFICATION_DIR:-"${repo_root}/build/verification"}
stamp=${QBOX_IREE_RUNTIME_PIPELINE_STAMP:-$(date +%Y%m%d-%H%M%S)}
readiness_json=${QBOX_IREE_RUNTIME_READINESS_JSON:-"${log_dir}/iree-runtime-pipeline-readiness-${stamp}.json"}
apko_json=${QBOX_IREE_RUNTIME_APKO_JSON:-"${log_dir}/iree-runtime-pipeline-apko-${stamp}.json"}
guest_summary_log=${QBOX_IREE_RUNTIME_GUEST_SUMMARY_LOG:-"${log_dir}/iree-runtime-pipeline-guest-${stamp}.log"}

run_guest_smoke=1
require_host_tools=0

usage() {
  cat <<'EOF'
Usage: ./scripts/check_iree_runtime_pipeline.sh [options]

Checks the repo-local Apollo QBox IREE runtime pipeline.

Default:
  1. Run IREE readiness checks.
  2. Run APKO/VMFB transition-lane checks.
  3. Boot QBox and run the APKO VADD Hexagon guest smoke.

Options:
  --quick               Skip the QBox guest smoke; run static/readiness checks only.
  --require-host-tools  Treat missing host IREE/ONNX tools as failures.
  -h, --help            Show this help.

Useful environment overrides:
  QBOX_VERIFICATION_DIR
  QBOX_IREE_RUNTIME_PIPELINE_STAMP
  QBOX_BOOT_TIMEOUT
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --quick)
      run_guest_smoke=0
      ;;
    --require-host-tools)
      require_host_tools=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

mkdir -p "${log_dir}"

echo "Workspace: ${repo_root}"
echo "Stamp: ${stamp}"
echo

readiness_args=(--repo "${repo_root}" --json "${readiness_json}")
apko_args=(--repo "${repo_root}" --json "${apko_json}")
if [[ "${require_host_tools}" -eq 1 ]]; then
  readiness_args+=(--require-host-tools)
  apko_args+=(--require-host-tools)
fi

echo "== IREE readiness =="
python3 "${repo_root}/scripts/check_iree_cnn_pipeline_readiness.py" "${readiness_args[@]}"
echo

echo "== APKO/VMFB transition lane =="
python3 "${repo_root}/scripts/check_apko_vmfb_verification_lane.py" "${apko_args[@]}"
echo

if [[ "${run_guest_smoke}" -eq 1 ]]; then
  echo "== QBox guest APKO VADD smoke =="
  QBOX_APKO_VADD_HEXAGON_GUEST_SMOKE_STAMP="${stamp}" \
    QBOX_BOOT_TIMEOUT="${QBOX_BOOT_TIMEOUT:-80}" \
    "${repo_root}/scripts/run_iree_apko_vadd_hexagon_qbox_guest_smoke.sh" \
    2>&1 | tee "${guest_summary_log}"
  echo
else
  guest_summary_log="skipped (--quick)"
fi

cat <<EOF
PASS: IREE runtime pipeline check completed

Evidence:
  Readiness JSON: ${readiness_json}
  APKO/VMFB JSON: ${apko_json}
  Guest smoke log: ${guest_summary_log}

Boundary:
  This validates the repo-local Apollo QBox runtime pipeline. It does not claim
  upstream IREE HAL driver/backend packaging or full bit-exact Arm SMMUv3
  compliance.
EOF
