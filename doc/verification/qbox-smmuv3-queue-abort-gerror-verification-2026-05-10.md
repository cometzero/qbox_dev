# QBox SMMUv3 Queue Abort GERROR Verification - 2026-05-10

## Scope

SMMU-COMP-020/050/060/070 EVENTQ/PRIQ queue abort GERROR functional slice.

This slice replaces the previous output-queue write-abort fallback path that
reused command-queue global-error signalling for EVENTQ/PRIQ record write
failures. Failed writes to the Event queue now report the architected
`SMMU_GERROR.EVENTQ_ABT_ERR` bit, and failed writes to the PRI queue now report
`SMMU_GERROR.PRIQ_ABT_ERR`. The existing compatibility overflow bit remains
only for the earlier OVFLG/OVACKFLG overflow slice.

This is still a functional compliance slice. It does not implement MSI abort
reporting, GIC/MSI delivery ordering, byte-exact queue access attributes, or the
full upstream Linux `arm-smmu-v3` interrupt recovery lifecycle.

## Ground truth

- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
  section 6.3.19 defines `SMMU_GERROR.EVENTQ_ABT_ERR` at bit 2 as an
  abort-terminated access to the Event queue.
- The same section defines `SMMU_GERROR.PRIQ_ABT_ERR` at bit 3 as an
  abort-terminated access to the PRI queue.
- Section 6.3.20 applies the same fields to `SMMU_GERRORN`, where software
  acknowledges active global errors by matching the corresponding GERROR bit.

## Implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  adds `ARCH_GERROR_EVENTQ_ABORT` and `ARCH_GERROR_PRIQ_ABORT` to the known
  GERROR mask.
- `push_arch_queue_record()` now receives the queue-specific abort GERROR bit.
  EVENTQ writes pass `ARCH_GERROR_EVENTQ_ABORT`; PRIQ writes pass
  `ARCH_GERROR_PRIQ_ABORT`.
- Failed downstream queue writes leave the producer index unchanged, set the
  queue-specific architected GERROR bit, raise the GERROR IRQ status, and log an
  architected queue abort record.
- `sources/linux/drivers/soc/apollo/apollo-hexagon-test.c` mirrors the
  architected EVENTQ/PRIQ abort bits in the known GERROR mask so Linux-side
  active-error decoding stays aligned with the TBU model.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc` adds
  `EventAndPriQueueWriteAbortUseArchitectedGerrorBits`.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh` gate the slice.

## Evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Component build | PASS | `build/verification/apollo-smmu-tbu-queue-abort-gerror-build-20260510.log`: `Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`. |
| Component CTest | PASS | `build/verification/apollo-smmu-tbu-queue-abort-gerror-ctest-20260510.log`: `100% tests passed, 0 tests failed out of 1`; `EventAndPriQueueWriteAbortUseArchitectedGerrorBits` verifies EVENTQ_ABT_ERR and PRIQ_ABT_ERR active-bit acknowledgement. |
| Static/checker/lane | PASS | `build/verification/smmu-queue-abort-gerror-static-final-20260510.log`: `PASS  tbu:queue-write-abort-gerror`, `SUMMARY {"pass": 267}`, and `Lane conclusion: Buildroot owns rootfs/DTB generation only; Linux Image comes from sources/linux, and libqemu comes from sources/qemu.` |
| Linux build | PASS | `build/verification/qbox-linux-smmu-queue-abort-gerror-20260510.log`: `Linux Image: /build/qbox_dev/build/linux-a710/arch/arm64/boot/Image`. |
| Artifact stage | PASS | `build/verification/stage-artifacts-smmu-queue-abort-gerror-20260510.log`: `Staged Linux + Buildroot artifacts into /build/qbox_dev/sources/qbox/platforms/buildroot/fw/Artifacts`. |
| Platform build | PASS | `build/verification/qbox-platform-smmu-queue-abort-gerror-20260510.log`: `QBox Buildroot platform runtime built in /build/qbox_dev/sources/qbox/build`. |
| Guest smoke | PASS | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-queue-abort-gerror.driver.log`: `PASS: QBox guest IREE Hexagon tiny-CNN output matched`; runtime log records `features=0xffffff` and `1x1x2x2xf32=[[[54 63][90 99]]]`. |

## Remaining blockers

- MSI abort bits (`MSI_CMDQ_ABT_ERR`, `MSI_EVENTQ_ABT_ERR`,
  `MSI_PRIQ_ABT_ERR`, `MSI_GERROR_ABT_ERR`) are not modeled.
- Full GIC/MSI delivery, ordering, and visibility guarantees are still open.
- Full Linux `arm-smmu-v3` queue-abort recovery is not wired to real IRQs.
- EVENTQ stall re-drive and PRIQ packet-level protocol completion remain future
  slices.
