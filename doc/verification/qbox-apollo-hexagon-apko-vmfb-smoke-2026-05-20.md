# QBox Apollo Hexagon APKO VMFB 검증 리포트

- 날짜: 2026-05-20
- 갱신: 2026-05-21
- 대상: `/build/qbox_dev`
- 기준 superproject: `5421510bbae7`
- Linux submodule: `7f510a9e2872`
- QBox submodule: `b9747372ab73`

## 결론

PASS. 리뷰 반영 범위에서 QBox Apollo Hexagon command queue에 deterministic
CNN 및 MNIST-like model-kernel stub을 추가했고, VMFB 내부 APKO trailer를 읽어
VADD/CNN command BO `LOAD_EXECUTABLE` + executable-slot `DISPATCH` 경로로 실행하는
guest smoke를 다시 통과시켰다.

이번 결과는 "모델 커널 실행 구조"의 하위 기반이다. 즉, QBox 모델은
VADD/CNN/MNIST-like dispatch kind를 인식하고 VADD/CNN은 Linux/UMD binding table을
통해 CMDQ로 실행된다. MNIST binding, true hardware BO mapping, full APKO code
execution, upstream IREE VMFB HAL executable packaging은 아직 남아 있다.

## 리뷰 반영 사항

| 영역 | 반영 내용 |
| --- | --- |
| QBox DMA 모델 | `CMDQ_DISPATCH_KIND_CNN`, `CMDQ_DISPATCH_KIND_MNIST` 추가 |
| QBox command queue | direct dispatch와 executable-slot dispatch에서 CNN/MNIST-like stub 처리 |
| QBox 테스트 | CNN direct dispatch, MNIST-like direct dispatch, CNN executable-slot dispatch, bad dispatch-kind fault 테스트 추가 |
| Linux driver | `CMD_SUBMIT` binding-table path를 VADD 전용에서 VADD/CNN model dispatch로 일반화 |
| Apollo IREE HAL UMD | APKO VADD/CNN 모두 BO create/bind + command BO submit 경로를 사용 |
| Readiness checker | VADD/CNN CMDQ binding을 PASS로 보고하고 남은 gap을 MNIST/true BO/upstream IREE backend로 좁힘 |
| Smoke script | UART interleave로 `LOAD_EXECUTABLE` driver marker가 쪼개져도 QBox DMA marker로 대체 판정 가능하게 수정 |

## 검증 명령

```bash
cd /build/qbox_dev/sources/qbox
cmake --build build --target apollo-hexagon-dma-tests --parallel
./build/tests/components/apollo_hexagon_dma/apollo-hexagon-dma-tests

cd /build/qbox_dev
./scripts/run_iree_tiny_cnn_host_smoke.sh
./scripts/run_iree_vector_add_host_smoke.sh
./scripts/stage_iree_tiny_cnn_guest_artifacts.sh
./scripts/stage_iree_vector_add_guest_artifacts.sh
QBOX_IREE_GUEST_ARTIFACTS_DIR=/build/qbox_dev/build/iree-guest-artifacts/tiny-cnn \
QBOX_IREE_VECTOR_ADD_GUEST_ARTIFACTS_DIR=/build/qbox_dev/build/iree-guest-artifacts/vector-add \
  ./scripts/build_qbox_buildroot_arm64.sh
./scripts/stage_buildroot_artifacts.sh
./scripts/build_qbox_buildroot_platform.sh
bash -n scripts/*.sh
PYTHONPYCACHEPREFIX=/tmp/qbox-pycache python3 -m py_compile \
  scripts/qbox_pty_runner.py \
  scripts/check_qbox_smmuv3_compliance.py \
  scripts/check_iree_cnn_pipeline_readiness.py \
  scripts/check_apko_vmfb_verification_lane.py
./scripts/check_buildroot_arm64_lane.sh
PYTHONPYCACHEPREFIX=/tmp/qbox-pycache \
  python3 scripts/check_qbox_smmuv3_compliance.py --repo . \
  --json build/verification/smmuv3-cnn-cmdq-review-2026-05-21.json
PYTHONPYCACHEPREFIX=/tmp/qbox-pycache \
  python3 scripts/check_apko_vmfb_verification_lane.py --repo . \
  --json build/verification/apko-vmfb-verification-lane-cnn-cmdq-2026-05-21.json
PATH=/build/qbox_dev/build/iree-smoke-venv/bin:$PATH \
PYTHONPYCACHEPREFIX=/tmp/qbox-pycache \
  /build/qbox_dev/build/iree-smoke-venv/bin/python \
  scripts/check_iree_cnn_pipeline_readiness.py --repo . \
  --json build/verification/iree-readiness-cnn-cmdq-review-venv-2026-05-21.json
QBOX_APKO_CNN_HEXAGON_GUEST_SMOKE_STAMP=20260521-cnn-cmdq-review \
  ./scripts/run_iree_apko_cnn_hexagon_qbox_guest_smoke.sh
QBOX_APKO_CNN_VMFB_HEXAGON_GUEST_SMOKE_STAMP=20260521-cnn-cmdq-review \
  ./scripts/run_iree_apko_cnn_vmfb_hexagon_qbox_guest_smoke.sh
QBOX_APKO_VADD_VMFB_HEXAGON_GUEST_SMOKE_STAMP=20260521-cnn-cmdq-review \
  ./scripts/run_iree_apko_vadd_vmfb_hexagon_qbox_guest_smoke.sh
git diff --check && git -C sources/linux diff --check && git -C sources/qbox diff --check
```

