# QBox Apollo IREE Hexagon 통합 구현/검증 리포트

## 요약

2026-05-09 기준으로 Apollo QBox에서 A710 Linux/Buildroot guest를 부팅한 뒤,
IREE tiny-CNN을 CPU local-task와 Apollo Hexagon functional accelerator path에서
모두 실행해 동일 출력(`1x1x2x2xf32=[[[54 63][90 99]]]`)을 확인했다.
이번 통합 범위는 **repo-local functional integration**이며, 다음 세 가지를
검증했다.

1. repo-local dynamic C HAL plugin 및 upstream IREE executable plugin export/load.
2. SMMU-translated TLM path의 functional page-walk/ATS/PRI/fault queue 관찰성.
3. shared SRAM 4KB granule 4-level page-table chain을 downstream TLM으로
   fetch/decode하는 architectural descriptor-walk probe.
4. 64KiB 초과 tensor/DMA, multi command queue, async IRQ/fence completion model.

다만 아래 두 항목은 아직 완료로 판정하지 않는다.

- upstream IREE runtime에 Apollo HAL device가 정식 C HAL driver/plugin으로 동적
  등록되는 구현.
- 실제 ARM SMMUv3 stream/context descriptor 기반 full architectural page-table
  walker와 architected PRI/ATS/fault queue protocol 전체 구현. 이번 pass에서는
  4-level table descriptor chain + L3 page descriptor fetch/decode probe까지만 추가했다.

## 구현 범위

### IREE dynamic C HAL plugin (repo-local)

- 추가/변경 파일:
  - `configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_hexagon_plugin.c`
  - `configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_hexagon_plugin.h`
  - `configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_executable_plugin_abi.h`
  - `configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_hexagon_hal.[ch]`
- `libapollo_iree_hexagon_hal_plugin.so`가 다음 symbol을 export한다.
  - `apollo_iree_hexagon_plugin_query`
  - `iree_hal_executable_plugin_query`
- `iree_hal_executable_plugin_query`는 upstream IREE
  `system_library_plugin` loader가 기대하는 v0 plugin header pointer를 반환하도록
  정리했다. 이는 executable plugin export/load 검증이며, upstream IREE HAL device
  registry에 Apollo driver를 정식 등록한 것은 아니다.
- `run_tiny_cnn_guest.sh`는 `iree-run-module --executable_plugin=...` 경로를 통해
  plugin load 가능성을 검증한다.
- `run_tiny_cnn_hexagon_guest.sh`는 Apollo HAL plugin을 `dlopen()`으로 로드해
  Hexagon submit path를 사용한다.

### SMMU functional model (architectural full model 아님)

