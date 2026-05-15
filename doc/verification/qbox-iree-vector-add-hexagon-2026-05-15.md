# QBox IREE Hexagon vector-add verification

- Date: 2026-05-15
- Target: `/build/qbox_dev`
- Scope: run an ONNX vector-add model through IREE and the repo-local Apollo
  Hexagon HAL path in the QBox Buildroot guest, with SMMUv3-translated DMA.
- Result: PASS for the repo-local integration slice.

## Implemented path

- `scripts/run_iree_vector_add_host_smoke.sh` creates a minimal ONNX
  `vector_add_graph`, imports it to MLIR, compiles host and AArch64 VMFBs with
  IREE, and verifies the host output.
- `scripts/stage_iree_vector_add_guest_artifacts.sh` stages the AArch64 VMFB,
  IREE runtime wrapper, Apollo Hexagon HAL runner, and dynamic HAL plugin under
  `build/iree-guest-artifacts/vector-add`.
- `configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/post-build.sh`
  can install those staged artifacts into `/opt/qbox/iree/vector-add`.
- The Apollo Hexagon UAPI, Linux driver, guest HAL/plugin, registry frontend,
  and firmware now expose a vector-add job beside the existing tiny-CNN and SG
  DMA stress paths.
- The Hexagon firmware consumes two `4xf32` input vectors through
  SMMUv3-translated DMA and returns `4xf32=11 22 33 44`.

## SMMUv3 probe fixes

The first QBox guest smoke boots reached `/sbin/init` but did not create
`/dev/apollo-hexagon` because the Linux probe expected stale SMMUv3 discovery
register values.  The fix keeps the Linux probe aligned with the current QBox
TBU register surface:

- `APOLLO_SMMUV3_AIDR` is `0x01c`, matching the architected AIDR slot.
- `APOLLO_SMMUV3_ARCH_IDR3` is `0x00007794`, matching the TBU's `IDR3`
  discovery value including `E0PD`.
- `scripts/check_buildroot_arm64_lane.sh` and
  `scripts/check_qbox_smmuv3_compliance.py` now check these values.

## Runtime evidence

| Check | Evidence | Result |
| --- | --- | --- |
| Host ONNX -> MLIR -> IREE compile/run | `build/verification/iree-vector-add-host/report.json` | PASS: expected `4xf32=11 22 33 44` |
| Guest artifact staging | `build/iree-guest-artifacts/vector-add/manifest.json` | PASS: staged AArch64 runtime, VMFB, runner, plugin, scripts |
| Firmware build | `build/verification/hexagon-vector-add-firmware-20260515-203035.log` | PASS: `apollo_hexagon_dma.bin` rebuilt |
| Linux build after SMMUv3 probe fixes | `build/verification/iree-vector-add-linux-idr3-fix-20260515-203855.log` | PASS: `drivers/soc/apollo/apollo-hexagon-test.o` rebuilt |
| Artifact staging after SMMUv3 probe fixes | `build/verification/iree-vector-add-stage-idr3-fix-20260515-203923.log` | PASS: Linux, Buildroot, and Hexagon artifacts staged |
| QBox guest Hexagon vector-add smoke | `build/verification/qbox-iree-vector-add-hexagon-guest-20260515-203926.log` | PASS: script exited 0 and output matched |

Key runtime markers from
`build/verification/qbox-iree-vector-add-hexagon-guest-20260515-203926.log`:

- `/dev/apollo-hexagon` registered:
  `userspace submit ABI ready at /dev/apollo-hexagon stream-id=0x1 primary=1`
- SMMUv3 path initialized:
  `SMMUv3 page-table walker/ATS/PRI/fault queue ready`
- IREE uses the Apollo Hexagon registry/plugin path:
  `dynamically registered C HAL plugin=/opt/qbox/iree/vector-add/lib/libapollo_iree_hexagon_hal_plugin.so`
- Vector-add input and output use SMMUv3-translated DMA:
  `APOLLO_HEXAGON_DMA: path=smmu-translated stream-id=0x1`
- Accelerator completion:
  `accelerator vector add ok queue=1 fence=2 status=0x56414444 out=41300000,41b00000,42040000,42300000`
- IREE output:
  `EXEC @vector_add_graph [apollo-hexagon]`
  `4xf32=11 22 33 44`

## Validation commands

| Command | Result |
| --- | --- |
| `./scripts/run_iree_vector_add_host_smoke.sh` | PASS |
| `./scripts/stage_iree_vector_add_guest_artifacts.sh` | PASS |
| `./scripts/build_qbox_hexagon_firmware.sh` | PASS |
| `./scripts/build_qbox_linux_arm64.sh` | PASS |
| `QBOX_IREE_VECTOR_ADD_GUEST_ARTIFACTS_DIR=/build/qbox_dev/build/iree-guest-artifacts/vector-add ./scripts/build_qbox_buildroot_arm64.sh` | PASS |
| `./scripts/build_qbox_buildroot_platform.sh` | PASS |
| `./scripts/stage_buildroot_artifacts.sh` | PASS |
| `QBOX_BOOT_TIMEOUT=70 ./scripts/run_iree_vector_add_hexagon_qbox_guest_smoke.sh` | PASS |
| `bash -n scripts/*.sh configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/post-build.sh` | PASS |
| `python3 -m py_compile scripts/check_iree_cnn_pipeline_readiness.py scripts/check_qbox_smmuv3_compliance.py scripts/qbox_pty_runner.py` | PASS |
| `PATH=/build/qbox_dev/build/iree-smoke-venv/bin:$PATH build/iree-smoke-venv/bin/python scripts/check_iree_cnn_pipeline_readiness.py --json build/verification/iree-vector-add-readiness-20260515-final.json` | PASS: `SUMMARY {"pass": 49}` |
| `python3 scripts/check_qbox_smmuv3_compliance.py --json build/verification/iree-vector-add-smmuv3-compliance-20260515.json` | PASS: `SUMMARY {"pass": 1058}` |
| `./scripts/check_buildroot_arm64_lane.sh` | PASS |
| `git diff --check` | PASS |
| `git -C sources/linux diff --check` | PASS |
| `git -C sources/qbox diff --check` | PASS |

## No-overclaim boundary

This verifies a repo-local IREE integration slice using the Apollo Hexagon HAL
registry/plugin frontend and QBox Hexagon firmware job ABI.  It does not claim
upstream IREE Hexagon backend integration or full Arm SMMUv3 bit-exact
compliance; the compliance checker still classifies the model as a functional
slice with remaining upstream-scale SMMUv3 work.
