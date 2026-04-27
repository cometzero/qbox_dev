# Apollo Hexagon SMMU-translated TLM DMA 검증 리포트

- 날짜: 2026-04-28
- 결과: **PASS**
- 대상: `apollo-qbox`에서 Hexagon firmware-triggered DMA를 direct router
  path가 아닌 `SMMU-translated TLM path`로 실행

## 구현 요약

이번 변경은 Hexagon DMA transaction 자체가 QBox router에 직접 연결되지 않고
전용 translated data-plane bridge를 통과하도록 구성했다.

```text
Hexagon firmware
  -> apollo_hexagon_dma MMIO
  -> apollo_hexagon_dma.translated_dma
  -> apollo_smmu_tbu.upstream
  -> IOVA window translation
  -> apollo_smmu_tbu.downstream
  -> QBox router
  -> SRAM
```

주요 변경점:

- `sources/qbox/systemc-components/apollo_smmu_tbu/`
  - 신규 functional TBU bridge 추가.
  - StreamID `0x1`과 IOVA window를 CCI parameter로 받는다.
  - IOVA `0x10000000..0x105fffff`를 PA `0x00a00000..0x00ffffff`로
    base/offset 변환한다.
  - window 밖 접근은 `TLM_ADDRESS_ERROR_RESPONSE`로 반환한다.
- `sources/qbox/platforms/buildroot/conf_aarch64.lua`
  - `hexagon_dma_0.translated_dma`를 `hexagon_smmu_tbu_0.upstream`에 bind.
  - `smmu_translated = true`로 전환.
  - `hexagon_smmu_tbu_0.downstream`을 router target socket에 bind.
- `sources/qbox/platforms/buildroot/fw/hexagon_dma_smoke.s`
  - firmware DMA source/destination을 PA가 아닌 IOVA로 변경.
  - source: `0x10201000` -> translated PA `0x00c01000`.
  - destination: `0x10000000` -> translated PA `0x00a00000`.
- `configs/linux/apollo_soc.dts`
  - `apollo,dma-path = "smmu-translated"`로 변경.
  - IOVA base/window property 추가.
- `sources/linux/drivers/soc/apollo/apollo-hexagon-test.c`
  - device model path와 DT `apollo,dma-path` mismatch를 probe 실패로 처리.
  - translated path 확인 로그에 `smmuv3-translated=yes` 명시.
- `scripts/check_buildroot_arm64_lane.sh`
  - translated path static contract와 runtime module checks 추가.

## 검증 명령 및 결과

| 항목 | 결과 | 증거 |
| --- | --- | --- |
| Shell/static lint | PASS | `git diff --check`, submodule `diff --check`, `bash -n scripts/*.sh` |
| Lane contract | PASS | `build/verification/static-smmu-translated-contract-20260428-001716.log` |
| Linux rebuild | PASS | `build/verification/linux-build-smmu-translated-20260428-001621.log` |
| QBox runtime rebuild | PASS | `build/verification/qbox-platform-smmu-translated-fix-20260428-001709.log` |
| Artifact staging | PASS | `build/verification/stage-smmu-translated-20260428-001807.log` |
| Boot + DMA smoke | PASS | `build/verification/qbox-boot-hexagon-smmu-translated-20260428-001817.log` |
| Marker/negative scan | PASS | `build/verification/markers-smmu-translated-20260428-001937.log` |

Boot 실행 명령:

```bash
QBOX_BOOT_TIMEOUT=60 \
QBOX_BOOT_HOSTFWD=off \
QBOX_BOOT_LOG=build/verification/qbox-boot-hexagon-smmu-translated-20260428-001817.log \
  ./scripts/run_qbox_buildroot_boot.sh
```

`BOOT_RC=124`는 60초 timeout으로 login prompt 이후 종료된 값이며, 아래 모든
성공 marker가 확인되어 PASS로 판정했다.

## 핵심 boot marker

```text
APOLLO_HEXAGON_DMA: firmware requested DMA src=0x10201000 dst=0x10000000 len=0x20
APOLLO_HEXAGON_DMA: path=smmu-translated stream-id=0x1 caps=0x5
APOLLO_SMMU_TBU: stream-id=0x1 translate read iova=0x10201000 pa=0xc01000 len=0x20
APOLLO_SMMU_TBU: stream-id=0x1 translate write iova=0x10000000 pa=0xa00000 len=0x20
APOLLO_HEXAGON_DMA: DMA copy complete src=0x10201000 dst=0x10000000 len=0x20 first=0x48455831
APOLLO_HEXAGON_DMA: firmware done magic=0x48455844
arm-smmu-v3 1c200000.iommu: oas 44-bit
platform 1c220000.hexagon: Adding to iommu group 0
apollo-hexagon-test 1c220000.hexagon: dma path smmu-translated caps=0x5 stream-id=0x1 smmuv3-translated=yes
apollo-hexagon-test 1c220000.hexagon: iommu group attached
apollo-hexagon-test 1c220000.hexagon: firmware dma traffic ok dst=0x0000000000a00000 words=8 first=0x48455831
apollo-hexagon-test 1c220000.hexagon: dma selftest ok
apollo-hexagon-test 1c220000.hexagon: probe ok
Run /sbin/init as init process
apollo-qbox login:
```

## Negative marker scan

다음 direct/fault/error marker는 모두 absent로 확인했다.

```text
APOLLO_HEXAGON_DMA: path=direct-tlm
smmuv3-translated=no
APOLLO_HEXAGON_DMA: DMA transaction failed
RESULT_TLM_ERROR
firmware dma traffic timeout
unsupported DMA path
stream-id mismatch
DMA path mismatch
iommu group unavailable
APOLLO_SMMU_TBU: translation fault
Kernel panic / Call trace / Oops / BUG
```

## 범위와 남은 한계

이번 결과는 **direct-TLM 우회가 아닌 SMMU-translated TLM data path**를
검증한다. 다만 QBox `arm_smmuv3` wrapper는 현재 MMIO/IRQ control-plane
모델이고 custom DMA traffic용 upstream/downstream TLM data-plane socket을
제공하지 않는다. 따라서 실제 data-plane 변환은 Apollo 전용 functional TBU인
`apollo_smmu_tbu`가 담당한다.

남은 확장 항목:

- `apollo_smmu_tbu`는 fixed-window translator이며 page table, ATS/PRI,
  SMMUv3 event queue fault model은 아직 없다.
- native Hexagon `dmlink`/`dmwait` descriptor engine 자체를 모델링한 것은
  아니며, firmware-programmed SystemC DMA engine smoke 단계다.
- production reset/power/mailbox/doorbell ABI는 후속 작업이다.
