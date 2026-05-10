# QBox Apollo IREE Hexagon 제품화 baseline 구현/검증 리포트

- 날짜: 2026-05-09
- 대상: `/build/qbox_dev`
- 목표: 기존 functional Hexagon offload를 제품화 가능한 repo-local baseline으로
  확장하고, QBox guest에서 CNN 결과와 multi-page DMA/SMMU marker를 검증한다.

## 결론

PASS. Apollo Hexagon offload 경로는 다음 제품화 baseline을 만족한다.

1. Guest HAL runner는 VMFB metadata loader, command buffer, synchronous queue,
   host-poll fence 구조를 가진다.
2. Linux `/dev/apollo-hexagon` ABI는 CNN submit 외에 8KB scatter/gather DMA
   stress ioctl을 제공한다.
3. QBox `apollo_smmu_tbu`는 dynamic map/unmap/clear와 multi-page TLM split을
   지원한다.
4. Hexagon firmware는 tiny CNN job과 DMA copy stress job을 모두 처리한다.
5. Booted guest smoke에서 SG DMA stress, CNN output, SMMU translated read/write
   marker가 모두 확인됐다.

이번 완료 범위는 **repo-local productization baseline**이다. Upstream IREE C HAL
plugin 병합 및 full architectural ARM SMMUv3 page-table walker/fault queue 구현은
별도 upstream/architecture integration 과제로 경계를 명확히 했다.

## 구현 요약

| 영역 | 구현 파일 | 내용 |
| --- | --- | --- |
| Guest HAL | `configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_hexagon_hal.c` | metadata load, queue open, CNN submit, SG DMA stress submit, fence signal |
| Guest runner | `.../apollo_iree_hexagon_runner.c` | command buffer 구성, stress 후 CNN 실행, IREE-like output 출력 |
| Guest UAPI | `.../apollo_hexagon_uapi_guest.h` | guest build용 ioctl ABI mirror |
| Linux UAPI | `sources/linux/include/uapi/linux/apollo_hexagon.h` | `APOLLO_HEXAGON_IOC_DMA_STRESS` 추가 |
| Linux driver | `sources/linux/drivers/soc/apollo/apollo-hexagon-test.c` | 8KB/2-segment SG mapping, checksum verify, ioctl dispatch |
| QBox TBU | `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h` | `MAP_CTRL_CLEAR`, segment translation, multi-page split |
| QBox DMA | `sources/qbox/systemc-components/apollo_hexagon_dma/include/apollo_hexagon_dma.h` | max DMA length 64KB |
| Hexagon firmware | `sources/qbox/platforms/buildroot/fw/hexagon_dma_smoke.s` | `dma_copy_job`, `SGOK` result, CNN job 유지 |
| Staging/smoke | `scripts/stage_iree_tiny_cnn_guest_artifacts.sh`, `scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh` | metadata staging 및 marker 기반 자동 검증 |

## 검증 명령

```bash
./scripts/build_qbox_hexagon_firmware.sh
./scripts/build_apollo_hexagon_guest_tools.sh
./scripts/build_qbox_linux_arm64.sh
./scripts/build_qbox_buildroot_platform.sh
./scripts/stage_iree_tiny_cnn_guest_artifacts.sh
QBOX_IREE_GUEST_ARTIFACTS_DIR=/build/qbox_dev/build/iree-guest-artifacts/tiny-cnn \
  ./scripts/build_qbox_buildroot_arm64.sh
./scripts/stage_buildroot_artifacts.sh
bash -n scripts/*.sh configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/post-build.sh
python3 -m py_compile scripts/check_iree_cnn_pipeline_readiness.py scripts/qbox_pty_runner.py
./scripts/check_buildroot_arm64_lane.sh
./scripts/check_iree_cnn_pipeline_readiness.py --require-host-tools
QBOX_HEXAGON_GUEST_SMOKE_STAMP=20260509-productization \
QBOX_IREE_LOGIN_DELAY=9 \
QBOX_IREE_COMMAND_DELAY=2 \
QBOX_IREE_AFTER_COMMAND_DELAY=12 \
QBOX_BOOT_TIMEOUT=90 \
  ./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh
```

