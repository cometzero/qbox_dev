# QBox SMMUv3 Negative Replay Suite Verification - 2026-05-10

## Scope

SMMU-COMP-050 negative fault replay matrix functional slice.

This slice expands the Apollo SMMUv3 TBU stalled replay coverage from isolated
fault cases to a table-style component suite. It verifies that negative replay
records preserve the architected event number, StreamID, nonzero STAG,
`EVTQ_1.STALL`, input IOVA, syndrome reason/class/stage, and write attribute for
a representative fault matrix.

It remains a functional slice. It does not implement every Arm SMMUv3 event
record variant, full suppression/merge ordering, endpoint transaction hold and
reissue, or upstream Linux `arm-smmu-v3` event-thread recovery parity.

## Ground truth

- `sources/linux/drivers/iommu/arm/arm-smmu-v3/arm-smmu-v3.h` provides the local
  Linux ABI field reference for `EVTQ_0_ID`, `EVTQ_0_SID`, `EVTQ_1_STAG`,
  `EVTQ_1_STALL`, and `EVTQ_2_ADDR`.
- `sources/smmu/SPEC_REVIEW.md` H-05 and NEW-26 require stalled replay records
  to carry STAG/STALL state, syndrome information, and StreamID match data.

## Implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  adds `ARCH_CTRL_NEGATIVE_REPLAY_WRITE` and routes it through
  `run_arch_negative_replay(true)` so permission faults are recorded with the
  write attribute.
- Existing negative replay remains read-oriented through
  `ARCH_CTRL_NEGATIVE_REPLAY`; the new write path shares the same stalled EVENTQ
  and STAG allocation machinery.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc` adds
  `NegativeFaultReplayMatrixRecordsArchitectedEvents` for bad StreamID, bad STE,
  bad CD, access-flag fault, and write-permission fault cases.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh` gate the negative replay matrix.

## Evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Component build | PASS | `build/verification/apollo-smmu-tbu-negative-replay-suite-build-20260510.log`: `Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`. |
| Component CTest | PASS | `build/verification/apollo-smmu-tbu-negative-replay-suite-ctest-20260510.log`: `100% tests passed, 0 tests failed out of 1`; suite includes `NegativeFaultReplayMatrixRecordsArchitectedEvents`. |
| Static/checker/lane | PASS | `build/verification/smmu-negative-replay-suite-static-final-20260510.log`: `PASS  tbu:negative-fault-replay-suite`, `SUMMARY {"pass": 290}`, `CLASSIFICATION {"full_smmuv3_compliance": "not_claimed: ..."}`, lane check passed, and `diff --check` passed. |

## Remaining blockers

- Endpoint transactions are not truly held and reissued on the TLM data path.
- Full EVENTQ byte-exact parity for every Arm SMMUv3 event type remains open.
- Stall suppression/merge, early retry behavior, MSI/GIC ordering, and upstream
  Linux `arm-smmu-v3` event-thread recovery remain open.
