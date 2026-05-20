# Apollo Hexagon APKO CODE Program 리뷰 반영 검증

날짜: 2026-05-21
작업공간: `/build/qbox_dev`
브랜치: `feature/qbox_dev`
superproject 기준: `0a8c24eeeaf6`
QBox 기준: `26e57728f9ce`
Linux 기준: `0d3b833d0f1a`

## 반영 범위

- QBox `apollo_hexagon_dma`가 `LOAD_CODE`로 전달된 2-word APKO `CODE` program을
  executable slot에 저장한다.
- executable-slot dispatch는 저장된 program을 순차 실행해
  `MODEL_DISPATCH`와 `END`를 확인한 뒤 VADD/CNN/MNIST model-kernel selector로
  넘어간다.
- smoke와 readiness/checker 계약은 `APKO code program dispatch pc=...`와
  `APKO code program end pc=...` marker를 요구한다.
- 이 반영은 full Hexagon instruction execution, true BO/SMMU/TBU page mapping,
  upstream IREE HAL executable packaging 완료가 아니다.

## 검증 결과

| 명령 | 결과 |
| --- | --- |
| `git -C sources/qbox diff --check` | PASS |
| `git diff --check` | PASS |
| `python3 -m py_compile scripts/check_iree_cnn_pipeline_readiness.py scripts/check_apko_vmfb_verification_lane.py` | PASS |
| `bash -n scripts/run_iree_apko_vadd_hexagon_qbox_guest_smoke.sh scripts/run_iree_apko_cnn_hexagon_qbox_guest_smoke.sh scripts/run_iree_apko_mnist_hexagon_qbox_guest_smoke.sh scripts/run_iree_apko_vadd_vmfb_hexagon_qbox_guest_smoke.sh scripts/run_iree_apko_cnn_vmfb_hexagon_qbox_guest_smoke.sh scripts/check_buildroot_arm64_lane.sh` | PASS |
| `./scripts/check_buildroot_arm64_lane.sh` | PASS |
| `python3 scripts/check_iree_cnn_pipeline_readiness.py --repo . --json build/verification/iree-readiness-apko-code-program-20260521.json` | PASS, `SUMMARY {"pass": 70}` |
| `python3 scripts/check_apko_vmfb_verification_lane.py --repo . --json build/verification/apko-vmfb-lane-apko-code-program-20260521.json` | PASS, `SUMMARY {"pass": 15}` |
| `cmake --build sources/qbox/build --target apollo-hexagon-dma-tests -j$(nproc)` | PASS |
| `ctest --test-dir sources/qbox/build --output-on-failure -R apollo-hexagon-dma-tests` | PASS, `1/1` |
| `./scripts/build_qbox_buildroot_platform.sh` | PASS |
| `QBOX_BOOT_TIMEOUT=80 QBOX_APKO_VADD_HEXAGON_GUEST_SMOKE_STAMP=20260521-054906 ./scripts/run_iree_apko_vadd_hexagon_qbox_guest_smoke.sh` | PASS |

## Runtime Evidence

주요 로그:

- `build/verification/qbox-iree-apko-vadd-hexagon-guest-20260521-054906.log`
- `build/verification/qbox-iree-apko-vadd-hexagon-guest-boot-20260521-054906.log`
- `build/verification/iree-readiness-apko-code-program-20260521.json`
- `build/verification/apko-vmfb-lane-apko-code-program-20260521.json`

확인 marker:

```text
APOLLO_HEXAGON_DMA: APKO code program dispatch pc=0 opcode=2 word=65538
APOLLO_HEXAGON_DMA: APKO code program end pc=1
4xf32=11 22 33 44
```

## 남은 Blocker

- 후속 direct-BO-TBU 리뷰 반영으로 command BO input/output tensor는 더 이상
  QBox shared-window copy shim을 거치지 않는다. 다만 이 문서의 검증 실행 당시에는
  해당 direct map 변경 전 상태였으므로, 최신 증거는 별도 direct-BO-TBU 검증 문서에
  기록한다.
- APKO `CODE` program은 2-word transition ABI다. full nontrivial APKO instruction
  execution 또는 실제 Hexagon binary execution은 아직 미완료다.
- VMFB trailer는 repo-local transition packaging이다. upstream IREE HAL executable
  section packaging 완료로 주장하지 않는다.
