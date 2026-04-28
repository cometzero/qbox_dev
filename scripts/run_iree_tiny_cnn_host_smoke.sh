#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
venv_dir=${QBOX_IREE_SMOKE_VENV:-"${repo_root}/build/iree-smoke-venv"}
out_dir=${QBOX_IREE_SMOKE_OUT:-"${repo_root}/build/verification/iree-tiny-cnn-host"}
aarch64_vmfb=${QBOX_IREE_AARCH64_VMFB:-"${out_dir}/tiny_cnn_aarch64.vmfb"}
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

python - "${out_dir}" "${aarch64_vmfb}" <<'PY'
from pathlib import Path
import json
import numpy as np
import onnx
from onnx import TensorProto, helper, numpy_helper

out = Path(__import__('sys').argv[1])
out.mkdir(parents=True, exist_ok=True)

x_info = helper.make_tensor_value_info('input', TensorProto.FLOAT, [1, 1, 4, 4])
y_info = helper.make_tensor_value_info('output', TensorProto.FLOAT, [1, 1, 2, 2])
weights = numpy_helper.from_array(np.ones((1, 1, 3, 3), dtype=np.float32), name='conv_w')
bias = numpy_helper.from_array(np.array([0.0], dtype=np.float32), name='conv_b')
conv = helper.make_node('Conv', ['input', 'conv_w', 'conv_b'], ['conv_out'], kernel_shape=[3, 3], strides=[1, 1])
relu = helper.make_node('Relu', ['conv_out'], ['output'])
graph = helper.make_graph([conv, relu], 'tiny_cnn_graph', [x_info], [y_info], [weights, bias])
model = helper.make_model(graph, opset_imports=[helper.make_opsetid('', 17)], producer_name='qbox-dev-iree-smoke')
# Keep the IR version compatible with current IREE ONNX importer wheels.
model.ir_version = 10
onnx.checker.check_model(model)
onnx.save(model, out / 'tiny_cnn.onnx')
reference = {
    'input': list(range(1, 17)),
    'kernel': '1x1x3x3 all ones',
    'expected_output': [54.0, 63.0, 90.0, 99.0],
}
(out / 'reference.json').write_text(json.dumps(reference, indent=2) + '\n', encoding='utf-8')
print(out / 'tiny_cnn.onnx')
PY

iree-import-onnx \
  "${out_dir}/tiny_cnn.onnx" \
  --opset-version 17 \
  -o "${out_dir}/tiny_cnn.mlir" \
  2>&1 | tee "${out_dir}/import.log"

iree-compile \
  "${out_dir}/tiny_cnn.mlir" \
  --iree-hal-target-device=local \
  --iree-hal-local-target-device-backends=llvm-cpu \
  --iree-llvmcpu-target-cpu=host \
  --iree-opt-level=O2 \
  --iree-opt-data-tiling \
  -o "${out_dir}/tiny_cnn_cpu.vmfb" \
  2>&1 | tee "${out_dir}/compile.log"


iree-compile \
  "${out_dir}/tiny_cnn.mlir" \
  --iree-hal-target-device=local \
  --iree-hal-local-target-device-backends=llvm-cpu \
  --iree-llvmcpu-target-triple=aarch64-unknown-linux-gnu \
  --iree-llvmcpu-target-cpu=cortex-a710 \
  --iree-opt-level=O2 \
  --iree-opt-data-tiling \
  -o "${aarch64_vmfb}" \
  2>&1 | tee "${out_dir}/compile-aarch64.log"

iree-run-module \
  --module="${out_dir}/tiny_cnn_cpu.vmfb" \
  --device=local-task \
  --function=tiny_cnn_graph \
  --input='1x1x4x4xf32=[1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16]' \
  2>&1 | tee "${out_dir}/run.log"

grep -F '1x1x2x2xf32=[[[54 63][90 99]]]' "${out_dir}/run.log" >/dev/null

python - "${out_dir}" "${aarch64_vmfb}" <<'PY'
from pathlib import Path
import json
import subprocess
import sys

out = Path(sys.argv[1])
aarch64_vmfb = Path(sys.argv[2])
versions = {}
commands = {
    'python-modules': ['python', '-c', 'import iree.compiler, iree.runtime, onnx, numpy; print("python modules ok")'],
    'iree-compile': ['iree-compile', '--version'],
    'pip-packages': ['python', '-m', 'pip', 'show', 'iree-base-compiler', 'iree-base-runtime', 'onnx', 'numpy'],
}
for name, cmd in commands.items():
    try:
        proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        versions[name] = proc.stdout.strip().splitlines()[:40]
    except Exception as exc:
        versions[name] = [repr(exc)]
report = {
    'status': 'pass',
    'pipeline': ['onnx', 'mlir', 'iree-compile llvm-cpu/local host', 'iree-compile llvm-cpu/local aarch64', 'iree-run-module local-task host'],
    'artifacts': {
        'onnx': str(out / 'tiny_cnn.onnx'),
        'mlir': str(out / 'tiny_cnn.mlir'),
        'host_vmfb': str(out / 'tiny_cnn_cpu.vmfb'),
        'aarch64_vmfb': str(aarch64_vmfb),
        'run_log': str(out / 'run.log'),
        'reference': str(out / 'reference.json'),
    },
    'expected_output': '1x1x2x2xf32=[[[54 63][90 99]]]',
    'versions': versions,
}
(out / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, indent=2))
PY
