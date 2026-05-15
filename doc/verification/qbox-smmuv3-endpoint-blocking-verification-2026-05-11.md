# QBox SMMUv3 Endpoint Blocking Replay Verification - 2026-05-11

## Scope

SMMU-COMP-050 endpoint blocking replay functional slice.

This slice extends endpoint replay from post-fault accounting/re-drive into an
opt-in caller-visible blocking model. When `REG_ARCH_ENDPOINT_REPLAY_CTRL` has
`ARCH_ENDPOINT_REPLAY_BLOCKING_ENABLE` set, an endpoint `b_transport()` access
that stalls on translation records the nonzero STAG and waits on the replay
resume event instead of immediately returning an address error. A matching
`CMD_RESUME(RETRY)` re-runs translation, re-drives the held payload downstream,
notifies the waiter, and lets the original caller return `TLM_OK_RESPONSE`.

The mode is opt-in to preserve the existing compatibility path used by current
platform smoke tests.

## Ground truth

- `sources/linux/drivers/iommu/arm/arm-smmu-v3/arm-smmu-v3.h` provides the local
  Linux ABI field reference for `CMDQ_RESUME_0_RESP`, `CMDQ_RESUME_0_SID`,
  `CMDQ_RESUME_1_STAG`, `EVTQ_1_STAG`, `EVTQ_1_STALL`, and `EVTQ_2_ADDR`.
- `sources/smmu/SPEC_REVIEW.md` H-05 and NEW-26 require stalled fault replay to
  preserve StreamID, STAG, stalled EVENTQ state, and resume matching state.

## Implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  adds `REG_ARCH_ENDPOINT_REPLAY_CTRL`, `REG_ARCH_ENDPOINT_BLOCK_STATUS`,
  `ARCH_ENDPOINT_REPLAY_BLOCKING_ENABLE`, and an endpoint replay resume event.
- `wait_endpoint_replay_resume()` waits for the matching replay record to be
  completed by `CMD_RESUME`, copies read data back to the original caller when
  applicable, and returns the replay status to the original transaction.
- `complete_endpoint_replay()` notifies waiting endpoint callers after retry,
  terminate, or abort completion.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc` adds
  `EndpointTransactionReplayBlocksCallerUntilCmdResume` using a spawned SystemC
  process to prove the original endpoint caller remains blocked until resume.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh` gate the caller-blocking slice.

## Evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Component build | PASS | `build/verification/apollo-smmu-tbu-endpoint-blocking-build-20260511.log`: `Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`. |
| Component CTest | PASS | `build/verification/apollo-smmu-tbu-endpoint-blocking-ctest-20260511.log`: `100% tests passed, 0 tests failed out of 1`; suite includes `EndpointTransactionReplayBlocksCallerUntilCmdResume`. |
| Static/checker/lane | PASS | `build/verification/smmu-endpoint-blocking-static-final-20260511.log`: `PASS  tbu:endpoint-replay-blocking`, `SUMMARY {"pass": 303}`, `CLASSIFICATION {"full_smmuv3_compliance": "not_claimed: ..."}`, lane check passed, and `diff --check` passed. |

## Remaining blockers

- Full EVENTQ byte-exact parity for every Arm SMMUv3 event type remains open.
- Stall suppression/merge, early retry behavior, MSI/GIC ordering, and upstream
  Linux `arm-smmu-v3` event-thread recovery remain open.
- This slice does not claim full ARM SMMUv3 compliance; the repository checker
  must continue to report `full_smmuv3_compliance=not_claimed` until every
  SMMU-COMP gate is complete.
