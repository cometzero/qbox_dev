#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
smoke_out=${QBOX_IREE_SMOKE_OUT:-"${repo_root}/build/verification/iree-tiny-cnn-host"}
stage_dir=${QBOX_IREE_GUEST_STAGE_DIR:-"${repo_root}/build/iree-guest-artifacts/tiny-cnn"}

"${repo_root}/scripts/run_iree_tiny_cnn_host_smoke.sh"

required=(
  "${smoke_out}/tiny_cnn.onnx"
  "${smoke_out}/tiny_cnn.mlir"
  "${smoke_out}/tiny_cnn_cpu.vmfb"
  "${smoke_out}/tiny_cnn_aarch64.vmfb"
  "${smoke_out}/reference.json"
  "${smoke_out}/report.json"
)
for path in "${required[@]}"; do
  if [[ ! -s "${path}" ]]; then
    echo "missing generated IREE artifact: ${path}" >&2
    exit 1
  fi
done

rm -rf "${stage_dir}"
install -d "${stage_dir}"
install -m 0644 "${smoke_out}/tiny_cnn.onnx" "${stage_dir}/tiny_cnn.onnx"
install -m 0644 "${smoke_out}/tiny_cnn.mlir" "${stage_dir}/tiny_cnn.mlir"
install -m 0644 "${smoke_out}/tiny_cnn_aarch64.vmfb" "${stage_dir}/tiny_cnn_aarch64.vmfb"
install -m 0644 "${smoke_out}/reference.json" "${stage_dir}/reference.json"
install -m 0644 "${smoke_out}/report.json" "${stage_dir}/host-report.json"

cat > "${stage_dir}/run_tiny_cnn_guest.sh" <<'GUEST'
#!/bin/sh
set -eu

module=${1:-/opt/qbox/iree/tiny-cnn/tiny_cnn_aarch64.vmfb}
if ! command -v iree-run-module >/dev/null 2>&1; then
  echo "iree-run-module is not installed in this Buildroot image." >&2
  echo "The VMFB and reference fixture are staged; add an AArch64 IREE runtime package next." >&2
  exit 127
fi

exec iree-run-module \
  --module="${module}" \
  --device=local-task \
  --function=tiny_cnn_graph \
  --input='1x1x4x4xf32=[1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16]'
GUEST
chmod 0755 "${stage_dir}/run_tiny_cnn_guest.sh"

python3 - "${stage_dir}" <<'PY'
from pathlib import Path
import json
import os
import sys
stage = Path(sys.argv[1])
manifest = {
    'name': 'apollo-qbox-iree-tiny-cnn-guest-artifacts',
    'status': 'staged',
    'target': 'aarch64-unknown-linux-gnu llvm-cpu local-task',
    'guest_install_path': '/opt/qbox/iree/tiny-cnn',
    'expected_output': '1x1x2x2xf32=[[[54 63][90 99]]]',
    'files': {p.name: p.stat().st_size for p in sorted(stage.iterdir()) if p.is_file()},
    'next_requirement': 'Package an AArch64 iree-run-module or custom IREE C runner into Buildroot to execute this VMFB in guest.',
}
(stage / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
print(json.dumps(manifest, indent=2))
PY

cat <<EOF
Staged IREE tiny-CNN guest artifacts: ${stage_dir}
To include them in the next Buildroot rootfs build, run:
  QBOX_IREE_GUEST_ARTIFACTS_DIR='${stage_dir}' ./scripts/build_qbox_buildroot_arm64.sh
EOF
