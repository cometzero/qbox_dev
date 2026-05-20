#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
smoke_out=${QBOX_IREE_MNIST_SMOKE_OUT:-"${repo_root}/build/verification/iree-mnist-host"}
stage_dir=${QBOX_IREE_MNIST_GUEST_STAGE_DIR:-"${repo_root}/build/iree-guest-artifacts/mnist"}
venv_dir=${QBOX_IREE_SMOKE_VENV:-"${repo_root}/build/iree-smoke-venv"}
runtime_version=${QBOX_IREE_RUNTIME_VERSION:-3.11.0}
wheel_dir=${QBOX_IREE_AARCH64_WHEEL_DIR:-"${repo_root}/build/iree-aarch64-wheel"}
extract_dir=${QBOX_IREE_AARCH64_EXTRACT_DIR:-"${repo_root}/build/iree-aarch64-runtime-extract"}
hexagon_tools_dir=${QBOX_APOLLO_HEXAGON_TOOLS_OUT:-"${repo_root}/build/apollo-hexagon-guest-tools"}

if [[ "${QBOX_IREE_MNIST_SKIP_HOST_SMOKE:-0}" != 1 ]]; then
  "${repo_root}/scripts/run_iree_mnist_host_smoke.sh"
fi
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
  "${smoke_out}/mnist.onnx"
  "${smoke_out}/mnist.mlir"
  "${smoke_out}/mnist_cpu.vmfb"
  "${smoke_out}/mnist_aarch64.vmfb"
  "${smoke_out}/reference.json"
  "${smoke_out}/report.json"
)
for path in "${required[@]}"; do
  if [[ ! -s "${path}" ]]; then
    echo "missing generated IREE MNIST artifact: ${path}" >&2
    exit 1
  fi
done

rm -rf "${stage_dir}"
install -d "${stage_dir}/bin" "${stage_dir}/lib"
install -m 0755 "${runtime_bin}" "${stage_dir}/bin/iree-run-module.real"
install -m 0755 "${hexagon_tools_dir}/bin/apollo-iree-run-module" \
  "${stage_dir}/bin/apollo-iree-run-module"
install -m 0755 "${hexagon_tools_dir}/bin/apollo-iree-hexagon-runner" \
  "${stage_dir}/bin/apollo-iree-hexagon-runner"
install -m 0755 "${hexagon_tools_dir}/lib/libapollo_iree_hexagon_hal_plugin.so" \
  "${stage_dir}/lib/libapollo_iree_hexagon_hal_plugin.so"
install -m 0644 "${smoke_out}/mnist.onnx" "${stage_dir}/mnist.onnx"
install -m 0644 "${smoke_out}/mnist.mlir" "${stage_dir}/mnist.mlir"
install -m 0644 "${smoke_out}/mnist_aarch64.vmfb" "${stage_dir}/mnist_aarch64.vmfb"
install -m 0644 "${smoke_out}/reference.json" "${stage_dir}/reference.json"
install -m 0644 "${smoke_out}/report.json" "${stage_dir}/host-report.json"

"${venv_dir}/bin/python" - "${stage_dir}" <<'PY'
from pathlib import Path
import struct
import sys

stage = Path(sys.argv[1])
magic = 0x4F4B5041
header_bytes = 48
abi_version = 0
executable_format = 1
entry_kind = 3
input_bytes = 28 * 28 * 4
output_bytes = 10 * 4
reserved = [0, 0, 0, 0, 0]
code_words = [entry_kind]
payload = struct.pack("<4I", 0x5041594C, 0, entry_kind, 4)
code = struct.pack("<4I", 0x45444F43, 0, len(code_words), 4)
code += struct.pack(f"<{len(code_words)}I", *code_words)
apko = struct.pack(
    "<12I",
    magic, header_bytes, abi_version, executable_format, entry_kind,
    input_bytes, output_bytes, *reserved,
) + payload + code
(stage / "mnist.apko").write_bytes(apko)
module = (stage / "mnist_aarch64.vmfb").read_bytes()
footer = struct.pack(
    "<8I",
    0x4F4B4156,
    0,
    32,
    len(apko),
    entry_kind,
    input_bytes,
    output_bytes,
    0,
)
(stage / "mnist_apollo.vmfb").write_bytes(module + apko + footer)
PY