- 변경 파일:
  - `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
- 기능:
  - dynamic map/unmap/clear slot 확장.
  - 4KiB page boundary 기준 TLM transaction split.
  - functional page-table walk marker.
  - downstream TLM descriptor fetch 기반 architectural 4-level descriptor probe.
  - ATS cache fill marker.
  - PRI request resolved marker.
  - fault queue push/status/clear register.
- Linux driver probe가 SMMU feature register와 fault probe를 확인한다.

### DMA, queue, async fence

- 변경 파일:
  - `sources/qbox/systemc-components/apollo_hexagon_dma/include/apollo_hexagon_dma.h`
  - `sources/qbox/platforms/buildroot/fw/hexagon_dma_smoke.s`
  - `sources/linux/drivers/soc/apollo/apollo-hexagon-test.c`
  - `sources/linux/include/uapi/linux/apollo_hexagon.h`
- 기능:
  - DMA cap을 256KiB로 확장.
  - 검증 stress traffic을 128KiB/8 segment로 확장.
  - queue 0은 SG DMA stress, queue 1은 CNN offload에 사용.
  - job fence sequence와 IRQ status/ACK register를 추가.
  - firmware가 CNN job과 SG DMA copy job을 모두 처리한다.

## 검증 결과

| 항목 | 결과 | 근거 |
| --- | --- | --- |
| guest tools build | PASS | `build/verification/apollo-hexagon-guest-tools-integration-r2-20260509.log` |
| plugin symbols | PASS | `build/verification/apollo-hexagon-plugin-symbols-integration-r2-20260509.log` |
| IREE artifact staging | PASS | `build/verification/stage-iree-integration-r2-20260509.log` |
| Linux build | PASS | `build/verification/linux-20260509-integration.log` |
| QBox platform build | PASS | `build/verification/qbox-platform-20260509-integration-r2.log` |
| Buildroot rootfs rebuild | PASS | `build/verification/buildroot-20260509-integration-r2.log` |
| artifact staging | PASS | `build/verification/stage-artifacts-20260509-integration-r2.log` |
| readiness check | PASS 35 | `build/verification/iree-cnn-readiness-integration-20260509.txt` |
| CPU local-task guest smoke + executable plugin | PASS | `build/verification/qbox-iree-tiny-cnn-guest-20260509-integration-plugin-r2.log` |
| Hexagon guest smoke | PASS | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260509-integration-r3.log` |
| architectural descriptor probe Linux build | PASS | `build/verification/linux-arch-ptw-20260509-225449.log` |
| architectural descriptor probe QBox platform build | PASS | `build/verification/qbox-platform-arch-ptw-20260509-225449.log` |
| architectural descriptor probe artifact staging | PASS | `build/verification/stage-artifacts-arch-ptw-20260509-225606.log` |
| architectural descriptor probe guest tools build | PASS | `build/verification/apollo-hexagon-guest-tools-arch-ptw-20260509-225606.log` |
| architectural descriptor probe Hexagon guest smoke | PASS | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260509-arch-ptw.log` |
| 4-level architectural descriptor probe Linux build | PASS | `build/verification/linux-arch-4level-20260509.log` |
| 4-level architectural descriptor probe QBox platform build | PASS | `build/verification/qbox-platform-arch-4level-20260509.log` |
| 4-level architectural descriptor probe artifact staging | PASS | `build/verification/stage-artifacts-arch-4level-20260509.log` |
| 4-level architectural descriptor probe guest tools build | PASS | `build/verification/apollo-hexagon-guest-tools-arch-4level-20260509.log` |
| 4-level architectural descriptor probe Hexagon guest smoke | PASS | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260509-arch-4level.log` |

대표 marker:

```text
IREE Apollo Hexagon HAL: dynamic C HAL plugin=/opt/qbox/iree/tiny-cnn/lib/libapollo_iree_hexagon_hal_plugin.so name=apollo-hexagon-hal api=1
IREE Apollo Hexagon HAL: upstream executable_plugin export=iree_hal_executable_plugin_query available
IREE Apollo Hexagon HAL: queues=2 command-buffer=fixed fence=async-irq-poll
APOLLO_SMMU_TBU: architectural table walk stream-id=0x1 level=0 table=0xa18000 index=0x0 desc-pa=0xa18000 desc=0xa19003 next-table=0xa19000
APOLLO_SMMU_TBU: architectural table walk stream-id=0x1 level=1 table=0xa19000 index=0x0 desc-pa=0xa19000 desc=0xa1a003 next-table=0xa1a000
APOLLO_SMMU_TBU: architectural table walk stream-id=0x1 level=2 table=0xa1a000 index=0x80 desc-pa=0xa1a400 desc=0xa1b003 next-table=0xa1b000
APOLLO_SMMU_TBU: architectural descriptor walk stream-id=0x1 levels=4 ttbr=0xa18000 desc-pa=0xa1b000 desc=0xa00703 iova=0x10000000 pa=0xa00000
apollo-hexagon-test 1c220000.hexagon: SMMUv3 architectural descriptor probe ok 4-level ttbr=0xa18000 iova=0x10000000 l0=0 l1=0 l2=128 l3=0 desc=0xa00703 pa=0xa00000 levels=4
apollo-hexagon-test 1c220000.hexagon: SMMUv3 page-table walker/ATS/PRI/fault queue ready features=0x3f
apollo-hexagon-test 1c220000.hexagon: SG DMA stress ok queue=0 fence=1 bytes=131072 segments=8
apollo-hexagon-test 1c220000.hexagon: accelerator tiny cnn ok queue=1 fence=2 status=0x434e4e4f
1x1x2x2xf32=[[[54 63][90 99]]]
```

## 실행한 주요 명령

