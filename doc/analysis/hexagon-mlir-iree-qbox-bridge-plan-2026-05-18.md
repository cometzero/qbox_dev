# Hexagon-MLIR to Apollo IREE/QBox Bridge Plan

Date: 2026-05-18
Workspace: `/build/qbox_dev`

## Conclusion

Direct `Hexagon-MLIR -> QBox Apollo Hexagon` execution is not feasible in the
current tree. Hexagon-MLIR currently exposes Triton/PyTorch compiler flows and
produces Hexagon-oriented lowering/object artifacts, while the QBox Apollo
Hexagon runtime path exposes fixed DRM accel jobs for CNN, vector-add, and DMA
stress. There is no generic Hexagon object/module loader ABI in the guest UAPI,
firmware job loop, or IREE HAL wrapper.

The feasible slice is:

1. Compile ONNX vector-add through the existing repo-local IREE host lane.
2. Run it in the guest through `iree-run-module --device=apollo-hexagon`.
3. Dispatch onto the existing Apollo VADD ioctl and firmware job.
4. Optionally stage a Hexagon-MLIR artifact as sidecar metadata so smoke logs
   can prove which compiler artifact was associated with the run.

MNIST is blocked until the repo has a model-specific or generic execution
contract: tensor buffers, submit ABI, firmware implementation, runner metadata,
and guest smoke markers.

## Evidence

- `sources/hexagon-mlir/README.md` describes Triton kernel and PyTorch model
  compilation/execution for Qualcomm Hexagon NPU targets.
- `sources/hexagon-mlir/docs/user-guide.md` requires Hexagon SDK 6.4.0.2,
  Hexagon Tools 19.0.02, HexKL, LLVM/Triton, Python 3.11, and real Hexagon NPU
  access for hardware tests.
- `configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_hexagon_uapi_guest.h`
  exposes `SUBMIT_CNN`, `SUBMIT_VADD`, and `DMA_STRESS`, not a generic object
  loader.
- `sources/qbox/platforms/buildroot/fw/hexagon_dma_smoke.s` implements fixed
  `vector_add_job`, CNN, and DMA copy jobs.
- `scripts/run_iree_vector_add_host_smoke.sh` already generates ONNX
  `vector_add_graph` and verifies `4xf32=11 22 33 44`.

## Implemented Bridge Slice

- `scripts/check_hexagon_mlir_iree_bridge.py` classifies direct connection,
  vadd feasibility, MNIST blockers, missing Hexagon-MLIR toolchain pieces, and
  the QBox fixed-job boundary.
- `apollo_iree_hexagon_hal.{h,c}` now accepts optional metadata:
  `compiler=hexagon-mlir` and `compiler_artifact=<relative-or-absolute-path>`.
- `apollo_iree_run_module.c` and `apollo_iree_hexagon_runner.c` print a
  `compiler bridge=... artifact=... bytes=...` runtime marker when sidecar
  metadata is present.
- `scripts/stage_iree_vector_add_guest_artifacts.sh` and
  `scripts/stage_iree_tiny_cnn_guest_artifacts.sh` accept
  `QBOX_HEXAGON_MLIR_ARTIFACT=/path/to/artifact` and stage it under
  `hexagon-mlir/`.

## Next Gates

1. Build Hexagon-MLIR by initializing its nested `triton` and `triton_shared`
   submodules and installing the required Qualcomm SDK/tools.
2. Generate a real vector-add Hexagon-MLIR artifact, then stage it with:

   ```bash
   QBOX_HEXAGON_MLIR_ARTIFACT=/path/to/vector_add.o \
     ./scripts/stage_iree_vector_add_guest_artifacts.sh
   ```

3. Add a generic QBox Apollo Hexagon object/module loader if the goal is to run
   Hexagon-MLIR object code directly instead of using the fixed VADD ioctl.
4. Add a MNIST-specific ABI or generic tensor execution ABI before claiming
   MNIST support.

## Verification Entry Points

```bash
python3 scripts/check_hexagon_mlir_iree_bridge.py \
  --repo . \
  --json build/verification/hexagon-mlir-iree-bridge-20260518.json

python3 scripts/check_hexagon_mlir_iree_bridge.py --repo . --require vadd
```
