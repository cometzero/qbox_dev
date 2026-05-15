# QBox SMMUv3 Early Retry Stale-Event Discard Verification - 2026-05-11

## Scope

SMMU-COMP-050 endpoint early-retry stale-event discard functional slice.

This slice models the Arm SMMUv3 permitted policy where a stalled transaction
successfully early-retries before its original fault event is committed to the
Event queue. QBox chooses the permitted discard behavior for buffered, not-yet
visible stalled EVENTQ records: the endpoint replay progresses with current
translations, the stale buffered event is removed, and the modeled STAG/replay
pending state is cleared because no software-visible fault record was committed.

It remains a functional slice. Full Arm SMMUv3 event matrix parity and upstream
Linux `arm-smmu-v3` event-thread recovery parity remain open.

## Ground truth

- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
  line 3005 states that if an SMMU successfully early-retries a stalled
  transaction before the original stall event is committed to the Event queue,
  the SMMU may discard the fault event or continue and commit it.
- `sources/smmu/wiki/concepts/event-queue.md` documents permitted early retry
  while an Event queue is not writable and stale-event handling when the queue
  later becomes writable.

## Implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  adds `event_committed` tracking to `arch_stall_record`, marks committed stall
  events after successful EVENTQ writes, and adds
  `discard_uncommitted_early_retry()` plus `discard_buffered_stall_event()`.
- `REG_ARCH_EARLY_RETRY_STATUS` now includes a high-byte discarded-event count.
- Successful early retry of a buffered, uncommitted stalled EVENTQ record removes
  the stale buffered event, clears the modeled pending STAG/replay state, and
  avoids later redrive when software advances `EVENTQ_CONS`.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc` adds
  `EndpointEarlyRetryDiscardsUncommittedStaleEvent`.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh` gate the stale-event discard slice.

## Evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Component build | PASS | `build/verification/apollo-smmu-tbu-early-retry-discard-build-20260511.log`: `Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`. |
| Component CTest | PASS | `build/verification/apollo-smmu-tbu-early-retry-discard-ctest-20260511.log`: `100% tests passed, 0 tests failed out of 1`; suite includes `EndpointEarlyRetryDiscardsUncommittedStaleEvent`. |
| Static/checker/lane | PASS | `build/verification/smmu-early-retry-discard-static-final-20260511.log`: `PASS  tbu:stall-early-retry-discard`, `SUMMARY {"pass": 315}`, `CLASSIFICATION {"full_smmuv3_compliance": "not_claimed: ..."}`, lane check passed, and `diff --check` passed. |

## Remaining blockers

- Full EVENTQ byte-exact parity for every Arm SMMUv3 event type remains open.
- This implements one permitted stale-event policy for buffered QBox events; the
  complete Arm implementation-defined policy matrix is still not exhaustive.
- MSI/GIC ordering and upstream Linux `arm-smmu-v3` event-thread recovery remain
  open.
- This slice does not claim full ARM SMMUv3 compliance; the repository checker
  must continue to report `full_smmuv3_compliance=not_claimed` until every
  SMMU-COMP gate is complete.
