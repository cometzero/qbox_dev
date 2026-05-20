#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
venv_dir=${QBOX_IREE_SMOKE_VENV:-"${repo_root}/build/iree-smoke-venv"}
out_dir=${QBOX_IREE_MNIST_SMOKE_OUT:-"${repo_root}/build/verification/iree-mnist-host"}
aarch64_vmfb=${QBOX_IREE_MNIST_AARCH64_VMFB:-"${out_dir}/mnist_aarch64.vmfb"}
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
import numpy as np
import onnx
from onnx import TensorProto, helper, numpy_helper
import sys

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)

x_info = helper.make_tensor_value_info("input", TensorProto.FLOAT, [1, 1, 28, 28])
y_info = helper.make_tensor_value_info("output", TensorProto.FLOAT, [1, 10])
weights = numpy_helper.from_array(np.zeros((784, 10), dtype=np.float32), name="fc_w")
bias = numpy_helper.from_array(np.arange(10, dtype=np.float32), name="fc_b")
flatten = helper.make_node("Flatten", ["input"], ["flat"], axis=1)
gemm = helper.make_node("Gemm", ["flat", "fc_w", "fc_b"], ["output"])
graph = helper.make_graph(
    [flatten, gemm],
    "mnist_graph",
    [x_info],
    [y_info],
    [weights, bias],
)
model = helper.make_model(
    graph,
    opset_imports=[helper.make_opsetid("", 17)],
    producer_name="qbox-dev-iree-mnist",
)
model.ir_version = 10
onnx.checker.check_model(model)
onnx.save(model, out / "mnist.onnx")
reference = {
    "input": "1x1x28x28 zeros",
    "model": "MNIST-shaped Flatten+Gemm classifier smoke with fixed bias",
    "expected_output": [float(i) for i in range(10)],
}
(out / "reference.json").write_text(json.dumps(reference, indent=2) + "\n",
                                     encoding="utf-8")
print(out / "mnist.onnx")
PY

iree-import-onnx \
  "${out_dir}/mnist.onnx" \
  --opset-version 17 \
  -o "${out_dir}/mnist.mlir" \
  2>&1 | tee "${out_dir}/import.log"

iree-compile \
  "${out_dir}/mnist.mlir" \
  --iree-hal-target-device=local \
  --iree-hal-local-target-device-backends=llvm-cpu \
  --iree-llvmcpu-target-cpu=host \
  --iree-opt-level=O2 \
  --iree-opt-data-tiling \
  -o "${out_dir}/mnist_cpu.vmfb" \
  2>&1 | tee "${out_dir}/compile.log"

iree-compile \
  "${out_dir}/mnist.mlir" \
  --iree-hal-target-device=local \
  --iree-hal-local-target-device-backends=llvm-cpu \
  --iree-llvmcpu-target-triple=aarch64-unknown-linux-gnu \
  --iree-llvmcpu-target-cpu=cortex-a710 \
  --iree-opt-level=O2 \
  --iree-opt-data-tiling \
  -o "${aarch64_vmfb}" \
  2>&1 | tee "${out_dir}/compile-aarch64.log"

iree-run-module \
  --module="${out_dir}/mnist_cpu.vmfb" \
  --device=local-task \
  --function=mnist_graph \
  --input='1x1x28x28xf32=0' \
  2>&1 | tee "${out_dir}/run.log"

grep -F '1x10xf32=[0 1 2 3 4 5 6 7 8 9]' "${out_dir}/run.log" >/dev/null

python - "${out_dir}" "${aarch64_vmfb}" <<'PY'
from pathlib import Path
import json
import subprocess
import sys

out = Path(sys.argv[1])
aarch64_vmfb = Path(sys.argv[2])
versions = {}
commands = {
    "python-modules": [
        "python",
        "-c",
        "import iree.compiler, iree.runtime, onnx, numpy; print('python modules ok')",
    ],
    "iree-compile": ["iree-compile", "--version"],
    "pip-packages": [
        "python",
        "-m",
        "pip",
        "show",
        "iree-base-compiler",
        "iree-base-runtime",
        "onnx",
        "numpy",
    ],
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
        "onnx": str(out / "mnist.onnx"),
        "mlir": str(out / "mnist.mlir"),
        "host_vmfb": str(out / "mnist_cpu.vmfb"),
        "aarch64_vmfb": str(aarch64_vmfb),
        "run_log": str(out / "run.log"),
        "reference": str(out / "reference.json"),
    },
    "expected_output": "1x10xf32=[0 1 2 3 4 5 6 7 8 9]",
    "semantic_scope": (
        "MNIST-shaped ONNX compile smoke; not a trained MNIST accuracy test "
        "and not proof that Apollo executes ONNX semantics yet"
    ),
    "versions": versions,
}
(out / "report.json").write_text(json.dumps(report, indent=2) + "\n",
                                  encoding="utf-8")
print(json.dumps(report, indent=2))
PY
