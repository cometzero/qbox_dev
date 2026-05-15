# QBox SMMUv3 nested TT fetch stage-2 verification - 2026-05-11

## Scope

SMMU-COMP-030/040/050 nested TT fetch stage-2 functional slice.

This slice extends the nested stream/context walk beyond CD fetches. When
`STE.Config=NESTED`, stage-1 translation-table descriptor fetch addresses are
modeled as IPAs, translated through the configured stage-2 descriptor walker,
and only then read from downstream memory. A stage-2 fault while translating a
stage-1 TT descriptor fetch is preserved as an S2 stalled translation event with
`CLASS=TT` and the TT fetch IPA in EVENTQ word 3.

This is still a functional slice: it does not claim full Arm descriptor matrix
parity or upstream Linux event-thread recovery parity. Nested 64K-L2 L1CD
fetch coverage is recorded in the follow-up L1CD report.

## Ground truth

- `sources/smmu/wiki/concepts/two-stage-translation.md` states that nested
  stage-1 table-walk addresses are subject to stage-2 translation, and that
  stage-2 faults during a stage-1 table walk remain stage-2 faults.
- `sources/smmu/wiki/concepts/event-queue.md` describes the EVENTQ `S2`,
  `CLASS`, `InputAddr`, and fetch/IPA fields used to distinguish input,
  translation-table, and CD-originated translation faults.
- `sources/linux/drivers/iommu/arm/arm-smmu-v3/arm-smmu-v3.h` defines the
  Linux-visible `EVTQ_1_CLASS_TT`, `EVTQ_1_S2`, and `EVTQ_3_IPA` fields used
  by the component test.

## Implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  extends `arch_descriptor_walk()` with `stage2_translate_descriptor_fetch` so
  nested stage-1 descriptor fetch IPAs are translated through stage 2 before the
  descriptor read. On translation failure, the path preserves
  `m_arch_fault_stage = ARCH_FAULT_STAGE_S2`,
  `m_arch_fault_event_class = ARCH_EVENT_CLASS_TT`, and
  `m_arch_last_ipa = desc_pa`.
- `arch_stream_context_walk()` passes the nested stage-2 walk configuration into
  the stage-1 descriptor walk, then reuses the same stage-2 configuration for
  the final IPA-to-PA translation.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  updates `ArchitectedWalkerStage2AndNestedMatrix` to map the nested stage-1
  table pages through stage 2 on the success path, and adds
  `ArchitectedNestedTtFetchStage2FaultRecordsClassTt` for the negative replay
  EVENTQ path.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh` gate the implementation and test
  markers.

## Evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Component build | PASS | `build/verification/apollo-smmu-tbu-nested-tt-fetch-s2-build-20260511.log`: `Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`. |
| Component CTest | PASS | `build/verification/apollo-smmu-tbu-nested-tt-fetch-s2-ctest-20260511.log`: `100% tests passed, 0 tests failed out of 1`. |
| Static/checker/lane | PASS | `build/verification/smmu-nested-tt-fetch-s2-static-final-20260511.log`: `PASS  tbu:cd-table-ssid-index`, `PASS  tbu:walker-granule-stage-matrix`, `PASS  tbu:nested-cd-fetch-stage2-fault`, `PASS  tbu:nested-tt-fetch-stage2-fault`, `SUMMARY {"pass": 353}`, `CLASSIFICATION {"full_smmuv3_compliance": "not_claimed: ..."}`, lane check passed, and diff checks passed. |

## Remaining blockers

- Follow-up nested 64K-L2 L1CD fetch stage-2 translation coverage is
  recorded in `doc/verification/qbox-smmuv3-nested-l1cd-fetch-s2-verification-2026-05-11.md`.
- Full Arm SMMUv3 EVENTQ matrix parity, Linux `arm-smmu-v3` event-thread
  recovery parity, Secure-state `NSIPA`, RME `GPCF`, and F_VMS_FETCH remain
  open.
- The repository checker must continue to report
  `full_smmuv3_compliance=not_claimed` until all SMMU-COMP gates pass.
