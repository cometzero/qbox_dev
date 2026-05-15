# QBox SMMUv3 STAG/RESUME Verification - 2026-05-10

## Scope

SMMU-COMP-050 STAG/RESUME functional slice.

This slice covers nonzero STAG allocation for stalled EVENTQ records,
`EVTQ_1.STAG` and `EVTQ_1.STALL` emission for stalled faults, `CMD_RESUME`
StreamID+STAG matching with architected response encodings, stream-wide
`CMD_STALL_TERM`, and stall clear on `SMMU_CR0.SMMUEN` 1->0.

It remains functional only. Endpoint transaction hold/reissue, full stall
suppression/merge rules, precise PCIe PASID/PRI stall behavior, and full event
field matrix parity remain open.

## Ground truth

- `sources/linux/drivers/iommu/arm/arm-smmu-v3/arm-smmu-v3.h` defines
  `CMDQ_RESUME_0_RESP`, `CMDQ_RESUME_0_SID`, `CMDQ_RESUME_1_STAG`,
  `EVTQ_1_STAG`, `EVTQ_1_STALL`, and `EVTQ_2_ADDR`.
- `sources/smmu/SPEC_REVIEW.md` records the reviewed requirements: H-05
  `CMD_RESUME(StreamID, SSec, STAG, Action, Abort)`, NEW-26 stalled event word1
  STAG/STALL layout, and NEW-30 StreamID-scoped `CMD_STALL_TERM` termination.

## Implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  adds `arch_stall_record`, nonzero STAG allocation, StreamID+STAG lookup,
  `ARCH_EVENT_STAG_MASK`, `ARCH_EVENT_STALL`, and `ARCH_CMD_RESUME_STAG_MASK`.
- Stalled EVENTQ records now place STAG/STALL and modeled event attributes in
  word 1 and the faulting IOVA in word 2. Non-stall event records keep the
  existing compatibility layout.
- `CMD_RESUME` decodes StreamID and response from word 0, decodes STAG from word
  1, rejects unknown StreamID/STAG pairs without clearing pending state, and
  clears matching entries for retry/terminate/abort responses.
- `CMD_STALL_TERM` clears all pending records for the requested StreamID only;
  unrelated streams remain pending.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc` adds
  `CmdResumeMatchesStreamIdAndStag` and updates the replay/event tests for the
  stalled EVENTQ word layout.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh` gate the slice.

## Evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Component build | PASS | `build/verification/apollo-smmu-tbu-stag-resume-build-20260510.log`: `Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`. |
| Component CTest | PASS | `build/verification/apollo-smmu-tbu-stag-resume-ctest-20260510.log`: `100% tests passed, 0 tests failed out of 1`; tests cover STAG event word1, StreamID+STAG resume matching, unknown-resume rejection, and stream-wide STALL_TERM. |
| Static/checker/lane | PASS | `build/verification/smmu-stag-resume-static-final-20260510.log`: `PASS  tbu:stall-stag-resume`, `SUMMARY {"pass": 286}`, `CLASSIFICATION {"full_smmuv3_compliance": "not_claimed: ..."}`, lane check passed, and `diff --check` passed. |

## Remaining blockers

- Endpoint transactions are not truly held and reissued on the TLM data path.
- The complete architected EVENTQ field matrix is not byte-exact against every
  Arm SMMUv3 event type.
- Full stall suppression/merge rules, early retry behavior, and ordering against
  `CMD_SYNC`, MSI/GIC delivery, and upstream `arm-smmu-v3` event-thread recovery
  remain open.
- This slice does not claim full ARM SMMUv3 compliance; the repository checker
  must continue to report `full_smmuv3_compliance=not_claimed` until every
  SMMU-COMP gate is complete.
