# QBox SMMUv3 IRQ/MSI CFG Verification - 2026-05-10

## Scope

SMMU-COMP-070 MSI IRQ_CFG functional slice.

This slice adds a functional MSI model to the Apollo SMMUv3 TBU register
aperture. It covers `SMMU_GERROR_IRQ_CFG{0,1,2}`,
`SMMU_EVENTQ_IRQ_CFG{0,1,2}`, `SMMU_PRIQ_IRQ_CFG{0,1,2}`, `SMMU_IDR0.MSI`,
`CMD_SYNC` SIG_IRQ MSI writes, and architected MSI abort GERROR bits for CMDQ,
EVENTQ, PRIQ, and GERROR MSI sources.

This remains a functional compliance slice. It does not claim full GIC/MSI
routing, PCIe MSI fabric delivery, interrupt coalescing/order parity, Secure or
Realm MSI register banks, or upstream Linux `arm-smmu-v3` interrupt lifecycle
parity.

## Ground truth

- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
  lists the non-secure `*_IRQ_CFG{0,1,2}` offsets, the `IDR0.MSI` bit, and
  `CMD_SYNC(ComplSignal, MSIAddress, MSIData, MSIWriteAttributes)` SIG_IRQ MSI
  semantics.
- `sources/linux/drivers/iommu/arm/arm-smmu-v3/arm-smmu-v3.h` defines the same
  IRQ_CFG offsets, `IDR0_MSI`, `CMDQ_SYNC_0_CS`, and `GERROR_MSI_*_ABT_ERR`
  bit positions used as Linux-facing ABI reference points.
- `sources/smmu/SPEC_REVIEW.md` records that GERROR MSI abort bits are
  `MSI_CMDQ_ABT_ERR`, `MSI_EVENTQ_ABT_ERR`, `MSI_PRIQ_ABT_ERR`, and
  `MSI_GERROR_ABT_ERR`.

## Implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  adds `FEATURE_ARCH_IRQ_MSI_CFG`, advertises `ARCH_IDR0_MSI`, exposes MSI
  IRQ_CFG registers, emits memory-backed MSI writes through the downstream TLM
  port, and reports failed MSI writes through architected GERROR bits.
- `CMD_SYNC` with `CS=SIG_IRQ` emits the command-provided MSI write and reports
  failed writes through `ARCH_GERROR_MSI_CMDQ_ABORT`.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc` adds
  `MsiIrqCfgRegistersAreMaskedAndGuarded`,
  `MsiWritesAndAbortGerrorBitsFollowIrqSources`, and
  `CmdSyncMsiWriteAndAbortAreReported`.
- `sources/linux/drivers/soc/apollo/apollo-hexagon-test.c` requires
  `APOLLO_TBU_FEATURE_ARCH_IRQ_MSI_CFG` in the guest feature probe, expects the
  MSI-capable TBU `IDR0=0x0181a705`, and reads the private status register at
  `0x0e0` after the architected `PRI_IRQ_CFG` window.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh` gate the slice.

## Evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Component build | PASS | `build/verification/apollo-smmu-tbu-irq-msi-cfg-build-20260510.log`: `Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`. |
| Component CTest | PASS | `build/verification/apollo-smmu-tbu-irq-msi-cfg-ctest-20260510.log`: `100% tests passed, 0 tests failed out of 1`; tests cover IRQ_CFG guard/mask, EVENTQ/PRIQ MSI write/abort, and CMD_SYNC MSI write/abort. |
| Linux build | PASS | `build/verification/qbox-linux-smmu-irq-msi-cfg-20260510.log`: `Linux Image: /build/qbox_dev/build/linux-a710/arch/arm64/boot/Image`. |
| Artifact staging | PASS | `build/verification/stage-artifacts-smmu-irq-msi-cfg-20260510.log`: `Staged Linux + Buildroot artifacts into /build/qbox_dev/sources/qbox/platforms/buildroot/fw/Artifacts`. |
| Platform build | PASS | `build/verification/qbox-platform-smmu-irq-msi-cfg-20260510.log`: `QBox Buildroot platform runtime built in /build/qbox_dev/sources/qbox/build`. |
| Guest smoke | PASS | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-irq-msi-cfg.driver.log`: `PASS: QBox guest IREE Hexagon tiny-CNN output matched`; runtime log records `features=0x7ffffff`, `idr0=0x180a305`, and `1x1x2x2xf32=[[[54 63][90 99]]]`. |
| Static/checker/lane | PASS | `build/verification/smmu-irq-msi-cfg-static-final-20260510.log`: `PASS  tbu:irq-msi-cfg`, `SUMMARY {"pass": 281}`, and lane check passed. |

## Remaining blockers

- Real PCIe/GIC MSI routing and interrupt-controller injection are still not
  implemented.
- MSI ordering/coalescing against queue visibility is only component-modeled.
- Secure and Realm IRQ/MSI register banks are out of scope for this slice.
- Upstream Linux `arm-smmu-v3` interrupt allocation and recovery lifecycle parity
  remains open.
