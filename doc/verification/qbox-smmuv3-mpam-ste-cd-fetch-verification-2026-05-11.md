# QBox SMMUv3 STE-sourced CD fetch verification - 2026-05-11

## Scope

SMMU-COMP-020/050 STE-sourced CD fetch functional slice.

This slice extends MPAM attribution to modeled context descriptor fetch reads.
When `STE.S1MPAM==0`, the TBU resolves `STE.PARTID/STE.PMG` before context
descriptor selection and then attaches those resolved MPAM attributes to L1CD
and CD fetch reads. This covers the non-S1MPAM STE-sourced descriptor-fetch
path without changing client-derived translation-table descriptor attribution.

Ground truth used for this slice:

- `sources/smmu/wiki/concepts/mpam.md`
  - L1CD and CD accesses use `STE.{PARTID,PMG}`.
  - Stage-1 and stage-2 translation-table descriptors use client-derived MPAM
    attributes, so this slice does not blanket-tag TT descriptor fetches.

## Implementation evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - `populate_arch_mpam_extension_from_state()`
  - `read_downstream_u64(..., bool apply_current_mpam = false)`
  - `read_downstream_u64(l1_fetch_pa, l1_desc, false, true)` for L1CD fetches
  - `read_downstream_u64(cd_fetch_pa, cd0, false, true)` for CD fetches
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - `SteMpamAttributesPropagateOnCdFetches`

## Validation evidence

| Check | Evidence |
| --- | --- |
| Build | `build/verification/apollo-smmu-tbu-mpam-cd-fetch-build-20260511.log` (`Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`) |
| Component CTest | `build/verification/apollo-smmu-tbu-mpam-cd-fetch-ctest-20260511.log` (`100% tests passed, 0 tests failed out of 1`) |
| Focused gTest | `build/verification/apollo-smmu-tbu-mpam-cd-fetch-gtest-20260511.log` (`[  PASSED  ] 1 test.`) |
| Syntax checks | `build/verification/smmu-mpam-cd-fetch-syntax-20260511.log` |
| Static/lane checker | `build/verification/smmu-mpam-cd-fetch-static-final-20260511.log` (`PASS  tbu:mpam-ste-cd-fetches`, `SUMMARY {"pass": 532}`) |
| Compliance JSON | `build/verification/qbox-smmuv3-compliance-mpam-cd-fetch-final-20260511.json` (`full_smmuv3_compliance: not_claimed`) |

## Result

`SteMpamAttributesPropagateOnCdFetches` programs STE PARTID/PMG with
`STE.S1MPAM==0`, drives a stream read that requires a CD fetch, and proves the
CD fetch carries the resolved STE PARTID/PMG on the Apollo SMMU TLM extension.
The later client transaction still observes the same resolved MPAM attributes
through the existing endpoint propagation path.

Remaining blockers: STE-sourced CD fetch attribution while `STE.S1MPAM==1`,
client-derived MPAM on stage-1/stage-2 translation-table descriptor fetches,
complete Secure/Realm MPAM_NS/SP selection, PMCG PARTID/PMG filtering, and
complete ATS Translated/PASID MPAM rules remain open.
