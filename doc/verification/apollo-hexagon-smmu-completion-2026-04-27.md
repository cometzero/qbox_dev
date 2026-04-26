# Apollo Hexagon SMMU/DMA Completion Report (2026-04-27)

## Result

PASS for the current Apollo QBox boot target:

- QBox launches real Hexagon firmware from `apollo_hexagon_dma.bin`.
- The firmware issues DMA traffic into the shared SRAM test buffer.
- Linux boots on the Apollo A710 cluster, probes the Hexagon device behind
  SMMUv3, verifies the DMA path ABI, and confirms the firmware DMA payload.
- The standalone QBox Hexagon SMMU reference test still builds and one
  representative runtime test passes.

Scope boundary: the Apollo custom DMA datapath is currently verified as
`direct-tlm`, not as an SMMUv3-translated custom TLM datapath. The QBox
`arm_smmuv3` component currently exposes register/IRQ integration, but no
stable generic downstream/upstream TLM data-plane socket that can be safely
inserted between `apollo_hexagon_dma` and DRAM. This pass therefore adds a
truthful boot-safe ABI and an opt-in translated-path seam instead of claiming
translation that is not wired.

## Implementation Summary

- `sources/qbox/systemc-components/apollo_hexagon_dma/include/apollo_hexagon_dma.h`
  - Added Linux-visible DMA capability/path/StreamID registers.
  - Added `stream_id` and `smmu_translated` CCI parameters.
  - Added a zero-or-more-bound `translated_dma` initiator socket as the future
    translated-path seam without breaking the current direct boot path.
  - Logs `APOLLO_HEXAGON_DMA: path=direct-tlm stream-id=0x1 caps=0x3` during
    firmware DMA execution.
- `sources/qbox/platforms/buildroot/conf_aarch64.lua`
  - Sets `APOLLO_HEXAGON_STREAM_ID = 0x1`.
  - Keeps `smmu_translated = false` for the current truthful direct path.
- `sources/linux/drivers/soc/apollo/apollo-hexagon-test.c`
  - Reads and validates DMA caps/path/StreamID from the QBox device model.
  - Logs `dma path direct-tlm ... smmuv3-translated=no` before DMA tests.
- `configs/linux/apollo_soc.dts`
  - Documents the current DMA path and StreamID in DT.
- `scripts/check_buildroot_arm64_lane.sh`
  - Locks the DTS, Linux driver, QBox platform, and QBox DMA model contract.

## Verification Evidence

| Check | Result | Evidence |
| --- | --- | --- |
| QBox platform rebuild | PASS | `build/verification/qbox-platform-dma-path-optional-socket-2026-04-27-000417.log` |
| Linux standalone rebuild | PASS | `build/verification/linux-dma-path-abi-2026-04-27-000417.log` |
| Artifact staging | PASS | `build/verification/stage-dma-path-abi-2026-04-27-000525.log` |
| Static contract checks | PASS | `build/verification/static-dma-path-2026-04-27-000541.log` |
| Hexagon SMMU preflight/build | PASS | `build/verification/hexagon-smmu-reference-dma-path-2026-04-27-000541.log` |
| Hexagon SMMU runtime sample | PASS | `build/verification/hexagon-smmu-reference-runtime-2026-04-27-000609.log` |
| Apollo boot + firmware DMA | PASS | `build/verification/qbox-boot-dma-path-abi-2026-04-27-000621.log` |

Boot evidence highlights from
`build/verification/qbox-boot-dma-path-abi-2026-04-27-000621.log`:

```text
APOLLO_HEXAGON_DMA: path=direct-tlm stream-id=0x1 caps=0x3
arm-smmu-v3 1c200000.iommu: oas 44-bit (features 0x01008305)
platform 1c220000.hexagon: Adding to iommu group 0
apollo-hexagon-test 1c220000.hexagon: dma path direct-tlm caps=0x3 stream-id=0x1 smmuv3-translated=no
apollo-hexagon-test 1c220000.hexagon: iommu group attached
apollo-hexagon-test 1c220000.hexagon: firmware dma traffic ok dst=0x0000000000a00000 words=8 first=0x48455831
apollo-hexagon-test 1c220000.hexagon: dma selftest ok dma=0x0000fffffffff000 size=4096
apollo-hexagon-test 1c220000.hexagon: probe ok
Run /sbin/init as init process
apollo-qbox login:
```

`BOOT_RC=124` is expected for this bounded smoke run because the QBox process
was intentionally stopped by `QBOX_BOOT_TIMEOUT=60` after the login prompt.

## Remaining Follow-up

To turn `smmu_translated=true`, QBox needs a real SMMUv3 data-plane bridge or a
component API exposing suitable TLM initiator/target sockets on `arm_smmuv3`.
Until that exists, the direct path must remain explicit in DTS, Linux logs, and
QBox platform configuration.
