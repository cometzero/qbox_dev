# QBox Apollo IREE Hexagon offload 구현/검증 리포트

- 날짜: 2026-05-09
- 대상: `/build/qbox_dev`
- 목표: Apollo QBox에서 Hexagon accelerator functional offload path를 구성하고
  tiny CNN output이 `1x1x2x2xf32=[[[54 63][90 99]]]`와 일치하는지 검증한다.

## 결론

PASS. A710 Linux guest에서 `/dev/apollo-hexagon` ioctl submit ABI를 통해
Hexagon job을 제출하고, QBox SMMU TBU dynamic map/unmap 경로를 거쳐 Hexagon
firmware CNN kernel/runtime이 DMA input/output traffic을 수행했다. Guest의
IREE-compatible Apollo Hexagon HAL runner shim은 최종 tensor를 IREE
`iree-run-module` 유사 출력 형식으로 표시했고 expected tensor와 일치했다.

이번 구현은 **functional HAL runner shim**이다. 즉, guest IREE runtime에 upstream
IREE C HAL plugin으로 동적 등록되는 형태는 아니지만, IREE pipeline의 tiny CNN
fixture를 Apollo Hexagon device path로 submit하고 결과를 검증하는 repo-local
offload baseline은 완료했다.

## 구현 내용

| 영역 | 구현 |
| --- | --- |
| Linux userspace ABI | `sources/linux/include/uapi/linux/apollo_hexagon.h` 및 `/dev/apollo-hexagon` miscdevice ioctl |
| Linux driver | `APOLLO_HEXAGON_IOC_SUBMIT_CNN`, shared SRAM input/output staging, completion polling |
| Dynamic SMMU | `apollo_smmu_tbu` register window, map/unmap control, active map count, translation fault 유지 |
| QBox platform | TBU dynamic register window를 `APOLLO_HEXAGON_CTRL + 0x1000`에 배치 |
| Hexagon DMA/job regs | job input/output/size/control/status/result registers 추가 |
| Hexagon firmware | boot DMA smoke 후 job loop 진입, DMA input copy, tiny CNN kernel, DMA output copy |
| Guest HAL runner | `apollo-iree-hexagon-runner`가 ioctl submit 후 IREE-like tensor output 출력 |
| Guest smoke | `scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh` 자동 검증 |

## 검증 명령

```bash
./scripts/build_qbox_linux_arm64.sh
./scripts/build_qbox_buildroot_platform.sh
./scripts/stage_iree_tiny_cnn_guest_artifacts.sh
QBOX_IREE_GUEST_ARTIFACTS_DIR=/build/qbox_dev/build/iree-guest-artifacts/tiny-cnn \
  ./scripts/build_qbox_buildroot_arm64.sh
./scripts/stage_buildroot_artifacts.sh
QBOX_IREE_LOGIN_DELAY=9 \
QBOX_IREE_COMMAND_DELAY=2 \
QBOX_IREE_AFTER_COMMAND_DELAY=12 \
QBOX_BOOT_TIMEOUT=80 \
  ./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh
```

## 증거 로그

- Linux rebuild: `build/verification/linux-hexagon-offload-20260509-175529.log`
- QBox platform rebuild:
  `build/verification/qbox-platform-hexagon-offload-20260509-175610.log`
- IREE/Hexagon guest artifact staging:
  `build/verification/stage-iree-hexagon-artifacts-20260509-175716.log`
- Buildroot rootfs:
  `build/verification/buildroot-hexagon-offload-20260509-175728.log`
- Artifact staging:
  `build/verification/stage-hexagon-offload-20260509-175742.log`
- QBox Hexagon guest smoke:
  `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260509-175746.log`
- QBox boot log:
  `build/verification/qbox-iree-tiny-cnn-hexagon-guest-boot-20260509-175746.log`
- 최종 lane contract 재검증:
  `build/verification/check-buildroot-arm64-lane-hexagon-offload-20260509.log`
- 최종 IREE readiness 재검증:
  `build/verification/iree-cnn-readiness-hexagon-offload-20260509.txt`
- 최종 QBox Hexagon guest smoke 재실행:
  `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260509-180435.log`
- 최종 QBox boot log 재실행:
  `build/verification/qbox-iree-tiny-cnn-hexagon-guest-boot-20260509-180435.log`

## 핵심 runtime 출력

```text
APOLLO_SMMU_TBU: map stream-id=0x1 iova=0x10000000 pa=0xa00000 len=0x600000 active=1
APOLLO_SMMU_TBU: unmap stream-id=0x1 iova=0x10000000 pa=0xa00000 len=0x600000 active=0
APOLLO_SMMU_TBU: map stream-id=0x1 iova=0x10000000 pa=0xa00000 len=0x600000 active=1
APOLLO_HEXAGON_DMA: firmware requested DMA src=0x10010000 dst=0x10202000 len=0x40
APOLLO_SMMU_TBU: stream-id=0x1 translate read iova=0x10010000 pa=0xa10000 len=0x40
APOLLO_SMMU_TBU: stream-id=0x1 translate write iova=0x10202000 pa=0xc02000 len=0x40
APOLLO_HEXAGON_DMA: firmware requested DMA src=0x10203000 dst=0x10011000 len=0x10
APOLLO_SMMU_TBU: stream-id=0x1 translate read iova=0x10203000 pa=0xc03000 len=0x10
APOLLO_SMMU_TBU: stream-id=0x1 translate write iova=0x10011000 pa=0xa11000 len=0x10
apollo-hexagon-test 1c220000.hexagon: accelerator tiny cnn ok status=0x434e4e4f out=42580000,427c0000,42b40000,42c60000
IREE Apollo Hexagon HAL: offload complete status=0x434e4e4f
EXEC @tiny_cnn_graph [apollo-hexagon]
result[0]: hal.buffer_view
1x1x2x2xf32=[[[54 63][90 99]]]
PASS: QBox guest IREE Hexagon tiny-CNN output matched
```

## 남은 제품화 과제

1. Functional HAL runner shim을 upstream IREE C HAL plugin/driver 구조로 전환.
2. VMFB executable loader, command buffer, queue, fence/synchronization 모델 확장.
3. TBU functional map/unmap을 실제 SMMUv3 page-table walker/fault queue 모델로 확장.
4. 4KB 초과 tensor, scatter/gather, multi-page DMA, cache coherency stress test 추가.
