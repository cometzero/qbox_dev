# QBox SMMUv3 Stall Suppression Verification - 2026-05-11

## Scope

SMMU-COMP-050 stall suppression merge functional slice.

This slice adds duplicate stalled-fault suppression for pending replay records.
When a new stalled fault has the same StreamID, IOVA, and SSID-valid/SSID tuple
as an already pending stall, the Apollo TBU returns the existing STAG, increments
merge/suppression accounting, and does not push another EVENTQ record. Faults for
a different IOVA or SubstreamID still allocate a new STAG and EVENTQ entry.

It remains a functional slice. Full Arm SMMUv3 event matrix parity and upstream
Linux `arm-smmu-v3` event-thread recovery parity remain open.

## Ground truth

- `sources/linux/drivers/iommu/arm/arm-smmu-v3/arm-smmu-v3.h` provides the local
  Linux ABI field reference for `EVTQ_1_STAG`, `EVTQ_1_STALL`, and `EVTQ_2_ADDR`.
- `sources/smmu/SPEC_REVIEW.md` H-05 and NEW-26 require stalled replay records
  to carry STAG/STALL state and match later resume commands by StreamID+STAG.

## Implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  adds `REG_ARCH_STALL_MERGE_STATUS`, `m_arch_stall_suppressed`,
  `m_arch_stall_merged`, and `find_stall_by_fault()`.
- `allocate_stall_record()` now reuses the pending STAG for duplicate
  StreamID/IOVA/SSID stalled faults instead of allocating a second STAG.
- `record_fault()` skips the duplicate EVENTQ push when the stall was merged.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc` adds
  `StalledFaultsSuppressDuplicateEventRecords`.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh` gate the stall suppression slice.

## Evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Component build | PASS | `build/verification/apollo-smmu-tbu-stall-suppress-build-20260511.log`: `Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`. |
| Component CTest | PASS | `build/verification/apollo-smmu-tbu-stall-suppress-ctest-20260511.log`: `100% tests passed, 0 tests failed out of 1`; suite includes `StalledFaultsSuppressDuplicateEventRecords`. |
| Static/checker/lane | PASS | `build/verification/smmu-stall-suppress-static-final-20260511.log`: `PASS  tbu:stall-suppression-merge`, `SUMMARY {"pass": 307}`, `CLASSIFICATION {"full_smmuv3_compliance": "not_claimed: ..."}`, lane check passed, and `diff --check` passed. |

## Remaining blockers

- Full EVENTQ byte-exact parity for every Arm SMMUv3 event type remains open.
- Early retry behavior, MSI/GIC ordering, and upstream Linux `arm-smmu-v3`
  event-thread recovery remain open.
- This slice does not claim full ARM SMMUv3 compliance; the repository checker
  must continue to report `full_smmuv3_compliance=not_claimed` until every
  SMMU-COMP gate is complete.
