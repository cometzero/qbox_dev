# QBox SMMUv3 STE-sourced MPAM verification - 2026-05-11

## Scope

SMMU-COMP-020/050 STE-sourced MPAM functional slice.

This slice extends the modeled MPAM assignment path so traffic with
`STE.S1MPAM==0` takes `STE.PARTID` and `STE.PMG` instead of CD/VMS-derived
attributes. The resolved PARTID/PMG are carried on the Apollo SMMU TLM
extension for the downstream memory access and exposed through private MPAM
status/detail registers for component verification.

Ground truth used for this slice:

- `sources/smmu/wiki/concepts/mpam.md`
  - Stage-1-only and nested traffic use `STE.PARTID`/`STE.PMG` when
    `STE.S1MPAM==0`.
  - The SMMU assigns PARTID/PMG to client transactions rather than passing
    through device-provided values.
- `sources/smmu/wiki/concepts/stream-table-entry.md`
  - `STE.PARTID` is bits `[287:272]` and `STE.PMG` is bits `[327:320]`.
  - `STE.S1MPAM==0` means PARTID/PMG come from the STE.

## Implementation evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - `ARCH_STE_MPAM_WORD4_OFFSET`
  - `ARCH_STE_PARTID_SHIFT = 16`
  - `ARCH_STE_PMG_SHIFT = 0`
  - `record_arch_mpam_from_ste()`
  - `REG_ARCH_MPAM_STATUS` / `REG_ARCH_MPAM_DETAIL`
- `sources/qbox/systemc-components/common/include/tlm-extensions/apollo-smmu-stream-id.h`
  - `mpam_valid`, `mpam_remapped`, `mpam_unknown`, `mpam_partid`, `mpam_pmg`
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - `SteMpamAttributesPropagateWhenS1MpamDisabled`

## Validation evidence

| Check | Evidence |
| --- | --- |
| Build | `build/verification/apollo-smmu-tbu-ste-mpam-attrs-build-20260511.log` (`Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`) |
| Component CTest | `build/verification/apollo-smmu-tbu-ste-mpam-attrs-ctest-20260511.log` (`100% tests passed, 0 tests failed out of 1`) |
| Focused gTest | `build/verification/apollo-smmu-tbu-ste-mpam-attrs-gtest-20260511.log` (`[  PASSED  ] 1 test.`) |
| Syntax checks | `build/verification/smmu-ste-mpam-attrs-syntax-20260511.log` |
| Static/lane checker | `build/verification/smmu-ste-mpam-attrs-static-final-20260511.log` (`PASS  tbu:ste-mpam-attributes`, `SUMMARY {"pass": 494}`) |
| Compliance JSON | `build/verification/qbox-smmuv3-compliance-ste-mpam-attrs-final-20260511.json` (`full_smmuv3_compliance: not_claimed`) |

## Result

`SteMpamAttributesPropagateWhenS1MpamDisabled` drives a stage-1 stream/context
walk with `STE.S1MPAM==0`, stages `STE.PARTID==0x1b` and `STE.PMG==0x6`, and
proves the downstream memory target observes those attributes on the Apollo
SMMU TLM extension without marking the transaction as VMS-remapped.

Remaining blockers: `GBPMPAM` global-bypass programming, `GMPAM`
SMMU-originated transaction attributes, Secure/Realm MPAM_NS/SP selection,
full PMG range and UNKNOWN behavior, PMCG PARTID/PMG filtering, and complete
ATS Translated/PASID MPAM rules remain open.
