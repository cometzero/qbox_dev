# QBox Apollo IREE CNN Pipeline Task Plan

## 목적

ONNX 모델을 MLIR로 import하고 IREE로 compile한 뒤 IREE Runtime에서 실행하는
pipeline을 Apollo QBox 환경에 단계적으로 연결한다. 현재 기능 모델이 지원하는
범위와 부족한 범위를 자동 검증 가능한 task로 나누어 추적한다.

## 범위 판정

- 즉시 완료 범위: host CPU에서 tiny CNN의 ONNX → MLIR → IREE CPU VMFB →
  `local-task` runtime 실행을 반복 검증한다.
- 부분 준비 범위: A710 Linux/Buildroot 부팅 lane은 준비되어 있으나, guest 내부
  IREE runtime packaging과 runner는 아직 없다.
- 미지원 범위: Hexagon을 IREE accelerator/HAL device로 사용하는 경로는 아직
  command ABI, Linux user submit driver, executable loader, dynamic SMMU mapping,
  Hexagon kernel runtime이 없다.

## Ultrapilot Task 분해

| ID | 상태 | 소유 파일/영역 | 결과물 | 검증 |
| --- | --- | --- | --- | --- |
| IREE-CNN-001 | 완료 | `scripts/check_iree_cnn_pipeline_readiness.py` | Apollo/IREE readiness 분류 스크립트 | `--require-host-tools` 실행 시 21개 PASS |
| IREE-CNN-002 | 완료 | `scripts/run_iree_tiny_cnn_host_smoke.sh` | tiny CNN ONNX 생성, host/AArch64 VMFB compile, host runtime smoke | expected tensor `[[[54 63][90 99]]]` 확인 |
| IREE-CNN-003 | 완료 | `doc/spec/qbox-iree-cnn-pipeline-tasks.md` | 다음 단계 task backlog와 acceptance criteria | 문서 검토 및 repo check |
| IREE-CNN-004 | 완료 | `doc/verification/qbox-iree-cnn-pipeline-2026-04-28.md` | 한글 구현/검증 리포트 | 실행 로그와 boot evidence 연결 |
| IREE-CNN-005A | 완료 | `scripts/stage_iree_tiny_cnn_guest_artifacts.sh`, `post-build.sh` | AArch64 VMFB/reference/runner를 Buildroot rootfs에 선택 staging | `rootfs.cpio` 내 `/opt/qbox/iree/tiny-cnn` 확인 |
| IREE-CNN-005B | 차기 | Buildroot external tree, IREE runtime package | A710 guest 내부 `iree-run-module` 실행 | qbox guest에서 tensor output 비교 |
| IREE-CNN-006 | 차기 | Apollo Linux driver/DTS | user submit ABI, mmap/ioctl, completion path | userspace command smoke |
| IREE-CNN-007 | 차기 | Apollo SMMU/TBU model | dynamic map/unmap, fault reporting, >4KB DMA | SMMU fault/no-fault test |
| IREE-CNN-008 | 차기 | IREE out-of-tree HAL | `apollo-hexagon` HAL driver/device prototype | IREE Runtime device enumeration |
| IREE-CNN-009 | 차기 | Hexagon firmware/kernel | non-trivial conv/vector kernel execution | reference tensor comparison |

## Acceptance Criteria

### Host tiny CNN baseline

1. `tiny_cnn.onnx` 생성.
2. `iree-import-onnx --opset-version 17` 성공.
3. `iree-compile --iree-hal-target-device=local` 및 `llvm-cpu` backend 성공.
4. `iree-run-module --device=local-task --function=tiny_cnn_graph` 성공.
5. 출력이 `1x1x2x2xf32=[[[54 63][90 99]]]`와 일치.

### A710 guest baseline

1. Buildroot rootfs에 IREE runtime 또는 runner가 포함되어야 한다.
2. AArch64 target VMFB 또는 compatible runtime artifact가 staging되어야 한다. **완료**
3. qbox boot 후 staged rootfs가 기존 boot lane을 깨지 않아야 한다. **완료**
4. qbox boot 후 guest shell에서 동일 CNN output을 확인해야 한다. **차기: IREE runtime 필요**

### Hexagon accelerator path

1. A710 Linux userspace에서 Hexagon job을 submit할 수 있어야 한다.
2. HAL buffer가 DMA-capable shared memory와 SMMU IOVA로 연결되어야 한다.
3. Hexagon firmware/runtime이 command queue를 소비하고 completion을 보고해야 한다.
4. IREE HAL driver가 buffer, executable, queue, synchronization을 구현해야 한다.
5. CNN output이 CPU reference와 일치해야 한다.

## 현재 Blocker

- repo에는 IREE guest runtime package 또는 Buildroot package가 없다. AArch64 VMFB/reference artifact staging은 준비됨.
- `apollo-hexagon-test`는 probe-time DMA selftest driver이며 userspace ABI가 없다.
- `apollo_hexagon_dma`는 4KB smoke copy 제한을 가진 MMIO DMA model이다.
- `apollo_smmu_tbu`는 fixed-window translator이며 SMMUv3 page-table datapath가 아니다.
- libqemu는 system-mode target 중심이고 Hexagon user-mode runtime 경로가 없다.