```bash
./scripts/build_apollo_hexagon_guest_tools.sh
readelf -Ws build/apollo-hexagon-guest-tools/lib/libapollo_iree_hexagon_hal_plugin.so \
  | grep -E 'apollo_iree_hexagon_plugin_query|iree_hal_executable_plugin_query'
./scripts/stage_iree_tiny_cnn_guest_artifacts.sh
PATH="$PWD/build/iree-smoke-venv/bin:$PATH" build/iree-smoke-venv/bin/python \
  scripts/check_iree_cnn_pipeline_readiness.py --require-host-tools \
  --json build/verification/iree-cnn-readiness-integration-20260509.json
./scripts/build_qbox_hexagon_firmware.sh
./scripts/build_qbox_linux_arm64.sh
./scripts/build_qbox_buildroot_platform.sh
QBOX_IREE_GUEST_ARTIFACTS_DIR="$PWD/build/iree-guest-artifacts/tiny-cnn" \
  ./scripts/build_qbox_buildroot_arm64.sh
./scripts/stage_buildroot_artifacts.sh
QBOX_IREE_GUEST_SMOKE_STAMP=20260509-integration-plugin-r2 \
  QBOX_BOOT_TIMEOUT=90 ./scripts/run_iree_tiny_cnn_qbox_guest_smoke.sh
QBOX_HEXAGON_GUEST_SMOKE_STAMP=20260509-integration-r3 \
  QBOX_BOOT_TIMEOUT=140 ./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh
./scripts/build_qbox_linux_arm64.sh
./scripts/build_qbox_buildroot_platform.sh
./scripts/stage_buildroot_artifacts.sh
QBOX_HEXAGON_GUEST_SMOKE_STAMP=20260509-arch-ptw \
  QBOX_IREE_LOGIN_DELAY=9 \
  QBOX_IREE_COMMAND_DELAY=2 \
  QBOX_IREE_AFTER_COMMAND_DELAY=12 \
  QBOX_BOOT_TIMEOUT=150 ./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh
```

## 요청 항목 대응표

| 요청 항목 | 현재 판정 | 근거/남은 일 |
| --- | --- | --- |
| Upstream IREE runtime에 동적으로 등록되는 C HAL plugin화 | 부분 완료, upstream 대기 | repo-local `dlopen()` plugin과 `iree_hal_executable_plugin_query` export/load는 검증됨. upstream IREE HAL driver registry/build/test 편입은 별도 과제. |
| 실제 ARM SMMUv3 architectural page-table walker, PRI/ATS/fault queue 전체 구현 | 부분 진행, full model 대기 | shared SRAM 4KB granule 4-level table descriptor chain fetch/decode probe는 추가됨. stream/context descriptor walk, architected ATS/PRI packet/replay, negative fault injection suite가 아직 필요. |
| 64KiB 초과 tensor, 다중 command queue, 비동기 interrupt/fence 모델 | 완료(기능 모델) | 128KiB/8 segment SG DMA, queue 0/1, async IRQ/fence marker가 guest smoke 대상으로 추가됨. |

## 경계 및 남은 주의점

- 이번 구현은 Apollo/QBox integration에 필요한 **functional SMMUv3 model**에
  architectural descriptor probe를 더한 상태다. Stream table/context descriptor를
  guest memory에서 모두 읽어 ARM SMMUv3 spec을 bit-exact하게 수행하는 full
  architectural compliance model은 아니다.
- ATS/PRI/fault queue는 driver/HAL integration 검증용 observable semantic model이다.
  PCIe ATS TLP, architected PRI packet, GIC-wired hardware interrupt delivery까지
  포함하는 완전한 IP 모델은 별도 범위다.
- IREE 쪽은 upstream executable plugin ABI와 dynamic C HAL plugin export/load를
  검증했다. Upstream IREE tree에 정식 HAL driver로 upstreaming하려면 build system,
  device registration, allocator/buffer model, async executor integration 설계가
  추가로 필요하다.

## 결론

repo-local functional integration 관점에서는 PASS다. A710 guest에서 Linux가
부팅되고, CPU IREE runtime과 Apollo Hexagon path 모두 tiny-CNN 출력 일치를 확인했다.
Hexagon path는 SMMU-translated TLM, architectural 4-level descriptor probe,
128KiB SG DMA, multi-queue, async fence marker를 동시에 통과하도록 확장했다.

단, upstream IREE HAL driver 등록과 bit-exact ARM SMMUv3 architectural model은
아직 완료가 아니며, 별도 upstream/architecture epic으로 추적해야 한다.
