# QBox Apollo IREE CNN Pipeline Task Plan

## 목적

ONNX 모델을 MLIR로 import하고 IREE로 compile한 뒤 IREE Runtime에서 실행하는
pipeline을 Apollo QBox 환경에 단계적으로 연결한다. 현재 기능 모델이 지원하는
범위와 부족한 범위를 자동 검증 가능한 task로 나누어 추적한다.

## 범위 판정

- 완료 범위: host CPU에서 tiny CNN의 ONNX → MLIR → IREE CPU VMFB →
  `local-task` runtime 실행을 반복 검증한다.
- 완료 범위: A710 Linux/Buildroot 부팅 lane에서 AArch64 IREE runtime runner와
  VMFB를 rootfs에 staging하고 guest 내부에서 tiny CNN 출력까지 검증한다.
- 완료 범위: Hexagon functional offload path는 `/dev/apollo-hexagon` submit ABI,
  dynamic SMMU TBU map/unmap, Hexagon firmware CNN kernel/runtime, 그리고
  Apollo Hexagon HAL runner/plugin으로 tiny CNN output까지 검증한다.
- 완료 범위: repo-local dynamic C HAL plugin이 `dlopen()`으로 로드되고, upstream
  IREE executable plugin ABI의 `iree_hal_executable_plugin_query` export가 실제
  `iree-run-module --executable_plugin=...` 경로에서 load 가능한지 검증한다.
  단, upstream IREE runtime에 정식 HAL driver/plugin으로 등록되는 구현은 아직
  별도 과제다.
- 완료 범위: guest artifact lane에서 `iree-run-module --device=apollo-hexagon`
  호출이 repo-local upstream-style HAL registry frontend로 dispatch되고 CPU
  fallback device name을 거부한다. 단, upstream IREE source tree에 HAL backend를
  merge하는 작업은 아직 별도 과제다.
- 완료 범위: SMMU-translated TLM path는 4KiB page split, functional page-table
  walk marker, ATS cache marker, PRI resolution marker, fault queue status/clear,
  128KiB scatter/gather DMA stress를 검증한다.
- 완료 범위: Linux driver가 shared SRAM에 SMMUv3-style stream table,
  context descriptor table, 4KB granule 4-level page-table chain을 작성하고,
  Apollo TBU가 downstream TLM으로 STE/CD/L0/L1/L2/L3 descriptor를 순서대로
  fetch/decode하는 architectural walk slice를 검증한다. 또한 architected ATS/PRI
  response accounting과 invalid STE 기반 negative fault replay queue를 검증한다.
  단, Arm SMMUv3 전체 register file, 모든 descriptor bitfield, PCIe ATS TLP,
  PRI packet protocol, GIC/MSI까지 포함한 bit-exact compliance IP 모델은 별도
  upstream-scale 과제다.
- 완료 범위: 64KiB 초과 DMA stress, 2개 command queue, async IRQ/fence register
  모델은 Apollo/QBox functional integration 범위에서 검증한다.

## Upstream/Architectural 후속 과제

| ID | 상태 | 소유 파일/영역 | 결과물 | 완료 기준 |
| --- | --- | --- | --- | --- |
| IREE-CNN-UPSTREAM-001 | 대기 | upstream IREE runtime + Buildroot package | Apollo Hexagon C HAL driver/plugin의 정식 runtime 등록 | local repo shim 없이 `iree-run-module`이 HAL device를 discover/open하고 upstream IREE 테스트가 통과 |
| IREE-CNN-SMMU-001 | 진행(확장 필요) | QBox SMMUv3 model + Linux/IOMMU traces | 전체 Arm SMMUv3 register/descriptor/protocol compliance model | 모든 architected register, descriptor bitfield, event/PRI/fault queue, ATS/PRI transport, interrupt wiring test 통과 |
| IREE-CNN-SMMU-002 | 완료(부분) | `apollo_smmu_tbu`, `apollo-hexagon-test.c` | shared SRAM 4-level table descriptor chain을 downstream TLM으로 fetch/decode하는 architectural descriptor probe | boot/probe log의 `SMMUv3 architectural descriptor probe ok`와 `architectural descriptor walk` marker |
| IREE-CNN-SMMU-003 | 완료(확장 slice) | `apollo_smmu_tbu`, `apollo-hexagon-test.c` | STE/CD walk, architected ATS/PRI response accounting, invalid STE negative fault replay | boot/probe log의 `SMMUv3 stream/context descriptor probe ok`, `SMMUv3 negative fault replay ok`, `architected fault replay queued` marker |
| IREE-CNN-ASYNC-001 | 완료(기능 모델) | QBox DMA/UAPI/driver/firmware | 128KiB tensor, 8 segment SG DMA, 2 queue, async IRQ/fence register | booted guest Hexagon smoke에서 `bytes=131072 segments=8`, queue 0/1, async fence marker 확인 |

