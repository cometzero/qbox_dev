# Apollo Hexagon direct-TLM DMA 수정 및 검증 리포트 (2026-04-27)

## 결론

PASS. Apollo QBox의 현재 Hexagon DMA 경로는 의도한 대로
`direct-tlm` 경로에서 동작하는 것을 재확인했다. Hexagon firmware가
`apollo_hexagon_dma` MMIO register를 program하고, QBox SystemC DMA 엔진이
router의 direct TLM socket으로 Hexagon SRAM `0x00C01000`에서 shared SRAM
`0x00A00000`으로 32 bytes를 복사했다. Linux `apollo-hexagon-test` driver도
동일 payload를 확인하고 probe를 완료했다.

## 수정 사항

- `sources/qbox/systemc-components/apollo_hexagon_dma/include/apollo_hexagon_dma.h`
  - direct-TLM read/write transaction 실패 시 `STATUS_DONE/RESULT_OK`로
    덮어쓰지 않도록 `do_dma()`가 `bool`을 반환하게 변경했다.
  - TLM transaction 실패 결과 코드 `RESULT_TLM_ERROR = 0xbad00002`를
    추가했다.
  - 실패 시 `APOLLO_HEXAGON_DMA: DMA transaction failed ...` 로그를 남기고
    DMA completion path를 중단하도록 했다.
- `scripts/check_buildroot_arm64_lane.sh`
  - direct-TLM error result와 실패 전파 경로가 유지되는지 정적 계약
    검증을 추가했다.
- `doc/hardware/hw_architecture.md`
  - `RESULT` register 설명에 성공/실패 값을 반영했다.

## 검증 명령

```bash
git diff --check
git -C sources/qbox diff --check
bash -n scripts/check_buildroot_arm64_lane.sh \
  scripts/build_qbox_buildroot_platform.sh \
  scripts/run_qbox_buildroot_boot.sh
./scripts/check_buildroot_arm64_lane.sh
./scripts/build_qbox_buildroot_platform.sh
./scripts/stage_buildroot_artifacts.sh
QBOX_BOOT_TIMEOUT=60 QBOX_BOOT_HOSTFWD=off \
  QBOX_BOOT_LOG=build/verification/qbox-boot-direct-tlm-fix-2026-04-27-235512.log \
  ./scripts/run_qbox_buildroot_boot.sh
```

`QBOX_BOOT_TIMEOUT=60`로 실행했기 때문에 boot wrapper의 반환값
`BOOT_RC=124`는 login prompt 확인 후 timeout으로 종료된 기대값이다.

## 증거 로그

| 항목 | 결과 | 로그 |
| --- | --- | --- |
| QBox platform rebuild | PASS | `build/verification/qbox-platform-direct-tlm-fix-2026-04-27-235400.log` |
| Artifact staging | PASS | `build/verification/stage-direct-tlm-fix-2026-04-27-235508.log` |
| Apollo boot + direct-TLM DMA | PASS | `build/verification/qbox-boot-direct-tlm-fix-2026-04-27-235512.log` |
| Marker check / error scan | PASS | `build/verification/static-direct-tlm-fix-2026-04-27-235624.log` |

핵심 runtime marker:

```text
APOLLO_HEXAGON_DMA: firmware requested DMA src=0xc01000 dst=0xa00000 len=0x20
APOLLO_HEXAGON_DMA: path=direct-tlm stream-id=0x1 caps=0x3
APOLLO_HEXAGON_DMA: DMA copy complete src=0xc01000 dst=0xa00000 len=0x20 first=0x48455831
APOLLO_HEXAGON_DMA: firmware done magic=0x48455844
apollo-hexagon-test 1c220000.hexagon: dma path direct-tlm caps=0x3 stream-id=0x1 smmuv3-translated=no
apollo-hexagon-test 1c220000.hexagon: iommu group attached
apollo-hexagon-test 1c220000.hexagon: firmware dma traffic ok dst=0x0000000000a00000 words=8 first=0x48455831
apollo-hexagon-test 1c220000.hexagon: dma selftest ok dma=0x0000fffffffff000 size=4096
apollo-hexagon-test 1c220000.hexagon: probe ok
Run /sbin/init as init process
apollo-qbox login:
```

Error scan 결과:

```text
No direct-TLM error markers found
```

## 현재 범위와 남은 일

- 이번 검증 범위는 현재 Apollo runtime의 **direct-TLM DMA path**이다.
- `smmuv3-translated=no`가 의도된 현재 상태다. 즉, Linux SMMUv3 probe와
  IOMMU group attach는 확인되지만, firmware-triggered custom DMA transaction
  자체는 아직 SMMUv3 translation datapath를 통과하지 않는다.
- 향후 `smmu_translated=true`로 전환하려면 QBox `arm_smmuv3`와
  `apollo_hexagon_dma` 사이에 실제 data-plane TLM bridge/socket wiring이
  추가되어야 한다.
