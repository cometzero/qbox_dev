# QBox SMMUv3 nested L1CD fetch stage-2 verification - 2026-05-11

## Scope

SMMU-COMP-030/040/050 nested L1CD fetch stage-2 functional slice.

This slice closes the 64K two-level context descriptor table gap in the nested
CD walk. When `STE.Config=NESTED` and `STE.S1FMT=64K_L2`, the Apollo TBU now
models the L1CD descriptor fetch address as an IPA, translates it through the
configured stage-2 descriptor walker, and reads the L1CD from the translated PA.
The L1CD descriptor's L2 pointer remains an IPA; the existing nested CD-fetch
stage-2 path then translates the selected L2 CD entry before reading the CD.

A stage-2 fault while translating an L1CD fetch is preserved as an S2 stalled
translation event with `CLASS=CD` and the L1CD fetch IPA in EVENTQ word 3.

This is still a functional slice: it does not claim full Arm CD invalidation
lifecycle parity, full descriptor-format parity, or upstream Linux event-thread
recovery parity.

## Ground truth

- `sources/smmu/wiki/concepts/two-stage-translation.md` records that CD/L1CD
  fetches use IPA space when stage 2 is present, and that a stage-2 fault during
  such SMMU-originated access remains a stage-2 fault.
- `sources/smmu/wiki/concepts/context-descriptor.md` describes the 64K L2 CD
  table shape where an L1CD descriptor points to a span of L2 CD entries.
- `sources/smmu/wiki/concepts/event-queue.md` and
  `sources/linux/drivers/iommu/arm/arm-smmu-v3/arm-smmu-v3.h` provide the
  EVENTQ `S2`, `CLASS`, `InputAddr`, and `IPA` fields used by the component
  tests.

## Implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  extends `arch_cd_address()` with `stage2_translate_l1cd_fetch`. For nested
  64K-L2 CD tables, the L1CD fetch IPA is translated via `arch_descriptor_walk()`
  before the L1 descriptor read. On translation failure, the path preserves
  `m_arch_fault_stage = ARCH_FAULT_STAGE_S2`,
  `m_arch_fault_event_class = ARCH_EVENT_CLASS_CD`, and
  `m_arch_last_ipa = l1_pa`.
- `arch_stream_context_walk()` passes the nested stage-2 walk configuration into
  `arch_cd_address()` before the selected CD address is returned, then continues
  to use the existing nested CD-fetch stage-2 path for the L2 CD entry itself.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc` adds
  `ArchitectedNestedL1CdFetchStage2Walks` for the successful nested L1CD+L2CD
  fetch path and `ArchitectedNestedL1CdFetchStage2FaultRecordsClassCd` for the
  negative replay EVENTQ path.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh` gate the implementation and test
  markers.

## Evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Component build | PASS | `build/verification/apollo-smmu-tbu-nested-l1cd-fetch-s2-build-20260511.log`: `Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`. |
| Component CTest | PASS | `build/verification/apollo-smmu-tbu-nested-l1cd-fetch-s2-ctest-20260511.log`: `100% tests passed, 0 tests failed out of 1`. |
| Static/checker/lane | PASS | `build/verification/smmu-nested-l1cd-fetch-s2-static-final-20260511.log`: `PASS  tbu:cd-table-ssid-index`, `PASS  tbu:walker-granule-stage-matrix`, `PASS  tbu:nested-l1cd-fetch-stage2-fault`, `SUMMARY {"pass": 362}`, `CLASSIFICATION {"full_smmuv3_compliance": "not_claimed: ..."}`, lane check passed, and diff checks passed. |

## Remaining blockers

- Full Arm SMMUv3 EVENTQ matrix parity, Linux `arm-smmu-v3` event-thread
  recovery parity, Secure-state `NSIPA`, RME `GPCF`, and F_VMS_FETCH remain
  open.
- Full upstream CD invalidation lifecycle parity remains open; this slice only
  validates modeled L1CD fetch translation and fault attribution.
- The repository checker must continue to report
  `full_smmuv3_compliance=not_claimed` until all SMMU-COMP gates pass.