## Ultrapilot Task 분해

| ID | 상태 | 소유 파일/영역 | 결과물 | 검증 |
| --- | --- | --- | --- | --- |
| IREE-CNN-001 | 완료 | `scripts/check_iree_cnn_pipeline_readiness.py` | Apollo/IREE readiness 분류 스크립트 | `--require-host-tools` 실행 시 PASS |
| IREE-CNN-002 | 완료 | `scripts/run_iree_tiny_cnn_host_smoke.sh` | tiny CNN ONNX 생성, host/AArch64 VMFB compile, host runtime smoke | expected tensor `[[[54 63][90 99]]]` 확인 |
| IREE-CNN-003 | 완료 | `doc/spec/qbox-iree-cnn-pipeline-tasks.md` | 다음 단계 task backlog와 acceptance criteria | 문서 검토 및 repo check |
| IREE-CNN-004 | 완료 | `doc/verification/qbox-iree-cnn-pipeline-2026-04-28.md` | 한글 구현/검증 리포트 | 실행 로그와 boot evidence 연결 |
| IREE-CNN-005A | 완료 | `scripts/stage_iree_tiny_cnn_guest_artifacts.sh`, `post-build.sh` | AArch64 VMFB/reference/runner를 Buildroot rootfs에 선택 staging | `rootfs.cpio` 내 `/opt/qbox/iree/tiny-cnn` 확인 |
| IREE-CNN-005B | 완료 | Buildroot external tree, IREE runtime package | A710 guest 내부 `iree-run-module` 실행 | qbox guest에서 tensor output `1x1x2x2xf32=[[[54 63][90 99]]]` 비교 |
| IREE-CNN-006 | 완료 | Apollo Linux driver/DTS | `/dev/apollo-hexagon` submit ioctl, completion path | guest userspace command smoke |
| IREE-CNN-007 | 완료 | Apollo SMMU/TBU model | dynamic map/unmap register path over translated TLM data plane | QBox log의 map/unmap/translate marker |
| IREE-CNN-008 | 완료 | IREE-compatible HAL shim | `apollo-iree-hexagon-runner` device/runner prototype | guest runner output 및 HAL marker |
| IREE-CNN-009 | 완료 | Hexagon firmware/kernel | firmware job loop, DMA input/output, tiny CNN kernel | reference tensor comparison |
| IREE-CNN-010 | 완료 | Guest HAL tool | VMFB metadata loader, command buffer, queue, fence 구조화 | `queue=sync command-buffer=fixed fence=host-poll` baseline |
| IREE-CNN-011 | 완료 | Linux UAPI/driver | `APOLLO_HEXAGON_IOC_DMA_STRESS`, SG DMA stress ABI | 초기 SG DMA stress |
| IREE-CNN-012 | 완료 | QBox TBU/DMA/firmware | multi-page TLM split, 64KB DMA cap, firmware DMA copy job | 4KiB read/write translate marker |
| IREE-CNN-013 | 완료 | Smoke/report | 제품화 baseline booted guest 검증 리포트 | `qbox-iree-tiny-cnn-hexagon-guest-20260509-productization.log` |
| IREE-CNN-014 | 완료(로컬) | Guest HAL plugin | repo-local dynamic C HAL plugin + upstream executable plugin export | `readelf` symbol check, `iree-run-module --executable_plugin` guest smoke; upstream HAL 등록은 `IREE-CNN-UPSTREAM-001` |
| IREE-CNN-014A | 완료(기능 slice) | Guest HAL registry frontend | `iree-run-module --device=apollo-hexagon` dispatch + CPU fallback rejection | `qbox-smmuv3-comp-090-verification-2026-05-10.md`, registry negative tests, Hexagon guest smoke |
| IREE-CNN-015 | 완료(기능 모델) | Apollo SMMU TBU | functional page walker marker, ATS cache marker, PRI resolution marker, fault queue status/clear | boot/probe log와 Hexagon smoke marker; architectural full walker는 `IREE-CNN-SMMU-001` |
| IREE-CNN-015A | 완료(부분) | Apollo SMMU TBU + Linux probe | descriptor-backed 4-level page-table probe | `SMMUv3 architectural descriptor probe ok`, `architectural descriptor walk` marker |
| IREE-CNN-015B | 완료(확장 slice) | Apollo SMMU TBU + Linux probe | STE/CD walk, ATS/PRI protocol counters, invalid STE fault replay | `SMMUv3 stream/context descriptor probe ok`, `SMMUv3 negative fault replay ok` marker |
| IREE-CNN-016 | 완료(기능 모델) | DMA/UAPI/driver/firmware | 128KiB tensor, 8 segment SG DMA, 2 queue, async IRQ/fence register model | `SG DMA stress ok bytes=131072 segments=8`, queue 0/1 fence log |
| IREE-CNN-017 | 완료 | Smoke/readiness/report | 통합 검증 및 한글 결과 리포트 | `qbox-iree-hexagon-integration-2026-05-09.md` |

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
4. qbox boot 후 guest shell에서 동일 CNN output을 확인해야 한다. **완료**
5. upstream IREE executable plugin ABI export를 `--executable_plugin`으로 로드해도
   local-task 실행이 성공해야 한다. **완료(로컬 export/load 검증)**
