# QBox SMMUv3 S1MPAM helper-walk MPAM verification - 2026-05-11

## Scope

SMMU-COMP-020/050 S1MPAM nested helper MPAM functional slice.

This slice tightens MPAM attribution when `STE.S1MPAM == 1`:

- L1CD/CD fetches and their nested stage-2 helper walks use STE-derived
  PARTID/PMG, as required for SMMU-originated L1CD/CD accesses.
- Once CD.PARTID/CD.PMG and VMS.PARTID_MAP are available, the current client
  transaction state is overwritten with CD/VMS-remapped PARTID/PMG for
  subsequent stage-1/stage-2 translation-table descriptor fetches and the final
  downstream client access.

Ground truth used for this slice:

- `sources/smmu/wiki/concepts/mpam.md`
  - L1CD/CD accesses use `STE.{PARTID,PMG}`.
  - Nested client transactions with `STE.S1MPAM == 1` use
    `VMS.PARTID_MAP[CD.PARTID]` and `CD.PMG`.
  - Stage-1/stage-2 translation-table descriptor fetches use the same
    PARTID/PMG as the client transaction.

## Implementation evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - `record_arch_mpam_from_ste()` now records `m_arch_last_ste5 = ste5`.
  - STE MPAM state is recorded before S2-only/S1/nested descriptor processing,
    independent of `STE.S1MPAM`.
  - `record_arch_mpam_from_cd(..., arch_ste_s1mpam(ste1))` still overrides the
    current client MPAM state after CD/VMS data is available.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - `SteMpamAttributesPropagateOnS1MpamCdFetches`
  - `NestedS1MpamAttributesPropagateOnStage2HelperWalks`

## Validation evidence

| Check | Evidence |
| --- | --- |
| Build | `build/verification/apollo-smmu-tbu-mpam-s1mpam-helper-build-20260511.log` (`Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`) |
| Component CTest | `build/verification/apollo-smmu-tbu-mpam-s1mpam-helper-ctest-20260511.log` (`100% tests passed, 0 tests failed out of 1`) |
| Focused gTest | `build/verification/apollo-smmu-tbu-mpam-s1mpam-helper-gtest-20260511.log` (`[  PASSED  ] 2 tests.`) |
| Syntax checks | `build/verification/smmu-mpam-s1mpam-helper-syntax-20260511.log` |
| Static/lane checker | `build/verification/smmu-mpam-s1mpam-helper-static-final-20260511.log` (`PASS  tbu:mpam-s1mpam-helper-walks`, `SUMMARY {"pass": 550}`) |
| Compliance JSON | `build/verification/qbox-smmuv3-compliance-mpam-s1mpam-helper-final-20260511.json` (`full_smmuv3_compliance: not_claimed`) |

## Result

`SteMpamAttributesPropagateOnS1MpamCdFetches` proves CD fetches still use
STE-derived PARTID/PMG even when `STE.S1MPAM == 1`, while the final client
access uses CD-derived PARTID/PMG. `NestedS1MpamAttributesPropagateOnStage2HelperWalks`
proves the nested CD-fetch stage-2 helper walk observes STE-derived MPAM first,
and later stage-2 descriptor fetches observe VMS-remapped CD-derived MPAM.

Remaining blockers: Secure/Realm MPAM_NS/SP selection, PMCG PARTID/PMG
filtering, full ATS Translated/PASID MPAM rules, full event/security/RME/GPC
coverage, and upstream arm-smmu-v3 lifecycle parity remain open.
