# Apollo Hexagon MNIST-like APKO 리뷰 반영 검증

- 날짜: 2026-05-21
- 작업 경로: `/build/qbox_dev`
- 루트 브랜치: `feature/qbox_dev`
- 기준 루트 HEAD: `b93fb173fabc test(apollo): prove CNN VMFB CMDQ path`
- 기준 Linux submodule HEAD: `d6106105b8ad feat(apollo): unblock CNN CMDQ submit`
- 기준 QBox submodule HEAD: `ac7975c17763 test(apollo): prove CNN CMDQ dispatch`

## 범위

리뷰 반영으로 MNIST-like APKO entry kind를 Linux UAPI, guest UAPI/HAL, QBox
command queue model test, staging, smoke, checker, 한글 계획 문서에 연결했다.
이 검증은 DNN kernel ABI와 `CMD_SUBMIT` 실행 경계를 확인한다.

이 결과는 true MNIST ONNX compile/runtime semantics를 의미하지 않는다. 현재
artifact는 deterministic byte-invert MNIST-like stub이다.

## 실행 명령

```sh
bash -n scripts/*.sh
python3 -m py_compile \
  scripts/check_iree_cnn_pipeline_readiness.py \
  scripts/check_apko_vmfb_verification_lane.py \
  scripts/check_qbox_smmuv3_compliance.py \
  scripts/qbox_pty_runner.py
git -C sources/linux diff --check
git diff --check -- . ':!sources/linux' ':!sources/qbox'
git -C sources/qbox diff --check
sources/qbox/build/tests/components/apollo_hexagon_dma/apollo-hexagon-dma-tests
python3 scripts/check_iree_cnn_pipeline_readiness.py \
  --repo . \
  --json build/verification/iree-readiness-mnist-review-rerun.json
python3 scripts/check_apko_vmfb_verification_lane.py \
  --repo . \
  --json build/verification/apko-vmfb-lane-mnist-review-rerun.json
./scripts/check_buildroot_arm64_lane.sh
./scripts/build_qbox_linux_arm64.sh
./scripts/stage_buildroot_artifacts.sh
QBOX_APKO_MNIST_HEXAGON_GUEST_SMOKE_STAMP=review-rerun-20260521 \
QBOX_BOOT_TIMEOUT=70 \
  ./scripts/run_iree_apko_mnist_hexagon_qbox_guest_smoke.sh
```

## 결과

- shell/python/diff 정적 검사: PASS
- QBox Apollo Hexagon DMA component tests: PASS, 14 tests
- IREE CNN pipeline readiness: PASS 63, MISSING 5
- APKO VMFB verification lane: PASS 12, BLOCKED_MISSING_TOOL 1
- Buildroot ARM64 lane contract: PASS
- Linux Image build: PASS
- artifact staging: PASS
- QBox guest MNIST-like APKO smoke: PASS

## 주요 smoke marker

```text
IREE Apollo Hexagon HAL: executable_format=apollo-hexagon-apko-v0
IREE Apollo Hexagon HAL: queues=2 command-buffer=generic-submit
command BO bound MNIST dispatch
APOLLO_HEXAGON_DMA: command load executable slot=1 kind=3
APOLLO_HEXAGON_DMA: command dispatch executable slot=1 kind=3
APOLLO_HEXAGON_DMA: command dispatch mnist
IREE Apollo Hexagon HAL: APKO CMD_SUBMIT MNIST ok
IREE Apollo Hexagon HAL: offload complete queue=1 status=0x4d4e4953
EXEC @mnist_graph [apollo-hexagon]
4xi32=0xfffffffe 0xfffffffd 0xfffffffc 0xfffffffb
```

## Evidence

- smoke log:
  `build/verification/qbox-iree-apko-mnist-hexagon-guest-review-rerun-20260521.log`
- boot log:
  `build/verification/qbox-iree-apko-mnist-hexagon-guest-boot-review-rerun-20260521.log`
- readiness JSON:
  `build/verification/iree-readiness-mnist-review-rerun.json`
- APKO VMFB lane JSON:
  `build/verification/apko-vmfb-lane-mnist-review-rerun.json`

## 남은 blocker

- true hardware BO mapping
- full APKO code/payload execution
- true MNIST ONNX compile/runtime semantics
- upstream IREE VMFB HAL executable section packaging
- host-side IREE/ONNX tooling:
  `iree-import-onnx`, `iree-compile`, `iree-run-module`, Python `onnx`,
  Python `numpy`

## OMX team 상태

`omx team status continue-apollo-hexag-e808b943` 직접 실행은 현재 Codex App/native
outside-tmux shell 훅에서 차단된다. 대신 `.omx/state/team-state.json`과 session
state를 확인했으며, 해당 team state는 `active=false`, `current_phase=cancelled`,
`completed_at=2026-05-20T15:34:34.171Z`로 남아 있다. 팀 operational checkpoint
commit들은 현재 `HEAD`에 reachable하지 않고, 루트 히스토리는 이미 Conventional
final commit 형태로 정리되어 있다.
