# QBox SMMUv3 Endpoint Redrive Verification - 2026-05-11

## Scope

SMMU-COMP-050 endpoint replay redrive functional slice.

This slice extends endpoint replay accounting into a downstream payload re-drive
model. A data-path translation fault now stores write payload bytes in the
pending StreamID+STAG replay record. When software installs a mapping and issues
a matching `CMD_RESUME(RETRY)`, the Apollo TBU re-runs translation and sends the
stored payload through the downstream TLM target. Read replay also allocates a
scratch payload buffer and performs the downstream read on retry.

It remains a functional slice. The original caller-visible `b_transport()` still
returns the expected address error for the initial stalled access; QBox does not
yet block that caller until resume through a SystemC scheduling path.

## Ground truth

- `sources/linux/drivers/iommu/arm/arm-smmu-v3/arm-smmu-v3.h` provides the local
  Linux ABI field reference for `CMDQ_RESUME_0_RESP`, `CMDQ_RESUME_0_SID`,
  `CMDQ_RESUME_1_STAG`, `EVTQ_1_STAG`, `EVTQ_1_STALL`, and `EVTQ_2_ADDR`.
- `sources/smmu/SPEC_REVIEW.md` H-05 and NEW-26 require stalled fault replay to
  preserve StreamID, STAG, stalled EVENTQ state, and resume matching state.

## Implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  extends `arch_endpoint_replay_record` with replay PA/length/status, redrive
  state, and held payload storage.
- `allocate_endpoint_replay_record()` captures endpoint write payload bytes for
  stalled data-path faults.
- `redrive_endpoint_replay()` walks the current translation mappings by segment
  and reissues read/write TLM payloads to `downstream` after `CMD_RESUME(RETRY)`.
- `complete_endpoint_replay()` now reports retry success only after downstream
  re-drive succeeds.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc` adds
  `EndpointTransactionReplayRedrivesWritePayload`.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh` gate the endpoint redrive slice.

## Evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Component build | PASS | `build/verification/apollo-smmu-tbu-endpoint-redrive-build-20260511.log`: `Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`. |
| Component CTest | PASS | `build/verification/apollo-smmu-tbu-endpoint-redrive-ctest-20260511.log`: `100% tests passed, 0 tests failed out of 1`; suite includes `EndpointTransactionReplayRedrivesWritePayload`. |
| Static/checker/lane | PASS | `build/verification/smmu-endpoint-redrive-static-final-20260511.log`: `PASS  tbu:endpoint-replay-redrive`, `SUMMARY {"pass": 299}`, `CLASSIFICATION {"full_smmuv3_compliance": "not_claimed: ..."}`, lane check passed, and `diff --check` passed. |

## Remaining blockers

- The original endpoint TLM transaction is not caller-blocked until resume.
- Full EVENTQ byte-exact parity for every Arm SMMUv3 event type remains open.
- Stall suppression/merge, early retry behavior, MSI/GIC ordering, and upstream
  Linux `arm-smmu-v3` event-thread recovery remain open.
- This slice does not claim full ARM SMMUv3 compliance; the repository checker
  must continue to report `full_smmuv3_compliance=not_claimed` until every
  SMMU-COMP gate is complete.
