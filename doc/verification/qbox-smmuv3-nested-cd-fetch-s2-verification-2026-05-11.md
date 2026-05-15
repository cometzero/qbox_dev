# QBox SMMUv3 nested CD fetch stage-2 verification - 2026-05-11

## Scope

SMMU-COMP-030/040/050 nested CD fetch stage-2 functional slice.

This slice connects the existing stage-2 `CLASS=CD` EVENTQ encoding to the
actual nested stream/context walk. When `STE.Config=NESTED`, the Apollo TBU now
treats the modeled CD address as an IPA, translates it through the stage-2 page
walker before fetching the CD, and reports a failed CD-fetch translation as an
S2 stalled translation event with `CLASS=CD` and the CD IPA in EVENTQ word 3.

This is still a functional slice: it does not claim full CD invalidation
lifecycle parity or upstream Linux recovery parity. Stage-1 translation-table
descriptor-fetch and 64K-L2 L1CD fetch S2 coverage are recorded in follow-up
reports.

## Ground truth

- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
  states that a stage-2 fault while fetching a CD is reported with
  `CLASS == CD`, and that the IPA field carries the CD address.
- `sources/smmu/wiki/concepts/context-descriptor.md` records the same nested CD
  fetch rule: CD fetch addresses are IPAs in nested configurations and stage-2
  faults during CD fetch use `CLASS == CD`.
- `sources/linux/drivers/iommu/arm/arm-smmu-v3/arm-smmu-v3.h` defines the
  Linux-visible EVENTQ `S2`, `CLASS`, `ADDR`, and `IPA` fields used by the
  component test.

## Implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  adds the `architectural nested CD fetch stage-2 walk` path in
  `arch_stream_context_walk()` before the CD read. The path sets
  `m_arch_fault_event_class = ARCH_EVENT_CLASS_CD`, preserves
  `m_arch_last_ipa = cd_pa`, uses the existing stage-2 descriptor walker, and
  resets the event class back to `CLASS=IN` after a successful CD fetch
  translation so later transaction IPA faults are not misclassified.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  updates `ArchitectedWalkerStage2AndNestedMatrix` so nested CD descriptors are
  fetched from the stage-2-translated CD PA, and adds
  `ArchitectedNestedCdFetchStage2FaultRecordsClassCd` for the negative replay
  EVENTQ path.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh` gate the implementation and test
  markers.

## Evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Component build | PASS | `build/verification/apollo-smmu-tbu-nested-cd-fetch-s2-build-20260511.log`: `Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`. |
| Component CTest | PASS | `build/verification/apollo-smmu-tbu-nested-cd-fetch-s2-ctest-20260511.log`: `100% tests passed, 0 tests failed out of 1`. |
| Static/checker/lane | PASS | `build/verification/smmu-nested-cd-fetch-s2-static-final-20260511.log`: `PASS  tbu:cd-table-ssid-index`, `PASS  tbu:walker-granule-stage-matrix`, `PASS  tbu:event-record-stage2-cd-class`, `PASS  tbu:nested-cd-fetch-stage2-fault`, `SUMMARY {"pass": 345}`, `CLASSIFICATION {"full_smmuv3_compliance": "not_claimed: ..."}`, lane check passed, and diff checks passed. |

## Remaining blockers

- Follow-up nested 64K-L2 L1CD fetch stage-2 translation coverage is
  recorded in `doc/verification/qbox-smmuv3-nested-l1cd-fetch-s2-verification-2026-05-11.md`.
- Follow-up stage-1 translation-table descriptor fetch `CLASS=TT` coverage is
  recorded in `doc/verification/qbox-smmuv3-nested-tt-fetch-s2-verification-2026-05-11.md`.
- Full Arm SMMUv3 EVENTQ matrix parity, Linux `arm-smmu-v3` event-thread
  recovery parity, Secure-state `NSIPA`, RME `GPCF`, and F_VMS_FETCH remain
  open.
- The repository checker must continue to report
  `full_smmuv3_compliance=not_claimed` until all SMMU-COMP gates pass.
