#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
venv_dir=${QBOX_IREE_SMOKE_VENV:-"${repo_root}/build/iree-smoke-venv"}
out_dir=${QBOX_IREE_VECTOR_ADD_SMOKE_OUT:-"${repo_root}/build/verification/iree-vector-add-host"}
aarch64_vmfb=${QBOX_IREE_VECTOR_ADD_AARCH64_VMFB:-"${out_dir}/vector_add_aarch64.vmfb"}
no_install=${QBOX_IREE_SMOKE_NO_INSTALL:-0}

mkdir -p "${out_dir}"

if [[ ! -x "${venv_dir}/bin/python" ]]; then
  python3 -m venv "${venv_dir}"
fi

# shellcheck source=/dev/null
source "${venv_dir}/bin/activate"

need_install=0
for tool in iree-import-onnx iree-compile iree-run-module; do
  if ! command -v "${tool}" >/dev/null 2>&1; then
    need_install=1
  fi
done
python - <<'PY' >/dev/null 2>&1 || need_install=1
import onnx
import numpy
PY

if [[ "${need_install}" == "1" ]]; then
  if [[ "${no_install}" == "1" ]]; then
    echo "IREE/ONNX tools are missing and QBOX_IREE_SMOKE_NO_INSTALL=1" >&2
    exit 2
  fi
  python -m pip install --upgrade pip | tee "${out_dir}/pip-upgrade.log"
  python -m pip install 'iree-base-compiler[onnx]' iree-base-runtime onnx numpy \
    | tee "${out_dir}/pip-install.log"
fi

python - "${out_dir}" <<'PY'
from pathlib import Path
import json
import onnx
from onnx import TensorProto, helper

out = Path(__import__("sys").argv[1])
out.mkdir(parents=True, exist_ok=True)

lhs_info = helper.make_tensor_value_info("lhs", TensorProto.FLOAT, [4])
rhs_info = helper.make_tensor_value_info("rhs", TensorProto.FLOAT, [4])
out_info = helper.make_tensor_value_info("output", TensorProto.FLOAT, [4])
add = helper.make_node("Add", ["lhs", "rhs"], ["output"])
graph = helper.make_graph([add], "vector_add_graph", [lhs_info, rhs_info], [out_info])
model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)],
                          producer_name="qbox-dev-iree-vector-add")
model.ir_version = 10
onnx.checker.check_model(model)
onnx.save(model, out / "vector_add.onnx")
reference = {
    "lhs": [1.0, 2.0, 3.0, 4.0],
    "rhs": [10.0, 20.0, 30.0, 40.0],
    "expected_output": [11.0, 22.0, 33.0, 44.0],
}
(out / "reference.json").write_text(json.dumps(reference, indent=2) + "\n",
                                     encoding="utf-8")
print(out / "vector_add.onnx")
PY

iree-import-onnx \
  "${out_dir}/vector_add.onnx" \
  --opset-version 17 \
  -o "${out_dir}/vector_add.mlir" \
  2>&1 | tee "${out_dir}/import.log"

iree-compile \
  "${out_dir}/vector_add.mlir" \
  --iree-hal-target-device=local \
  --iree-hal-local-target-device-backends=llvm-cpu \
  --iree-llvmcpu-target-cpu=host \
  --iree-opt-level=O2 \
  --iree-opt-data-tiling \
  -o "${out_dir}/vector_add_cpu.vmfb" \
  2>&1 | tee "${out_dir}/compile.log"

iree-compile \
  "${out_dir}/vector_add.mlir" \
  --iree-hal-target-device=local \
  --iree-hal-local-target-device-backends=llvm-cpu \
  --iree-llvmcpu-target-triple=aarch64-unknown-linux-gnu \
  --iree-llvmcpu-target-cpu=cortex-a710 \
  --iree-opt-level=O2 \
  --iree-opt-data-tiling \
  -o "${aarch64_vmfb}" \
  2>&1 | tee "${out_dir}/compile-aarch64.log"

iree-run-module \
  --module="${out_dir}/vector_add_cpu.vmfb" \
  --device=local-task \
  --function=vector_add_graph \
  --input='4xf32=[1 2 3 4]' \
  --input='4xf32=[10 20 30 40]' \
  2>&1 | tee "${out_dir}/run.log"

grep -F '4xf32=11 22 33 44' "${out_dir}/run.log" >/dev/null

python - "${out_dir}" "${aarch64_vmfb}" <<'PY'
from pathlib import Path
import json
import subprocess
import sys

out = Path(sys.argv[1])
aarch64_vmfb = Path(sys.argv[2])
versions = {}
commands = {
    "python-modules": ["python", "-c",
                       "import iree.compiler, iree.runtime, onnx, numpy; print('python modules ok')"],
    "iree-compile": ["iree-compile", "--version"],
    "pip-packages": ["python", "-m", "pip", "show",
                     "iree-base-compiler", "iree-base-runtime", "onnx", "numpy"],
}
for name, cmd in commands.items():
    try:
        proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, check=False)
        versions[name] = proc.stdout.strip().splitlines()[:40]
    except Exception as exc:
        versions[name] = [repr(exc)]
report = {
    "status": "pass",
    "pipeline": [
        "onnx",
        "mlir",
        "iree-compile llvm-cpu/local host",
        "iree-compile llvm-cpu/local aarch64",
        "iree-run-module local-task host",
    ],
    "artifacts": {
        "onnx": str(out / "vector_add.onnx"),
        "mlir": str(out / "vector_add.mlir"),
        "host_vmfb": str(out / "vector_add_cpu.vmfb"),
        "aarch64_vmfb": str(aarch64_vmfb),
        "run_log": str(out / "run.log"),
        "reference": str(out / "reference.json"),
    },
    "expected_output": "4xf32=11 22 33 44",
    "versions": versions,
}
(out / "report.json").write_text(json.dumps(report, indent=2) + "\n",
                                  encoding="utf-8")
print(json.dumps(report, indent=2))
PY
