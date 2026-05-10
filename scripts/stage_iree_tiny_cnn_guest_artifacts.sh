#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
smoke_out=${QBOX_IREE_SMOKE_OUT:-"${repo_root}/build/verification/iree-tiny-cnn-host"}
stage_dir=${QBOX_IREE_GUEST_STAGE_DIR:-"${repo_root}/build/iree-guest-artifacts/tiny-cnn"}
venv_dir=${QBOX_IREE_SMOKE_VENV:-"${repo_root}/build/iree-smoke-venv"}
runtime_version=${QBOX_IREE_RUNTIME_VERSION:-3.11.0}
wheel_dir=${QBOX_IREE_AARCH64_WHEEL_DIR:-"${repo_root}/build/iree-aarch64-wheel"}
extract_dir=${QBOX_IREE_AARCH64_EXTRACT_DIR:-"${repo_root}/build/iree-aarch64-runtime-extract"}
hexagon_tools_dir=${QBOX_APOLLO_HEXAGON_TOOLS_OUT:-"${repo_root}/build/apollo-hexagon-guest-tools"}

"${repo_root}/scripts/run_iree_tiny_cnn_host_smoke.sh"
"${repo_root}/scripts/build_apollo_hexagon_guest_tools.sh"

if [[ ! -x "${venv_dir}/bin/python" ]]; then
  python3 -m venv "${venv_dir}"
fi

mkdir -p "${wheel_dir}"
if ! compgen -G "${wheel_dir}/iree_base_runtime-${runtime_version}-*aarch64*.whl" >/dev/null; then
  "${venv_dir}/bin/python" -m pip download \
    --only-binary=:all: \
    --no-deps \
    --platform manylinux_2_28_aarch64 \
    --implementation cp \
    --python-version 312 \
    --abi cp312 \
    --dest "${wheel_dir}" \
    "iree-base-runtime==${runtime_version}"
fi

rm -rf "${extract_dir}"
"${venv_dir}/bin/python" - "${wheel_dir}" "${runtime_version}" "${extract_dir}" <<'PY'
from pathlib import Path
import sys
import zipfile

wheel_dir = Path(sys.argv[1])
runtime_version = sys.argv[2]
extract_dir = Path(sys.argv[3])
wheels = sorted(wheel_dir.glob(f"iree_base_runtime-{runtime_version}-*aarch64*.whl"))
if not wheels:
    raise SystemExit(f"no aarch64 iree-base-runtime wheel found in {wheel_dir}")
wheel = wheels[-1]
needed = {
    "iree/_runtime_libs/iree-run-module",
    "iree/_runtime_libs/version.py",
}
with zipfile.ZipFile(wheel) as zf:
    names = set(zf.namelist())
    missing = sorted(needed - names)
    if missing:
        raise SystemExit(f"wheel {wheel} missing {missing}")
    for name in needed:
        zf.extract(name, extract_dir)
print(wheel)
PY

runtime_bin="${extract_dir}/iree/_runtime_libs/iree-run-module"
if [[ ! -s "${runtime_bin}" ]]; then
  echo "missing extracted AArch64 iree-run-module: ${runtime_bin}" >&2
  exit 1
fi
chmod 0755 "${runtime_bin}"

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
install -d "${stage_dir}/bin" "${stage_dir}/lib"
install -m 0755 "${runtime_bin}" "${stage_dir}/bin/iree-run-module"
install -m 0755 "${hexagon_tools_dir}/bin/apollo-iree-hexagon-runner" \
  "${stage_dir}/bin/apollo-iree-hexagon-runner"
install -m 0755 "${hexagon_tools_dir}/lib/libapollo_iree_hexagon_hal_plugin.so" \
  "${stage_dir}/lib/libapollo_iree_hexagon_hal_plugin.so"
install -m 0644 "${smoke_out}/tiny_cnn.onnx" "${stage_dir}/tiny_cnn.onnx"
install -m 0644 "${smoke_out}/tiny_cnn.mlir" "${stage_dir}/tiny_cnn.mlir"
install -m 0644 "${smoke_out}/tiny_cnn_aarch64.vmfb" "${stage_dir}/tiny_cnn_aarch64.vmfb"
install -m 0644 "${smoke_out}/reference.json" "${stage_dir}/reference.json"
install -m 0644 "${smoke_out}/report.json" "${stage_dir}/host-report.json"
cat > "${stage_dir}/apollo_hexagon.vmfb.meta" <<'META'
module=tiny_cnn_aarch64.vmfb
entry=tiny_cnn_graph
device=apollo-hexagon
expected=1x1x2x2xf32=[[[54 63][90 99]]]
plugin=lib/libapollo_iree_hexagon_hal_plugin.so
upstream_executable_plugin=iree_hal_executable_plugin_query
queue=multi
command_buffer=fixed
fence=async-irq-poll
META

