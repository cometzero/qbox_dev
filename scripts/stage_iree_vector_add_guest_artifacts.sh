#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
smoke_out=${QBOX_IREE_VECTOR_ADD_SMOKE_OUT:-"${repo_root}/build/verification/iree-vector-add-host"}
stage_dir=${QBOX_IREE_VECTOR_ADD_GUEST_STAGE_DIR:-"${repo_root}/build/iree-guest-artifacts/vector-add"}
venv_dir=${QBOX_IREE_SMOKE_VENV:-"${repo_root}/build/iree-smoke-venv"}
runtime_version=${QBOX_IREE_RUNTIME_VERSION:-3.11.0}
wheel_dir=${QBOX_IREE_AARCH64_WHEEL_DIR:-"${repo_root}/build/iree-aarch64-wheel"}
extract_dir=${QBOX_IREE_AARCH64_EXTRACT_DIR:-"${repo_root}/build/iree-aarch64-runtime-extract"}
hexagon_tools_dir=${QBOX_APOLLO_HEXAGON_TOOLS_OUT:-"${repo_root}/build/apollo-hexagon-guest-tools"}
hexagon_mlir_artifact=${QBOX_HEXAGON_MLIR_ARTIFACT:-}

if [[ "${QBOX_IREE_VECTOR_ADD_SKIP_HOST_SMOKE:-0}" != 1 ]]; then
  "${repo_root}/scripts/run_iree_vector_add_host_smoke.sh"
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
  "${smoke_out}/vector_add.onnx"
  "${smoke_out}/vector_add.mlir"
  "${smoke_out}/vector_add_cpu.vmfb"
  "${smoke_out}/vector_add_aarch64.vmfb"
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
install -m 0755 "${runtime_bin}" "${stage_dir}/bin/iree-run-module.real"
install -m 0755 "${hexagon_tools_dir}/bin/apollo-iree-run-module" \
  "${stage_dir}/bin/apollo-iree-run-module"
install -m 0755 "${hexagon_tools_dir}/bin/apollo-iree-hexagon-runner" \
  "${stage_dir}/bin/apollo-iree-hexagon-runner"
install -m 0755 "${hexagon_tools_dir}/bin/apollo-hexagon-apko-negative" \
  "${stage_dir}/bin/apollo-hexagon-apko-negative"
install -m 0755 "${hexagon_tools_dir}/lib/libapollo_iree_hexagon_hal_plugin.so" \
  "${stage_dir}/lib/libapollo_iree_hexagon_hal_plugin.so"
install -m 0644 "${smoke_out}/vector_add.onnx" "${stage_dir}/vector_add.onnx"
install -m 0644 "${smoke_out}/vector_add.mlir" "${stage_dir}/vector_add.mlir"
install -m 0644 "${smoke_out}/vector_add_aarch64.vmfb" "${stage_dir}/vector_add_aarch64.vmfb"
install -m 0644 "${smoke_out}/reference.json" "${stage_dir}/reference.json"
install -m 0644 "${smoke_out}/report.json" "${stage_dir}/host-report.json"
hexagon_mlir_rel=
if [[ -n "${hexagon_mlir_artifact}" ]]; then
  if [[ ! -s "${hexagon_mlir_artifact}" ]]; then
    echo "QBOX_HEXAGON_MLIR_ARTIFACT is missing or empty: ${hexagon_mlir_artifact}" >&2
    exit 1
  fi
  install -d "${stage_dir}/hexagon-mlir"
  hexagon_mlir_name=$(basename "${hexagon_mlir_artifact}")
  install -m 0644 "${hexagon_mlir_artifact}" \
    "${stage_dir}/hexagon-mlir/${hexagon_mlir_name}"
  hexagon_mlir_rel="hexagon-mlir/${hexagon_mlir_name}"
fi
cat > "${stage_dir}/apollo_hexagon.vmfb.meta" <<'META'
module=vector_add_aarch64.vmfb
entry=vector_add_graph
device=apollo-hexagon
expected=4xf32=11 22 33 44
plugin=lib/libapollo_iree_hexagon_hal_plugin.so
upstream_executable_plugin=iree_hal_executable_plugin_query
queue=multi
command_buffer=fixed
fence=async-irq-poll
META
if [[ -n "${hexagon_mlir_rel}" ]]; then
  {
    echo "compiler=hexagon-mlir"
    echo "compiler_model=vector-add"
    echo "compiler_artifact=${hexagon_mlir_rel}"
  } >> "${stage_dir}/apollo_hexagon.vmfb.meta"
fi

