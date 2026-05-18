# Hexagon-MLIR Target Execution Analysis

Date: 2026-05-18
Workspace: `/build/qbox_dev`

## Target Runtime Model

`sources/hexagon-mlir` does not execute generated code by loading a Hexagon
object into the current QBox firmware loop. Its upstream runtime path builds a
Hexagon shared object and then runs it through Qualcomm SDK launchers.

There are two supported upstream execution modes:

1. Android device mode
   - `RUN_ON_SIM=0`
   - `adb` pushes inputs, generated `.so` files, `run_main_on_hexagon`, the
     `librun_main_on_hexagon_skel.so` library, and Hexagon `libc++.so.1` to
     `/data/local/tmp/<kernel-run-id>`.
   - The target command runs `./run_main_on_hexagon 3 <principal-lib.so>` with
     `ADSP_LIBRARY_PATH=<run-dir>/lib;/vendor/lib/rfsa/adsp/`.
   - Required target variables are `ANDROID_SERIAL` and optionally
     `ANDROID_HOST`.

2. QuRT simulator mode
   - `RUN_ON_SIM=1`
   - The executor writes simulator config files for `qurt_model.so`,
     `qtimer.so`, and `l2vic.so`.
   - It launches `hexagon-sim` with SDK `runelf.pbn` and
     `run_main_on_hexagon_sim`.

Both modes require the Hexagon SDK, Hexagon Tools, built Hexagon-MLIR/Triton
tools, and runtime libraries such as `libqhmath_hvx.a`.

## QBox Compatibility

The current QBox Apollo Hexagon target is not the same runtime contract. It is
a Buildroot Linux guest plus a QBox Hexagon firmware loop exposing fixed DRM
accel jobs:

- `SUBMIT_CNN`
- `SUBMIT_VADD`
- `DMA_STRESS`

There is no Qualcomm Android RFSA/ADSP filesystem, no `run_main_on_hexagon`
service, and no generic Apollo object/module loader ABI. Therefore direct
Hexagon-MLIR object execution on QBox is blocked until a new loader ABI and
firmware/runtime loader exist.

The currently implemented QBox-compatible slice is an adapter:

- Use existing IREE ONNX vector-add artifacts.
- Execute through `iree-run-module --device=apollo-hexagon`.
- Dispatch the fixed Apollo VADD ioctl.
- Optionally attach a Hexagon-MLIR artifact with
  `QBOX_HEXAGON_MLIR_ARTIFACT=/path/to/artifact` as sidecar metadata.

## Implemented Entry Points

- `scripts/check_hexagon_mlir_target_execution.py`
  - Reports source, compiler, link, Android device, simulator, and QBox
    readiness.
  - Writes machine-readable JSON for dated evidence.
  - Supports `--require device`, `--require simulator`, and `--require qbox`.

- `scripts/run_hexagon_mlir_target_vec_add.sh`
  - Runs preflight by default and writes a JSON report.
  - With all prerequisites available, runs upstream
    `pytest -sv test/python/triton/test_vec_add.py` under either
    `--mode device` or `--mode simulator`.

## Commands

Preflight only:

```bash
./scripts/run_hexagon_mlir_target_vec_add.sh --mode simulator --preflight-only
```

Require simulator readiness and run:

```bash
./scripts/run_hexagon_mlir_target_vec_add.sh --mode simulator
```

Require Android device readiness and run:

```bash
export ANDROID_SERIAL=<serial>
./scripts/run_hexagon_mlir_target_vec_add.sh --mode device
```

QBox adapter path:

```bash
QBOX_HEXAGON_MLIR_ARTIFACT=/path/to/hexagon-mlir/artifact \
  ./scripts/stage_iree_vector_add_guest_artifacts.sh

QBOX_IREE_VECTOR_ADD_GUEST_ARTIFACTS_DIR=build/iree-guest-artifacts/vector-add \
  ./scripts/build_qbox_buildroot_arm64.sh

./scripts/stage_buildroot_artifacts.sh
QBOX_BOOT_TIMEOUT=70 ./scripts/run_iree_vector_add_hexagon_qbox_guest_smoke.sh
```

## Current Blockers

- `triton` and `triton_shared` nested submodules under `sources/hexagon-mlir`
  are not initialized in this checkout.
- `HEXAGON_SDK_ROOT`, `HEXAGON_TOOLS`, `HEXKL_ROOT`,
  `LLVM_PROJECT_BUILD_DIR`, and `CONDA_ENV` are not set to valid directories in
  the current shell.
- Built `linalg-hexagon-opt`, `linalg-hexagon-translate`, and
  `triton-shared-opt` are not available.
- No Android device serial is configured.
- QBox lacks the generic object loader needed for direct Hexagon-MLIR object
  execution.