cat > "${stage_dir}/run_tiny_cnn_guest.sh" <<'GUEST'
#!/bin/sh
set -eu

self_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
module=${1:-"${self_dir}/tiny_cnn_aarch64.vmfb"}
runner=${IREE_RUN_MODULE:-"${self_dir}/bin/iree-run-module"}
if [ ! -x "${runner}" ]; then
  runner=$(command -v iree-run-module || true)
fi
if [ -z "${runner}" ] || [ ! -x "${runner}" ]; then
  echo "iree-run-module is not installed in this Buildroot image." >&2
  echo "The VMFB and reference fixture are staged; add an AArch64 IREE runtime package next." >&2
  exit 127
fi

exec "${runner}" \
  --executable_plugin="${self_dir}/lib/libapollo_iree_hexagon_hal_plugin.so" \
  --module="${module}" \
  --device=local-task \
  --function=tiny_cnn_graph \
  --input='1x1x4x4xf32=[1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16]'
GUEST
chmod 0755 "${stage_dir}/run_tiny_cnn_guest.sh"

cat > "${stage_dir}/run_tiny_cnn_hexagon_guest.sh" <<'GUEST'
#!/bin/sh
set -eu

self_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
runner=${APOLLO_IREE_HEXAGON_RUNNER:-"${self_dir}/bin/apollo-iree-hexagon-runner"}
if [ ! -x "${runner}" ]; then
  echo "apollo-iree-hexagon-runner is not installed in this Buildroot image." >&2
  exit 127
fi

exec "${runner}" --metadata "${self_dir}/apollo_hexagon.vmfb.meta" \
  --plugin "${self_dir}/lib/libapollo_iree_hexagon_hal_plugin.so" "$@"
GUEST
chmod 0755 "${stage_dir}/run_tiny_cnn_hexagon_guest.sh"

"${venv_dir}/bin/python" - "${stage_dir}" "${runtime_version}" <<'PY'
from pathlib import Path
import json
import subprocess
import sys
stage = Path(sys.argv[1])
runtime_version = sys.argv[2]
runner = stage / 'bin' / 'iree-run-module'
try:
    runner_file = subprocess.check_output(['file', str(runner)], text=True).strip()
except Exception as exc:
    runner_file = repr(exc)
manifest = {
    'name': 'apollo-qbox-iree-tiny-cnn-guest-artifacts',
    'status': 'staged',
    'target': 'aarch64-unknown-linux-gnu llvm-cpu local-task',
    'guest_install_path': '/opt/qbox/iree/tiny-cnn',
    'expected_output': '1x1x2x2xf32=[[[54 63][90 99]]]',
    'runtime': {
        'source': 'PyPI iree-base-runtime manylinux aarch64 wheel',
        'version': runtime_version,
        'runner': 'bin/iree-run-module',
        'file': runner_file,
    },
    'hexagon_offload': {
        'runner': 'bin/apollo-iree-hexagon-runner',
        'plugin': 'lib/libapollo_iree_hexagon_hal_plugin.so',
        'upstream_executable_plugin_export': 'iree_hal_executable_plugin_query',
        'device': '/dev/apollo-hexagon',
        'script': 'run_tiny_cnn_hexagon_guest.sh',
        'metadata': 'apollo_hexagon.vmfb.meta',
        'queue': 'multi',
        'command_buffer': 'fixed',
        'fence': 'async-irq-poll',
        'dma_stress_bytes': 131072,
        'dma_stress_segments': 8,
    },
    'files': {str(p.relative_to(stage)): p.stat().st_size for p in sorted(stage.rglob('*')) if p.is_file()},
    'next_requirement': 'Run run_tiny_cnn_guest.sh for A710 CPU or run_tiny_cnn_hexagon_guest.sh for Apollo Hexagon offload in the QBox guest.',
}
(stage / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
print(json.dumps(manifest, indent=2))
PY

cat <<EOF
Staged IREE tiny-CNN guest artifacts: ${stage_dir}
To include them in the next Buildroot rootfs build, run:
  QBOX_IREE_GUEST_ARTIFACTS_DIR='${stage_dir}' ./scripts/build_qbox_buildroot_arm64.sh
EOF