"${venv_dir}/bin/python" - "${stage_dir}" <<'PY'
from pathlib import Path
import struct
import sys

stage = Path(sys.argv[1])
path = stage / "vector_add.apko"
magic = 0x4F4B5041
header_bytes = 48
abi_version = 0
executable_format = 1
entry_kind = 2
input_bytes = 32
output_bytes = 16
reserved = [0, 0, 0, 0, 0]
payload = struct.pack("<4I", 0x5041594C, 0, entry_kind, 4)
apko = struct.pack(
    "<12I",
    magic, header_bytes, abi_version, executable_format, entry_kind,
    input_bytes, output_bytes, *reserved,
) + payload
path.write_bytes(apko)

module = (stage / "vector_add_aarch64.vmfb").read_bytes()
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
(stage / "vector_add_apollo.vmfb").write_bytes(module + apko + footer)
PY

cat > "${stage_dir}/apollo_hexagon_apko.vmfb.meta" <<'META'
module=vector_add_aarch64.vmfb
entry=vector_add_graph
device=apollo-hexagon
expected=4xf32=11 22 33 44
plugin=lib/libapollo_iree_hexagon_hal_plugin.so
upstream_executable_plugin=iree_hal_executable_plugin_query
queue=multi
command_buffer=generic-submit
fence=async-irq-poll
executable_format=apollo-hexagon-apko-v0
apko=vector_add.apko
apko_entry_kind=vadd
apko_input_bytes=32
apko_output_bytes=16
META
if [[ -n "${hexagon_mlir_rel}" ]]; then
  {
    echo "compiler=hexagon-mlir"
    echo "compiler_model=vector-add"
    echo "compiler_artifact=${hexagon_mlir_rel}"
  } >> "${stage_dir}/apollo_hexagon_apko.vmfb.meta"
fi

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
  if [ "${has_metadata}" -eq 0 ] && [ -f "${stage_dir}/apollo_hexagon.vmfb.meta" ]; then
    metadata_arg="--metadata=${stage_dir}/apollo_hexagon.vmfb.meta"
  fi
  exec "${apollo_runner}" ${metadata_arg:+"${metadata_arg}"} "$@"
fi

exec "${real_runner}" "$@"
GUEST
chmod 0755 "${stage_dir}/bin/iree-run-module"

cat > "${stage_dir}/run_vector_add_guest.sh" <<'GUEST'
#!/bin/sh
set -eu

self_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
module=${1:-"${self_dir}/vector_add_aarch64.vmfb"}
runner=${IREE_RUN_MODULE:-"${self_dir}/bin/iree-run-module"}
if [ ! -x "${runner}" ]; then
  runner=$(command -v iree-run-module || true)
fi
if [ -z "${runner}" ] || [ ! -x "${runner}" ]; then
  echo "iree-run-module is not installed in this Buildroot image." >&2
  exit 127
fi

exec "${runner}" \
  --executable_plugin="${self_dir}/lib/libapollo_iree_hexagon_hal_plugin.so" \
  --module="${module}" \
  --device=local-task \
  --function=vector_add_graph \
  --input='4xf32=[1 2 3 4]' \
  --input='4xf32=[10 20 30 40]'
GUEST
chmod 0755 "${stage_dir}/run_vector_add_guest.sh"

cat > "${stage_dir}/run_vector_add_hexagon_guest.sh" <<'GUEST'
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
  --metadata="${self_dir}/apollo_hexagon.vmfb.meta" \
  --executable_plugin="${self_dir}/lib/libapollo_iree_hexagon_hal_plugin.so" \
  --module="${self_dir}/vector_add_aarch64.vmfb" \
  --function=vector_add_graph \
  --input='4xf32=[1 2 3 4]' \
  --input='4xf32=[10 20 30 40]' \
  "$@"
GUEST
chmod 0755 "${stage_dir}/run_vector_add_hexagon_guest.sh"

cat > "${stage_dir}/run_vector_add_apko_hexagon_guest.sh" <<'GUEST'
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
  --module="${self_dir}/vector_add_aarch64.vmfb" \
  --function=vector_add_graph \
  --input='4xf32=[1 2 3 4]' \
  --input='4xf32=[10 20 30 40]' \
  "$@"
GUEST
chmod 0755 "${stage_dir}/run_vector_add_apko_hexagon_guest.sh"

cat > "${stage_dir}/run_vector_add_vmfb_apko_hexagon_guest.sh" <<'GUEST'
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
  --module="${self_dir}/vector_add_apollo.vmfb" \
  --function=vector_add_graph \
  --input='4xf32=[1 2 3 4]' \
  --input='4xf32=[10 20 30 40]' \
  "$@"