cat > "${stage_dir}/apollo_hexagon_apko.vmfb.meta" <<'META'
module=mnist_aarch64.vmfb
entry=mnist_graph
device=apollo-hexagon
expected=1x10xf32=[0 1 2 3 4 5 6 7 8 9]
plugin=lib/libapollo_iree_hexagon_hal_plugin.so
upstream_executable_plugin=iree_hal_executable_plugin_query
queue=multi
command_buffer=generic-submit
fence=async-irq-poll
executable_format=apollo-hexagon-apko-v0
apko=mnist.apko
apko_entry_kind=mnist
apko_input_bytes=3136
apko_output_bytes=40
host_onnx_compile=mnist-shaped-flatten-gemm
host_expected=1x10xf32=[0 1 2 3 4 5 6 7 8 9]
apollo_payload_semantics=mnist-flatten-gemm-zero-weights-bias-0-9
semantic_match=host-onnx-and-apollo-payload-produce-1x10xf32-bias-output
META

cat > "${stage_dir}/bin/iree-run-module" <<'GUEST'
#!/bin/sh
set -eu

self_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
stage_dir=$(CDPATH= cd -- "${self_dir}/.." && pwd)
real_runner="${self_dir}/iree-run-module.real"
apollo_runner="${self_dir}/apollo-iree-run-module"
is_apollo=0
has_query=0
has_metadata=0
prev=""

for arg in "$@"; do
  if [ "${prev}" = "--device" ]; then
    if [ "${arg}" = "apollo-hexagon" ] || [ "${arg}" = "apollo-hexagon://0" ]; then
      is_apollo=1
    fi
    prev=""
    continue
  fi
  case "${arg}" in
    --list_drivers|--dump_devices)
      has_query=1
      ;;
    --device=apollo-hexagon|--device=apollo-hexagon://0)
      is_apollo=1
      ;;
    --device)
      prev="--device"
      ;;
    --metadata|--metadata=*)
      has_metadata=1
      ;;
  esac
done

if [ "${is_apollo}" -eq 1 ] || [ "${has_query}" -eq 1 ]; then
  metadata_arg=""
  if [ "${has_metadata}" -eq 0 ] && [ -f "${stage_dir}/apollo_hexagon_apko.vmfb.meta" ]; then
    metadata_arg="--metadata=${stage_dir}/apollo_hexagon_apko.vmfb.meta"
  fi
  exec "${apollo_runner}" ${metadata_arg:+"${metadata_arg}"} "$@"
fi

exec "${real_runner}" "$@"
GUEST
chmod 0755 "${stage_dir}/bin/iree-run-module"

cat > "${stage_dir}/run_mnist_apko_hexagon_guest.sh" <<'GUEST'
#!/bin/sh
set -eu

self_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
runner=${IREE_RUN_MODULE:-"${self_dir}/bin/iree-run-module"}
if [ ! -x "${runner}" ]; then
  echo "iree-run-module Apollo registry wrapper is not installed in this Buildroot image." >&2
  exit 127
fi

exec "${runner}" \
  --device=apollo-hexagon \
  --metadata="${self_dir}/apollo_hexagon_apko.vmfb.meta" \
  --executable_plugin="${self_dir}/lib/libapollo_iree_hexagon_hal_plugin.so" \
  --module="${self_dir}/mnist_aarch64.vmfb" \
  --function=mnist_graph \
  --input='1x1x28x28xf32=0' \
  "$@"
GUEST
chmod 0755 "${stage_dir}/run_mnist_apko_hexagon_guest.sh"

cat > "${stage_dir}/run_mnist_vmfb_apko_hexagon_guest.sh" <<'GUEST'
#!/bin/sh
set -eu

self_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
runner=${IREE_RUN_MODULE:-"${self_dir}/bin/iree-run-module"}
if [ ! -x "${runner}" ]; then
  echo "iree-run-module Apollo registry wrapper is not installed in this Buildroot image." >&2
  exit 127
