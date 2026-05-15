# QBox SMMUv3 client-derived TT fetch verification - 2026-05-11

## Scope

SMMU-COMP-020/050 client-derived translation-table descriptor fetch functional
slice.

Evidence pattern: SMMU-COMP-020/050 client-derived TT fetch functional slice.

This slice extends MPAM attribution to modeled stage-1 and stage-2 translation
table descriptor reads. Once the current client transaction's MPAM state is
resolved from STE/CD/VMS inputs, `arch_descriptor_walk()` attaches that state to
translation-table descriptor fetches. This keeps TT descriptor fetches separate
from GMPAM-originated queue/STE/VMS fetches and from STE-sourced L1CD/CD
fetches.

Ground truth used for this slice:

- `sources/smmu/wiki/concepts/mpam.md`
  - Stage-1 translation table descriptors use the same PARTID/PMG as the client
    transaction, resolved through the STE/CD/VMS chain as appropriate.
  - Stage-2 translation table descriptors use the same PARTID/PMG as the client
    transaction for that stream.

## Implementation evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - `populate_arch_mpam_extension_from_state()`
  - `read_downstream_u64(..., bool apply_current_mpam = false)`
  - `read_downstream_u64(desc_fetch_pa, desc, false, true)` in
    `arch_descriptor_walk()`
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - `SteMpamAttributesPropagateOnS1TtFetches`
  - `SteMpamAttributesPropagateOnS2TtFetches`

## Validation evidence

| Check | Evidence |
| --- | --- |
| Build | `build/verification/apollo-smmu-tbu-mpam-tt-fetch-build-20260511.log` (`Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`) |
| Component CTest | `build/verification/apollo-smmu-tbu-mpam-tt-fetch-ctest-20260511.log` (`100% tests passed, 0 tests failed out of 1`) |
| Focused gTest | `build/verification/apollo-smmu-tbu-mpam-tt-fetch-gtest-20260511.log` (`[  PASSED  ] 2 tests.`) |
| Syntax checks | `build/verification/smmu-mpam-tt-fetch-syntax-20260511.log` |
| Static/lane checker | `build/verification/smmu-mpam-tt-fetch-static-final-20260511.log` (`PASS  tbu:mpam-client-tt-fetches`, `SUMMARY {"pass": 541}`) |
| Compliance JSON | `build/verification/qbox-smmuv3-compliance-mpam-tt-fetch-final-20260511.json` (`full_smmuv3_compliance: not_claimed`) |

## Result

`SteMpamAttributesPropagateOnS1TtFetches` proves a stage-1 translation-table
fetch carries the resolved STE PARTID/PMG, and
`SteMpamAttributesPropagateOnS2TtFetches` proves a stage-2-only translation-table
fetch carries the same client-derived MPAM state. Both tests use the Apollo SMMU
TLM extension observed by the downstream memory target.

Remaining blockers: client-derived TT fetch attribution for nested
`STE.S1MPAM==1` CD/VMS remapped state before all stage-2 helper walks,
Secure/Realm MPAM_NS/SP selection, PMCG PARTID/PMG filtering, and complete ATS
Translated/PASID MPAM rules remain open.
