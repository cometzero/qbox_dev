# Apollo Hexagon MNIST ONNX Compile Verification (2026-05-21)

## 목적

`iree compile -> VMFB -> iree runtime -> apollo hexagon UMD -> apollo
hexagon driver -> apollo hexagon hardware` 구조에서 MNIST 경로가 빈
stub VMFB가 아니라 실제 IREE host compile 산출물을 기준으로 staging되는지
검증했다.

이번 검증은 MNIST-shaped `Flatten + Gemm` ONNX graph를 생성하고,
`iree-import-onnx`와 `iree-compile`로 host/AArch64 VMFB를 만든 뒤,
그 AArch64 VMFB를 Apollo MNIST APKO trailer 경로의 base module로 사용한다.

## 작업공간

- Workspace: `/build/qbox_dev`
- Branch: `feature/qbox_dev`
- Date: `2026-05-21`

## 산출물

- Host smoke output: `build/verification/iree-mnist-host/`
- Guest artifact stage: `build/iree-guest-artifacts/mnist/`
- APKO lane checker: `build/verification/apko-vmfb-lane-mnist-onnx-compile-rerun.json`
- IREE readiness checker: `build/verification/iree-readiness-mnist-onnx-compile-rerun.json`
- QBox guest smoke log:
  `build/verification/qbox-iree-apko-mnist-hexagon-guest-mnist-onnx-compile-rerun-20260521.log`
- QBox guest boot log:
  `build/verification/qbox-iree-apko-mnist-hexagon-guest-boot-mnist-onnx-compile-rerun-20260521.log`

## 검증 결과

| Command | Result | Evidence |
| --- | --- | --- |
| `./scripts/run_iree_mnist_host_smoke.sh` | PASS | `expected_output=1x10xf32=[0 1 2 3 4 5 6 7 8 9]` |
| `./scripts/stage_iree_mnist_guest_artifacts.sh` | PASS | `mnist_aarch64.vmfb`가 Apollo APKO base VMFB로 staging됨 |
| `bash -n scripts/*.sh` | PASS | shell syntax check 통과 |
| `python3 -m py_compile scripts/check_iree_cnn_pipeline_readiness.py scripts/check_apko_vmfb_verification_lane.py scripts/qbox_pty_runner.py scripts/check_qbox_smmuv3_compliance.py` | PASS | Python syntax check 통과 |
| `git diff --check -- . ':!sources/linux' ':!sources/qbox' && git -C sources/linux diff --check && git -C sources/qbox diff --check` | PASS | whitespace check 통과 |
| `python3 scripts/check_apko_vmfb_verification_lane.py --repo . --json build/verification/apko-vmfb-lane-mnist-onnx-compile-rerun.json` | PASS | `summary.pass=13` |
| `python3 scripts/check_iree_cnn_pipeline_readiness.py --repo . --json build/verification/iree-readiness-mnist-onnx-compile-rerun.json` | PASS | `summary.pass=69` |
| `./scripts/check_buildroot_arm64_lane.sh` | PASS | Buildroot/Hexagon/IREE contract surface 통과 |
| `QBOX_IREE_MNIST_GUEST_ARTIFACTS_DIR=/build/qbox_dev/build/iree-guest-artifacts/mnist ./scripts/build_qbox_buildroot_arm64.sh` | PASS | rootfs/DTB 생성 통과 |
| `./scripts/stage_buildroot_artifacts.sh` | PASS | `Image.bin`, `apollo_soc.dtb`, `rootfs.cpio` staging 통과 |
| `QBOX_APKO_MNIST_HEXAGON_GUEST_SMOKE_STAMP=mnist-onnx-compile-rerun-20260521 QBOX_BOOT_TIMEOUT=70 ./scripts/run_iree_apko_mnist_hexagon_qbox_guest_smoke.sh` | PASS | QBox guest APKO MNIST-like output matched |

## Host IREE Compile Evidence

`build/verification/iree-mnist-host/report.json` 기준:

- Pipeline:
  `onnx -> mlir -> iree-compile host -> iree-compile aarch64 -> iree-run-module`
- ONNX: `build/verification/iree-mnist-host/mnist.onnx`
- MLIR: `build/verification/iree-mnist-host/mnist.mlir`
- Host VMFB: `build/verification/iree-mnist-host/mnist_cpu.vmfb`
- AArch64 VMFB: `build/verification/iree-mnist-host/mnist_aarch64.vmfb`
- Expected host output: `1x10xf32=[0 1 2 3 4 5 6 7 8 9]`
- IREE compiler:
  `3.11.0rc20260316 @ e4a3b0405d7d23554da26403658d0e8c3c5ecf25`
- LLVM: `23.0.0git`

## Guest Stage Evidence

`build/iree-guest-artifacts/mnist/manifest.json` 기준:

- `mnist_aarch64.vmfb`: 9378 bytes
- `mnist_apollo.vmfb`: 9458 bytes
- `mnist.onnx`: 31611 bytes
- `mnist.mlir`: 63873 bytes
- `mnist.apko`: 48 bytes
- `host-report.json`: 2855 bytes
- Guest install path: `/opt/qbox/iree/mnist`
- Runtime wrapper: `bin/apollo-iree-run-module`
- Hexagon runner: `bin/apollo-iree-hexagon-runner`
- HAL plugin: `lib/libapollo_iree_hexagon_hal_plugin.so`

## QBox Guest Evidence

QBox guest smoke는 다음 marker들을 확인했다.

- `executable=/opt/qbox/iree/mnist/mnist_aarch64.vmfb entry=mnist_graph bytes=9378`
- `IREE Apollo Hexagon HAL: executable_format=apollo-hexagon-apko-v0`
- `IREE Apollo Hexagon HAL: APKO CMD_SUBMIT MNIST ok`
- `APOLLO_HEXAGON_DMA: command dispatch executable slot=1 kind=3`
- `APOLLO_HEXAGON_DMA: command dispatch mnist`
- `IREE Apollo Hexagon HAL: offload complete queue=1 status=0x4d4e4953`
- `EXEC @mnist_graph [apollo-hexagon]`
- `4xi32=0xfffffffe 0xfffffffd 0xfffffffc 0xfffffffb`

## 남은 Gap

이번 변경은 MNIST 경로의 compile artifact boundary를 명확하게 만들었다.
하지만 아직 다음 항목은 완료가 아니다.

- Apollo payload는 host ONNX graph semantics를 실행하지 않는다.
- `mnist.apko` payload는 deterministic byte-invert stub이다.
- true hardware BO mapping은 아직 구현되지 않았다.
- full APKO code/payload execution은 아직 구현되지 않았다.
- upstream IREE VMFB HAL executable target backend packaging은 아직 남아 있다.
- trained MNIST accuracy 검증은 수행하지 않았다.

따라서 현재 상태는 "MNIST-shaped ONNX compile artifact가 Apollo MNIST APKO
경로의 base VMFB로 staging되고, 별도 deterministic Apollo payload stub이
Linux/UMD/driver/QBox CMD_SUBMIT 경로를 통과한다"로 표현해야 한다.
