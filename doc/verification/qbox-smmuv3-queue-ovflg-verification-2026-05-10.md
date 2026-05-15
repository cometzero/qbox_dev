# QBox SMMUv3 Output Queue OVFLG Verification - 2026-05-10

## Scope

SMMU-COMP-020/050/060 EVENTQ/PRIQ OVFLG/OVACKFLG functional slice.

This slice models architected output queue overflow flags for the Apollo TBU
SMMUv3 aperture. On EVENTQ/PRIQ overflow the TBU now toggles the producer
`OVFLG` bit once while the overflow remains unacknowledged, exposes that bit via
`SMMU_EVENTQ_PROD` or `SMMU_PRIQ_PROD`, and clears the internal overflow state
when software writes the matching `OVACKFLG` value through the corresponding
consumer register.

This is still a functional compliance slice. It does not claim byte-exact Event
or PRI queue layout parity, complete stall re-drive, PCIe packet-level PRI
responses, MSI delivery, or full upstream `arm-smmu-v3` lifecycle parity.

## Ground truth

- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
  section 7.4 says Event queue overflow is present when
  `SMMU_EVENTQ_PROD.OVFLG != SMMU_EVENTQ_CONS.OVACKFLG`, and that the SMMU
  toggles `OVFLG` only when the overflow condition is not already present.
- The same reference says software acknowledges overflow by writing the matching
  `OVACKFLG` value in the consumer register.
- Section 8.1 applies the same `OVFLG`/`OVACKFLG` protocol to PRI queue
  overflow.

## Implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  adds `FEATURE_ARCH_QUEUE_OVERFLOW_FLAGS`, `ARCH_QUEUE_OVFLG`, per-queue
  `ovflg`/`ovackflg` state, `queue_prod_reg()`, `queue_cons_reg()`,
  `set_arch_queue_overflow()`, and `write_arch_output_queue_cons()`.
- `SMMUV3_EVENTQ_PROD`, `SMMUV3_EVENTQ_CONS`, `SMMUV3_PRIQ_PROD`, and
  `SMMUV3_PRIQ_CONS` reads now expose the overflow/acknowledgement bits.
- `EVENTQ_CONS` and `PRIQ_CONS` writes now accept software `OVACKFLG`
  acknowledgement while preserving low queue index/wrap bits.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  adds `EventAndPriQueueOverflowFlagsToggleAndAck` and extends the existing
  EVENTQ overflow test.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh` gate the slice.

## Evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Component build | PASS | `build/verification/apollo-smmu-tbu-queue-ovflg-build-20260510.log`: `Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`. |
| Component CTest | PASS | `build/verification/apollo-smmu-tbu-queue-ovflg-ctest-20260510.log`: `100% tests passed, 0 tests failed out of 1`; `EventAndPriQueueOverflowFlagsToggleAndAck` verifies EVENTQ overflow toggles SMMU_EVENTQ_PROD.OVFLG and PRIQ overflow toggles SMMU_PRIQ_PROD.OVFLG. |
| Platform build | PASS | `build/verification/qbox-platform-smmu-queue-ovflg-20260510.log`: `QBox Buildroot platform runtime built in /build/qbox_dev/sources/qbox/build`. |
| Guest smoke | PASS | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-queue-ovflg-v2.driver.log`: `PASS: QBox guest IREE Hexagon tiny-CNN output matched`; runtime log records `features=0xffffff`, `architected PRIQ overflow stream-id=0x1 prod=0x80000008 cons=0x1`, and `1x1x2x2xf32=[[[54 63][90 99]]]`. |
| Static/checker/lane | PASS | `build/verification/smmu-queue-ovflg-static-final-20260510.log`: `PASS  tbu:output-queue-ovflg-ovack`, `SUMMARY {"pass": 254}`, and `Lane conclusion: Buildroot owns rootfs/DTB generation only; Linux Image comes from sources/linux, and libqemu comes from sources/qemu.` |

## Remaining blockers

- Full byte-exact EVENTQ and PRIQ record layouts for every architected event.
- Stall buffering and endpoint transaction re-drive when EVENTQ is full.
- Packet-level PCIe PRI request/response semantics and PASID-prefix policy.
- MSI/GIC delivery and abort-reporting parity for queue and GERROR interrupts.
- Upstream Linux `arm-smmu-v3` lifecycle parity for queue overflow recovery.