6. Apollo HAL device가 upstream IREE runtime에 정식 C HAL driver/plugin으로 등록되어
   local shim 없이 discover/open되어야 한다. **대기: `IREE-CNN-UPSTREAM-001`**
6-1. QBox guest artifact lane에서 `iree-run-module --device=apollo-hexagon`이
   Apollo registry frontend로 dispatch되고 CPU fallback을 거부해야 한다.
   **완료(기능 slice): `IREE-CNN-014A`**

### Hexagon accelerator path

1. A710 Linux userspace에서 Hexagon job을 submit할 수 있어야 한다. **완료**
2. HAL buffer가 DMA-capable shared memory와 SMMU IOVA로 연결되어야 한다. **완료**
3. Hexagon firmware/runtime이 command queue를 소비하고 completion을 보고해야 한다.
   **완료**
4. IREE HAL runner/plugin/registry frontend가 buffer, executable, queue,
   synchronization을 구현해야 한다.
   **완료: repo-local functional HAL runner + dynamic C plugin + registry dispatch**
5. CNN output이 CPU reference와 일치해야 한다. **완료**

### SMMU, DMA, queue/fence integration

1. SMMU-translated TLM path가 4KiB page 단위로 split되어야 한다. **완료**
2. functional page-table walk, ATS cache, PRI resolution, fault queue가 관찰 가능해야 한다.
   **완료(기능 모델)**
2-1. shared SRAM 4-level table descriptor chain을 TBU가 downstream TLM으로 fetch/decode하는
   architectural descriptor-walk probe가 있어야 한다. **완료(부분): `IREE-CNN-SMMU-002`**
2-2. SMMUv3-style stream/context descriptor walk 및 architected PRI/ATS/fault
   replay observability가 있어야 한다. **완료(확장 slice): `IREE-CNN-SMMU-003`**
2-3. 전체 Arm SMMUv3 register/protocol compliance model을 구현해야 한다.
   **진행(확장 필요): `IREE-CNN-SMMU-001`**
3. 64KiB를 초과하는 tensor/DMA traffic을 검증해야 한다. **완료: 128KiB**
4. 적어도 2개 queue를 사용해야 한다. **완료: queue 0 DMA stress, queue 1 CNN**
5. completion이 async IRQ/fence register로 관찰되고 ACK 가능해야 한다. **완료**

## 현재 상태 및 경계

- A710 CPU IREE baseline은 guest 실행까지 완료됐다. 현재 runner는 PyPI
  `iree-base-runtime` manylinux AArch64 wheel에서 추출한 `iree-run-module`을
  optional rootfs artifact로 staging하는 방식이며, Buildroot native package화는
  별도 과제다.
- Apollo Hexagon path는 실제 QBox guest에서 `/dev/apollo-hexagon` submit ABI,
  repo-local dynamic C HAL plugin, firmware CNN runtime, SMMU-translated DMA를
  통과해 expected tensor까지 검증됐다.
- SMMU 구현은 Apollo/QBox functional model에서 STE/CD fetch, 4-level
  descriptor walk, ATS/PRI response accounting, invalid STE negative fault
  replay까지 검증하는 compliance-oriented slice다. 전체 Arm SMMUv3 register
  file/descriptor bitfield/event queue/PRI packet/GIC interrupt까지 포함한
  bit-exact hardware compliance 구현은 아직 `IREE-CNN-SMMU-001`로 남긴다.
