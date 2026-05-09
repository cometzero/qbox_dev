# QBox Apollo IREE CNN Pipeline Task Plan

## 목적

ONNX 모델을 MLIR로 import하고 IREE로 compile한 뒤 IREE Runtime에서 실행하는
pipeline을 Apollo QBox 환경에 단계적으로 연결한다. 현재 기능 모델이 지원하는
범위와 부족한 범위를 자동 검증 가능한 task로 나누어 추적한다.

## 범위 판정

- 즉시 완료 범위: host CPU에서 tiny CNN의 ONNX → MLIR → IREE CPU VMFB →
  `local-task` runtime 실행을 반복 검증한다.
- 완료 범위: A710 Linux/Buildroot 부팅 lane에서 AArch64 IREE runtime runner와
  VMFB를 rootfs에 staging하고 guest 내부에서 tiny CNN 출력까지 검증한다.
- 완료 범위: Hexagon functional offload path는 `/dev/apollo-hexagon` submit ABI,
  dynamic SMMU TBU map/unmap, Hexagon firmware CNN kernel/runtime, 그리고
  IREE-compatible Apollo Hexagon HAL runner shim으로 tiny CNN output까지 검증한다.

## Ultrapilot Task 분해

| ID | 상태 | 소유 파일/영역 | 결과물 | 검증 |
| --- | --- | --- | --- | --- |
| IREE-CNN-001 | 완료 | `scripts/check_iree_cnn_pipeline_readiness.py` | Apollo/IREE readiness 분류 스크립트 | `--require-host-tools` 실행 시 21개 PASS |
| IREE-CNN-002 | 완료 | `scripts/run_iree_tiny_cnn_host_smoke.sh` | tiny CNN ONNX 생성, host/AArch64 VMFB compile, host runtime smoke | expected tensor `[[[54 63][90 99]]]` 확인 |
| IREE-CNN-003 | 완료 | `doc/spec/qbox-iree-cnn-pipeline-tasks.md` | 다음 단계 task backlog와 acceptance criteria | 문서 검토 및 repo check |
| IREE-CNN-004 | 완료 | `doc/verification/qbox-iree-cnn-pipeline-2026-04-28.md` | 한글 구현/검증 리포트 | 실행 로그와 boot evidence 연결 |
| IREE-CNN-005A | 완료 | `scripts/stage_iree_tiny_cnn_guest_artifacts.sh`, `post-build.sh` | AArch64 VMFB/reference/runner를 Buildroot rootfs에 선택 staging | `rootfs.cpio` 내 `/opt/qbox/iree/tiny-cnn` 확인 |
| IREE-CNN-005B | 완료 | Buildroot external tree, IREE runtime package | A710 guest 내부 `iree-run-module` 실행 | qbox guest에서 tensor output `1x1x2x2xf32=[[[54 63][90 99]]]` 비교 |
| IREE-CNN-006 | 완료 | Apollo Linux driver/DTS | `/dev/apollo-hexagon` submit ioctl, completion path | guest userspace command smoke |
| IREE-CNN-007 | 완료 | Apollo SMMU/TBU model | dynamic map/unmap register path over translated TLM data plane | QBox log의 map/unmap/translate marker |
| IREE-CNN-008 | 완료 | IREE-compatible HAL shim | `apollo-iree-hexagon-runner` device/runner prototype | guest runner output 및 HAL marker |
| IREE-CNN-009 | 완료 | Hexagon firmware/kernel | firmware job loop, DMA input/output, tiny CNN kernel | reference tensor comparison |

## Acceptance Criteria

### Host tiny CNN baseline

1. `tiny_cnn.onnx` 생성.
2. `iree-import-onnx --opset-version 17` 성공.
3. `iree-compile --iree-hal-target-device=local` 및 `llvm-cpu` backend 성공.
4. `iree-run-module --device=local-task --function=tiny_cnn_graph` 성공.
5. 출력이 `1x1x2x2xf32=[[[54 63][90 99]]]`와 일치.

### A710 guest baseline

1. Buildroot rootfs에 IREE runtime 또는 runner가 포함되어야 한다. **완료**
2. AArch64 target VMFB 또는 compatible runtime artifact가 staging되어야 한다. **완료**
3. qbox boot 후 staged rootfs가 기존 boot lane을 깨지 않아야 한다. **완료**
4. qbox boot 후 guest shell에서 동일 CNN output을 확인해야 한다. **완료: `scripts/run_iree_tiny_cnn_qbox_guest_smoke.sh`**

### Hexagon accelerator path

1. A710 Linux userspace에서 Hexagon job을 submit할 수 있어야 한다. **완료**
2. HAL buffer가 DMA-capable shared memory와 SMMU IOVA로 연결되어야 한다. **완료**
3. Hexagon firmware/runtime이 command queue를 소비하고 completion을 보고해야 한다. **완료**
4. IREE HAL driver가 buffer, executable, queue, synchronization을 구현해야 한다. **완료: repo-local functional HAL runner shim**
5. CNN output이 CPU reference와 일치해야 한다. **완료**

## 현재 Blocker

- A710 CPU IREE baseline은 guest 실행까지 완료됐다. 단, 현재 runner는 PyPI `iree-base-runtime` manylinux AArch64 wheel에서 추출한 `iree-run-module`을 optional rootfs artifact로 staging하는 방식이며, Buildroot native package화는 아직 별도 과제다.
- `apollo-hexagon-test`는 `/dev/apollo-hexagon` ioctl submit ABI까지 확장됐다.
- `apollo_smmu_tbu`는 dynamic map/unmap register path를 제공하지만, 아직 실제
  ARM SMMUv3 page-table walker는 아니다.
- `apollo-iree-hexagon-runner`는 IREE-compatible functional HAL shim이다. Upstream
  IREE C HAL plugin 형태로 runtime에 동적 등록하는 작업은 별도 제품화 과제다.
- `apollo_hexagon_dma`는 현재 small CNN fixture에 충분한 4KB transfer limit을
  유지한다. 대형 tensor용 scatter/gather 및 multi-page stress는 별도 과제다.
