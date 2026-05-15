# QBox SMMUv3 EVENTQ Access Attributes Verification - 2026-05-11

## Scope

SMMU-COMP-050 EVENTQ common access attributes functional slice.

This slice narrows EVENTQ byte-layout parity by adding modeled common access
attributes for stalled translation fault records: `PnU`, `InD`, `RnW`, and
`CLASS=IN`, modeled CLASS=TT/CD for translation-table and CD-originated stage-2 faults, modeled stage-2 IPA encoding, and modeled STE/CD/F_WALK_EABT fetch-address encoding in EVENTQ word 3. It does not claim full EVENTQ matrix parity.

## Ground truth

- `sources/linux/drivers/iommu/arm/arm-smmu-v3/arm-smmu-v3.h` defines
  `EVTQ_1_PnU`, `EVTQ_1_InD`, `EVTQ_1_RnW`, and `EVTQ_1_CLASS` in EVENTQ word 1.
- `sources/smmu/wiki/concepts/event-queue.md` documents the Arm SMMUv3 §7.3
  common fields: `RnW`, `PnU`, `InD`, `SSV`, `SubstreamID`, `S2`, and `CLASS`.
- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
  states that translation/access/permission events use input access attributes,
  post-STE override, and require `InD == 0` when `RnW == 0`.

## Implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  adds `ARCH_EVENT_PNU_SHIFT`, `ARCH_EVENT_IND_SHIFT`, `ARCH_EVENT_CLASS_IN`,
  `ARCH_EVENT_IPA_MASK`, `m_arch_last_fetch_addr`, and `arch_event_record_word3()`, encodes modeled
  `PnU`/`InD`/`RnW` plus `CLASS=IN/TT/CD` in stalled translation EVENTQ word 1, and
  separates byte-exact word-3 IPA/fetch fields from private fault detail status.
- `sources/qbox/systemc-components/common/include/tlm-extensions/apollo-smmu-stream-id.h`
  can carry modeled privilege and instruction attributes alongside StreamID and
  SubstreamID metadata.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc` adds
  `ArchitectedEventRecordCommonAccessAttributesAreEncoded`, including the
  write-class guard that forces `InD` low when `RnW` is low, and
  `EndpointAccessAttributesPropagateToFaultEvent` for endpoint TLM metadata propagation, and
  `ArchitectedEventRecordClassDistinguishesTableFaults` for CLASS=TT table-fault layout, `ArchitectedEventRecordStage2CdFaultUsesClassCd` for CLASS=CD stage-2 CD-fault layout, `ArchitectedEventRecordStage2IpaIsEncoded` for stage-2 IPA word-3 layout, and `ArchitectedEventRecordFetchAddressIsEncoded` for F_STE_FETCH/F_CD_FETCH fetch-address word-3 layout, and `ArchitectedEventRecordWalkEabtCarriesFetchAddress` for F_WALK_EABT fetch-address layout.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh` gate the new access-attribute slice.

## Evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Component build | PASS | `build/verification/apollo-smmu-tbu-eventq-attrs-build-20260511.log`: `Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`. |
| Component CTest | PASS | `build/verification/apollo-smmu-tbu-eventq-attrs-ctest-20260511.log`: `100% tests passed, 0 tests failed out of 1`; suite includes `ArchitectedEventRecordCommonAccessAttributesAreEncoded`, `EndpointAccessAttributesPropagateToFaultEvent`, and `ArchitectedEventRecordStage2IpaIsEncoded`. |
| Static/checker/lane | PASS | `build/verification/smmu-eventq-attrs-static-final-20260511.log`: `PASS  tbu:event-record-common-access-attrs`, `PASS  tbu:event-record-stage2-ipa`, `PASS  tbu:event-record-class-selector`, `PASS  tbu:event-record-stage2-cd-class`, `PASS  tbu:event-record-fetch-address`, `PASS  tbu:event-record-walk-eabt`, `SUMMARY {"pass": 338}`, `CLASSIFICATION {"full_smmuv3_compliance": "not_claimed: ..."}`, lane check passed, and diff checks passed. |

## Remaining blockers

- Full byte-exact EVENTQ parity for every Arm SMMUv3 event type remains open.
- This slice models access attributes for QBox stalled translation records only;
  remaining event-specific fields, full CLASS matrix parity, F_VMS_FETCH fetch-address layouts, Secure-state `NSIPA`, and RME
  `GPCF` remain future work.
- MSI/GIC ordering and upstream Linux `arm-smmu-v3` event-thread recovery remain
  open.
- The repository checker must continue to report
  `full_smmuv3_compliance=not_claimed` until all SMMU-COMP gates pass.