GUEST
chmod 0755 "${stage_dir}/run_vector_add_vmfb_apko_hexagon_guest.sh"

cat > "${stage_dir}/run_apko_negative_hexagon_guest.sh" <<'GUEST'
#!/bin/sh
set -eu

self_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
runner="${self_dir}/bin/apollo-hexagon-apko-negative"
if [ ! -x "${runner}" ]; then
  echo "apollo-hexagon-apko-negative is not installed in this Buildroot image." >&2
  exit 127
fi

exec "${runner}" "$@"
GUEST
chmod 0755 "${stage_dir}/run_apko_negative_hexagon_guest.sh"

"${venv_dir}/bin/python" - "${stage_dir}" "${runtime_version}" "${hexagon_mlir_rel}" <<'PY'
from pathlib import Path
import json
import subprocess
import sys
stage = Path(sys.argv[1])
runtime_version = sys.argv[2]
hexagon_mlir_rel = sys.argv[3]
runner = stage / "bin" / "iree-run-module.real"
try:
    runner_file = subprocess.check_output(["file", str(runner)], text=True).strip()
except Exception as exc:
    runner_file = repr(exc)
manifest = {
    "name": "apollo-qbox-iree-vector-add-guest-artifacts",
    "status": "staged",
    "target": "aarch64-unknown-linux-gnu llvm-cpu local-task",
    "guest_install_path": "/opt/qbox/iree/vector-add",
    "expected_output": "4xf32=11 22 33 44",
    "runtime": {
        "source": "PyPI iree-base-runtime manylinux aarch64 wheel",
        "version": runtime_version,
        "runner": "bin/iree-run-module",
        "real_runner": "bin/iree-run-module.real",
        "file": runner_file,
    },
    "hexagon_offload": {
        "registry_frontend": "bin/apollo-iree-run-module",
        "iree_run_module_dispatch": "bin/iree-run-module --device=apollo-hexagon",
        "driver_query": "bin/iree-run-module --list_drivers; bin/iree-run-module --dump_devices --device=apollo-hexagon://0 --executable_plugin=lib/libapollo_iree_hexagon_hal_plugin.so",
        "integration_status": "repo-local-registry-frontend",
        "upstream_hal_driver": "not-linked",
        "evidence_guard": "Do not report VMFB trailer APKO or wrapper dispatch evidence as upstream IREE HAL driver integration.",
        "runner": "bin/apollo-iree-hexagon-runner",
        "plugin": "lib/libapollo_iree_hexagon_hal_plugin.so",
        "upstream_executable_plugin_export": "iree_hal_executable_plugin_query",
        "device": "/dev/accel/accel0",
        "script": "run_vector_add_hexagon_guest.sh",
        "apko_script": "run_vector_add_apko_hexagon_guest.sh",
        "embedded_apko_script": "run_vector_add_vmfb_apko_hexagon_guest.sh",
        "negative_script": "run_apko_negative_hexagon_guest.sh",
        "metadata": "apollo_hexagon.vmfb.meta",
        "apko_metadata": "apollo_hexagon_apko.vmfb.meta",
        "apko": "vector_add.apko",
        "embedded_apko_module": "vector_add_apollo.vmfb",
        "queue": "multi",
        "command_buffer": "fixed",
        "generic_command_buffer": "generic-submit",
        "embedded_apko_contract": "VMFB file carries a repo-local APKO trailer and runs without .vmfb.meta sidecar metadata",
        "fence": "async-irq-poll",
    },
    "hexagon_mlir_bridge": {
        "status": "metadata_sidecar_staged" if hexagon_mlir_rel else "not_requested",
        "model": "vector-add",
        "artifact": hexagon_mlir_rel,
        "execution_contract": "metadata-only sidecar; APKO metadata uses the generic submit ioctl while fixed VADD remains a compatibility path",
    },
    "files": {str(p.relative_to(stage)): p.stat().st_size
              for p in sorted(stage.rglob("*")) if p.is_file()},
    "next_requirement": "Run run_vector_add_hexagon_guest.sh in the QBox guest.",
}
(stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                      encoding="utf-8")
print(json.dumps(manifest, indent=2))
PY

cat <<EOF
Staged IREE vector-add guest artifacts: ${stage_dir}
To include them in the next Buildroot rootfs build, run:
  QBOX_IREE_VECTOR_ADD_GUEST_ARTIFACTS_DIR='${stage_dir}' ./scripts/build_qbox_buildroot_arm64.sh
EOF