fi

exec "${runner}" \
  --device=apollo-hexagon \
  --metadata= \
  --executable_plugin="${self_dir}/lib/libapollo_iree_hexagon_hal_plugin.so" \
  --module="${self_dir}/mnist_apollo.vmfb" \
  --function=mnist_graph \
  --input='1x1x28x28xf32=0' \
  "$@"
GUEST
chmod 0755 "${stage_dir}/run_mnist_vmfb_apko_hexagon_guest.sh"

"${venv_dir}/bin/python" - "${stage_dir}" "${runtime_version}" <<'PY'
from pathlib import Path
import json
import subprocess
import sys

stage = Path(sys.argv[1])
runtime_version = sys.argv[2]
runner = stage / "bin" / "iree-run-module.real"
try:
    runner_file = subprocess.check_output(["file", str(runner)], text=True).strip()
except Exception as exc:
    runner_file = repr(exc)
manifest = {
    "name": "apollo-qbox-iree-mnist-guest-artifacts",
    "status": "staged",
    "target": "aarch64-unknown-linux-gnu llvm-cpu local-task base VMFB",
    "guest_install_path": "/opt/qbox/iree/mnist",
    "expected_output": "1x10xf32=[0 1 2 3 4 5 6 7 8 9]",
    "host_compile": {
        "source_model": "mnist.onnx",
        "mlir": "mnist.mlir",
        "aarch64_vmfb": "mnist_aarch64.vmfb",
        "report": "host-report.json",
        "expected_output": "1x10xf32=[0 1 2 3 4 5 6 7 8 9]",
        "semantic_scope": "MNIST-shaped ONNX compile smoke, not trained accuracy",
    },
    "runtime": {
        "source": "PyPI iree-base-runtime manylinux aarch64 wheel",
        "version": runtime_version,
        "runner": "bin/iree-run-module",
        "real_runner": "bin/iree-run-module.real",
        "file": runner_file,
    },
    "hexagon_offload": {
        "registry_frontend": "bin/apollo-iree-run-module",
        "driver_query": "bin/iree-run-module --list_drivers; bin/iree-run-module --dump_devices --device=apollo-hexagon://0 --executable_plugin=lib/libapollo_iree_hexagon_hal_plugin.so",
        "integration_status": "repo-local-registry-frontend",
        "upstream_hal_driver": "not-linked",
        "evidence_guard": "Do not report VMFB trailer APKO or wrapper dispatch evidence as upstream IREE HAL driver integration.",
        "runner": "bin/apollo-iree-hexagon-runner",
        "plugin": "lib/libapollo_iree_hexagon_hal_plugin.so",
        "device": "/dev/accel/accel0",
        "apko_script": "run_mnist_apko_hexagon_guest.sh",
        "embedded_apko_script": "run_mnist_vmfb_apko_hexagon_guest.sh",
        "metadata": "apollo_hexagon_apko.vmfb.meta",
        "apko": "mnist.apko",
        "embedded_apko_module": "mnist_apollo.vmfb",
        "entry_kind": "mnist",
        "input_bytes": 3136,
        "output_bytes": 40,
        "command_buffer": "generic-submit",
        "model_semantics": "MNIST-shaped Flatten+Gemm with zero weights and bias 0..9",
        "semantic_match": "host ONNX smoke and Apollo payload both produce 1x10xf32=[0 1 2 3 4 5 6 7 8 9] for zero input",
        "fence": "async-irq-poll",
    },
    "files": {str(p.relative_to(stage)): p.stat().st_size
              for p in sorted(stage.rglob("*")) if p.is_file()},
    "next_requirement": "Run run_mnist_apko_hexagon_guest.sh in the QBox guest.",
}
(stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                      encoding="utf-8")
print(json.dumps(manifest, indent=2))
PY

cat <<EOF
Staged IREE MNIST guest artifacts: ${stage_dir}
To include them in the next Buildroot rootfs build, run:
  QBOX_IREE_MNIST_GUEST_ARTIFACTS_DIR='${stage_dir}' ./scripts/build_qbox_buildroot_arm64.sh
EOF
