# QBox SMMUv3 Early Retry Verification - 2026-05-11

## Scope

SMMU-COMP-050 endpoint early-retry functional slice.

This slice models the Arm SMMUv3 permitted early retry behavior for pending
stalled endpoint transactions. A private QBox TBU control bit can retry pending
endpoint replay records without an explicit `CMD_RESUME(RETRY)`. The retry uses
the current translation state, does not emit another EVENTQ record, and leaves
the original STAG/stall pending until software acknowledges it with a matching
`CMD_RESUME` command.

It remains a functional slice. Full Arm SMMUv3 event matrix parity, optional
pre-commit stale-event discard policy, and upstream Linux `arm-smmu-v3`
event-thread recovery parity remain open.

## Ground truth

- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
  lines around 2989-2997 state that early retry is permitted, must perform the
  full translation procedure with current state, must not create additional
  fault records, and does not remove software's requirement to acknowledge the
  stalled fault record.
- `sources/smmu/TASKS_CPP_OPERATION.md` lists early retry and the preserved
  acknowledgement requirement as open C++ model work items.

## Implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  adds `ARCH_ENDPOINT_REPLAY_EARLY_RETRY`, `REG_ARCH_EARLY_RETRY_STATUS`,
  `early_retry_endpoint_replays()`, and replay-record `early_retry_succeeded`
  state.
- Early retry calls `redrive_endpoint_replay()` against pending endpoint replay
  records but does not clear the pending stall. If the retry succeeds, a later
  matching `CMD_RESUME(RETRY)` acknowledges the STAG without issuing a duplicate
  downstream replay.
- Failed early retries leave the replay/stall pending and account the failure
  without adding another EVENTQ record.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc` adds
  `EndpointEarlyRetryDoesNotDuplicateFaultAndRequiresResume`.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh` gate the early-retry slice.

## Evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Component build | PASS | `build/verification/apollo-smmu-tbu-early-retry-build-20260511.log`: `Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`. |
| Component CTest | PASS | `build/verification/apollo-smmu-tbu-early-retry-ctest-20260511.log`: `100% tests passed, 0 tests failed out of 1`; suite includes `EndpointEarlyRetryDoesNotDuplicateFaultAndRequiresResume`. |
| Static/checker/lane | PASS | `build/verification/smmu-early-retry-static-final-20260511.log`: `PASS  tbu:stall-early-retry`, `SUMMARY {"pass": 311}`, `CLASSIFICATION {"full_smmuv3_compliance": "not_claimed: ..."}`, lane check passed, and `diff --check` passed. |

## Remaining blockers

- Full EVENTQ byte-exact parity for every Arm SMMUv3 event type remains open.
- Early retry before a fault event is committed to EVENTQ can be modeled further
  with stale-event discard/commit policy tests.
- MSI/GIC ordering and upstream Linux `arm-smmu-v3` event-thread recovery remain
  open.
- This slice does not claim full ARM SMMUv3 compliance; the repository checker
  must continue to report `full_smmuv3_compliance=not_claimed` until every
  SMMU-COMP gate is complete.