## 검증 결과

- QBox component build: PASS.
- QBox Apollo Hexagon DMA tests: PASS, 14 tests.
- Shell syntax: PASS.
- Python compile: PASS.
- Buildroot ARM64 lane contract: PASS.
- IREE/CNN readiness with repo venv: PASS 67.
- SMMUv3 compliance checker: PASS 1063.
- APKO VMFB verification lane: PASS 11, `unsupported_onnx_negative_tool_gate`
  `BLOCKED_MISSING_TOOL` 1.
- Buildroot rootfs rebuild, artifact staging, QBox platform rebuild: PASS.
- APKO CNN sidecar guest smoke: PASS.
- APKO CNN VMFB guest smoke: PASS.
- APKO VADD VMFB guest smoke: PASS.

최종 smoke 핵심 marker:

```text
IREE Apollo Hexagon HAL: executable_source=vmfb-embedded-apko
IREE Apollo Hexagon HAL: generic_abi_version=1 executable_formats=0x00000002
APOLLO_HEXAGON_DMA: command load executable slot=1 kind=1
APOLLO_HEXAGON_DMA: command dispatch executable slot=1 kind=1
APOLLO_HEXAGON_DMA: command dispatch cnn input=0x10010000 output=0x10011000 bytes=0x40
IREE Apollo Hexagon HAL: APKO CMD_SUBMIT CNN ok
EXEC @tiny_cnn_graph [apollo-hexagon]
1x1x2x2xf32=[[[54 63][90 99]]]
APOLLO_HEXAGON_DMA: command load executable slot=1 kind=2
APOLLO_HEXAGON_DMA: command dispatch executable slot=1 kind=2
APOLLO_HEXAGON_DMA: command dispatch vadd input=0x10010000 output=0x10011000 bytes=0x20
IREE Apollo Hexagon HAL: APKO CMD_SUBMIT VADD ok
IREE Apollo Hexagon HAL: command buffer submitted
EXEC @vector_add_graph [apollo-hexagon]
4xf32=11 22 33 44
```

## 증거 로그

- 최종 PASS smoke:
  `build/verification/qbox-iree-apko-cnn-hexagon-guest-20260521-cnn-cmdq-review.log`
- 최종 PASS CNN VMFB smoke:
  `build/verification/qbox-iree-apko-cnn-vmfb-hexagon-guest-20260521-cnn-cmdq-review.log`
- 최종 PASS VADD VMFB smoke:
  `build/verification/qbox-iree-apko-vadd-vmfb-hexagon-guest-20260521-cnn-cmdq-review.log`
- readiness JSON:
  `build/verification/iree-readiness-cnn-cmdq-review-venv-2026-05-21.json`
- APKO VMFB lane JSON:
  `build/verification/apko-vmfb-verification-lane-cnn-cmdq-2026-05-21.json`
- SMMUv3 compliance JSON:
  `build/verification/smmuv3-cnn-cmdq-review-2026-05-21.json`
- smoke script 보강 전 실패 로그:
  `build/verification/qbox-iree-apko-vadd-vmfb-hexagon-guest-20260520-review-final.log`

보강 전 실패는 실행 실패가 아니라 marker 판정 실패였다. 로그에는
`4xf32=11 22 33 44`가 있었지만, UART interleave로 Linux driver의
`LOAD_EXECUTABLE slot=1 kind=2` 문자열이 쪼개졌다. 수정 후에는 같은 의미의
QBox DMA marker도 허용한다.

## 남은 범위

- host `iree-import-onnx`, `iree-compile`, `iree-run-module`, Python `onnx`,
  Python `numpy`는 repo venv 기준 PASS다. system Python/PATH로 실행하면 여전히
  missing으로 분류될 수 있다.
- CNN/MNIST-like QBox CMDQ dispatch는 deterministic stub이다. 실제 graph
  payload 실행, weight/tensor binding, scheduler semantics는 별도 구현이 필요하다.
- Linux/UMD는 현재 APKO VADD/CNN binding-table command BO 경로를 검증했다.
  MNIST CMDQ binding은 후속 작업이다.
- boot log의 Linux version 문자열은 기존 staged Image의 dirty suffix를 포함한다.
  현재 source 기준 Linux submodule은 `7f510a9e2872`로 정리되어 있으나, release
  증거로 쓰려면 Linux Image를 재빌드해 dirty suffix 없는 boot log를 다시 남겨야
  한다.
