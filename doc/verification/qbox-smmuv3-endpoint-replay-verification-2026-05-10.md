# QBox SMMUv3 Endpoint Replay Verification - 2026-05-10

## Scope

SMMU-COMP-050 endpoint replay accounting functional slice.

This slice connects the modeled stalled EVENTQ path to endpoint-originated TLM
translation faults. A data-path translation fault now allocates a nonzero STAG,
records a stalled endpoint replay entry, exposes pending/retry/success/terminate
accounting, and re-runs translation when software issues a matching
`CMD_RESUME(RETRY)` for the StreamID+STAG pair.

It remains a functional accounting slice. It does not make the original TLM
transaction block until resume, does not re-drive the original payload through a
SystemC scheduler path, and does not claim full Arm SMMUv3 event/stall replay
parity.

## Ground truth

- `sources/linux/drivers/iommu/arm/arm-smmu-v3/arm-smmu-v3.h` provides the local
  Linux ABI field reference for `CMDQ_RESUME_0_RESP`, `CMDQ_RESUME_0_SID`,
  `CMDQ_RESUME_1_STAG`, `EVTQ_1_STAG`, `EVTQ_1_STALL`, and `EVTQ_2_ADDR`.
- `sources/smmu/SPEC_REVIEW.md` H-05 and NEW-26 require stalled fault replay to
  preserve StreamID, STAG, stalled EVENTQ state, and resume matching state.

## Implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  adds `arch_endpoint_replay_record`, `REG_ARCH_ENDPOINT_REPLAY_STATUS`,
  `allocate_endpoint_replay_record`, and `complete_endpoint_replay`.
- Data-path `log_fault()` records faults as stalled EVENTQ entries and allocates
  endpoint replay accounting instead of aborting the component test harness with
  an expected translation fault report.
- `complete_stall()` calls `complete_endpoint_replay()` before clearing the
  matching stall record; `CMD_STALL_TERM` terminates matching replay records.
- `complete_endpoint_replay()` accounts retry/terminate outcomes and, for
  `CMD_RESUME(RETRY)`, re-runs translation against the current map so resolved
  faults can populate the modeled ATS/page-walk state.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc` adds
  `EndpointTransactionReplayRetriesAfterCmdResume`.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh` gate the endpoint replay slice.

## Evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Component build | PASS | `build/verification/apollo-smmu-tbu-endpoint-replay-build-20260510.log`: `Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`. |
| Component CTest | PASS | `build/verification/apollo-smmu-tbu-endpoint-replay-ctest-20260510.log`: `100% tests passed, 0 tests failed out of 1`; suite includes `EndpointTransactionReplayRetriesAfterCmdResume`. |
| Static/checker/lane | PASS | `build/verification/smmu-endpoint-replay-static-final-20260510.log`: `PASS  tbu:endpoint-replay-accounting`, `SUMMARY {"pass": 295}`, `CLASSIFICATION {"full_smmuv3_compliance": "not_claimed: ..."}`, lane check passed, and `diff --check` passed. |

## Remaining blockers

- The original endpoint TLM transaction is not truly held, resumed, and re-driven
  through a blocking SystemC transaction path.
- Full EVENTQ byte-exact parity for every Arm SMMUv3 event type remains open.
- Stall suppression/merge, early retry behavior, MSI/GIC ordering, and upstream
  Linux `arm-smmu-v3` event-thread recovery remain open.
- This slice does not claim full ARM SMMUv3 compliance; the repository checker
  must continue to report `full_smmuv3_compliance=not_claimed` until every
  SMMU-COMP gate is complete.