## 증거 로그

- Linux build: `build/verification/linux-productization-20260509-productization.log`
- QBox platform build:
  `build/verification/qbox-platform-productization-20260509-productization.log`
- IREE/Hexagon artifact staging:
  `build/verification/stage-iree-productization-20260509-productization.log`
- Buildroot rootfs:
  `build/verification/buildroot-productization-20260509-productization.log`
- Artifact staging: `build/verification/stage-productization-20260509-productization.log`
- Lane contract:
  `build/verification/check-buildroot-arm64-lane-productization-20260509.log`
- IREE readiness:
  `build/verification/iree-cnn-readiness-productization-20260509.txt`
- QBox guest smoke:
  `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260509-productization.log`
- QBox boot log:
  `build/verification/qbox-iree-tiny-cnn-hexagon-guest-boot-20260509-productization.log`

## 핵심 runtime 출력

```text
IREE Apollo Hexagon HAL: executable=/opt/qbox/iree/tiny-cnn/tiny_cnn_aarch64.vmfb entry=tiny_cnn_graph bytes=9285
IREE Apollo Hexagon HAL: queue=sync command-buffer=fixed fence=host-poll
APOLLO_SMMU_TBU: clear stream-id=0x1 removed=0 active=0
APOLLO_SMMU_TBU: map stream-id=0x1 iova=0x10020000 pa=0xa20000 len=0x1000 active=1
APOLLO_SMMU_TBU: map stream-id=0x1 iova=0x10021000 pa=0xa22000 len=0x1000 active=2
APOLLO_SMMU_TBU: map stream-id=0x1 iova=0x10040000 pa=0xa40000 len=0x1000 active=3
APOLLO_SMMU_TBU: map stream-id=0x1 iova=0x10041000 pa=0xa42000 len=0x1000 active=4
APOLLO_HEXAGON_DMA: firmware requested DMA src=0x10020000 dst=0x10040000 len=0x2000
APOLLO_SMMU_TBU: stream-id=0x1 translate read iova=0x10020000 pa=0xa20000 len=0x1000
APOLLO_SMMU_TBU: stream-id=0x1 translate read iova=0x10021000 pa=0xa22000 len=0x1000
APOLLO_SMMU_TBU: stream-id=0x1 translate write iova=0x10040000 pa=0xa40000 len=0x1000
APOLLO_SMMU_TBU: stream-id=0x1 translate write iova=0x10041000 pa=0xa42000 len=0x1000
APOLLO_HEXAGON_DMA: DMA copy complete src=0x10020000 dst=0x10040000 len=0x2000 first=0x8d60e266
apollo-hexagon-test 1c220000.hexagon: SG DMA stress ok bytes=8192 segments=2 checksum=0x01954000 status=0x53474f4b
IREE Apollo Hexagon HAL: SG DMA stress ok bytes=8192 segments=2 checksum=0x01954000
IREE Apollo Hexagon HAL: command buffer submitted
IREE Apollo Hexagon HAL: offload complete status=0x434e4e4f
IREE Apollo Hexagon HAL: fence signaled status=0x434e4e4f
EXEC @tiny_cnn_graph [apollo-hexagon]
1x1x2x2xf32=[[[54 63][90 99]]]
PASS: QBox guest IREE Hexagon tiny-CNN output matched
```

## 남은 별도 integration 과제

- Upstream IREE runtime에 동적으로 등록되는 C HAL plugin화.
- 실제 ARM SMMUv3 architectural page-table walker, PRI/ATS/fault queue 전체 구현.

## 후속 integration에서 확장된 항목

- 64KiB 초과 tensor, 다중 command queue, 비동기 interrupt/fence 모델은 후속
  integration pass에서 128KiB/8 segment SG DMA, queue 0/1, async fence marker로
  확장했다.
- SMMUv3는 후속 integration pass에서 shared SRAM 4-level table descriptor chain을 TBU가 downstream
  TLM으로 fetch/decode하는 architectural descriptor-walk probe까지 확장했다.
  자세한 근거는 `doc/verification/qbox-iree-hexagon-integration-2026-05-09.md`를
  참조한다.
