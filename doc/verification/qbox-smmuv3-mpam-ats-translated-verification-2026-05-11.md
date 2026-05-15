# QBox SMMUv3 ATS Translated MPAM verification - 2026-05-11

## Scope

SMMU-COMP-020/050/060 ATS Translated MPAM functional slice.

This slice adds MPAM attribution for three ATS Translated cases that QBox can
model without full PASIDTT/CD lookup support:

- `SMMU_CR0.ATSCHK == 0`: Translated traffic bypasses configuration lookup and
  receives `SMMU_GBPMPAM.GBP_PARTID/GBP_PMG`.
- `SMMU_CR0.ATSCHK == 1` with a STE-sourced MPAM decision: Translated traffic
  receives `STE.PARTID/STE.PMG` when the modeled STE path does not require
  CD/PASID MPAM lookup.
- `SMMU_CR0.ATSCHK == 1` with `STE.S1MPAM == 1` on the modeled stage-1
  path: CD fetches use STE MPAM first, then the downstream Translated payload
  receives `CD.PARTID/CD.PMG`.

Ground truth used for this slice:

- `sources/smmu/wiki/concepts/mpam.md`
  - ATS Translated transactions use GBPMPAM when ATSCHK is disabled.
  - When ATSCHK is enabled, ATS Translated transactions follow ordinary STE/CD
    MPAM determination, with PASID dependency controlled by `SMMU_IDR3.PASIDTT`.

## Implementation evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - `allow_arch_translated_transaction()` resets and records translated MPAM
    state before the downstream payload is routed.
  - `translate_segment(..., preserve_mpam_state)` preserves the MPAM decision
    made by the ATS Translated gate while dynamic-map routing resolves the
    simulation PA.
  - `record_arch_mpam_from_gbp()` is used for ATSCHK-disabled Translated
    traffic.
  - `record_arch_mpam_from_ste()` is used for ATSCHK-enabled STE-sourced
    Translated traffic.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - `AtsTranslatedAtschkDisabledUsesGbpmpamAttributes`
  - `AtsTranslatedSteMpamAttributesPropagateWhenAtschkEnabled`
  - `AtsTranslatedCdMpamAttributesPropagateWhenS1MpamEnabled`

## Validation evidence

| Check | Evidence |
| --- | --- |
| Build | `build/verification/apollo-smmu-tbu-mpam-ats-translated-cd-build-20260511.log` (`Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`) |
| Component CTest | `build/verification/apollo-smmu-tbu-mpam-ats-translated-cd-ctest-20260511.log` (`100% tests passed, 0 tests failed out of 1`) |
| Focused gTest | `build/verification/apollo-smmu-tbu-mpam-ats-translated-cd-gtest-20260511.log` (`[  PASSED  ] 3 tests.`) |
| Syntax checks | `build/verification/smmu-mpam-ats-translated-cd-syntax-20260511.log` |
| Static/lane checker | `build/verification/smmu-mpam-ats-translated-cd-static-final-20260511.log` (`PASS  tbu:mpam-ats-translated-gbp-ste`, `PASS  tbu:mpam-ats-translated-cd`, `SUMMARY {"pass": 567}`) |
| Compliance JSON | `build/verification/qbox-smmuv3-compliance-mpam-ats-translated-cd-final-20260511.json` (`full_smmuv3_compliance: not_claimed`) |

## Result

`AtsTranslatedAtschkDisabledUsesGbpmpamAttributes` proves ATSCHK-disabled
Translated payloads carry GBPMPAM attributes downstream.
`AtsTranslatedSteMpamAttributesPropagateWhenAtschkEnabled` proves ATSCHK-enabled
Translated payloads carry STE-derived MPAM attributes for the modeled
STE-sourced case. `AtsTranslatedCdMpamAttributesPropagateWhenS1MpamEnabled`
proves the modeled S1 `STE.S1MPAM==1` path uses STE MPAM for the CD MPAM fetch
and CD-derived MPAM for the downstream Translated payload.

Remaining blockers: nested VMS/PASIDTT-dependent ATS Translated MPAM resolution,
Secure/Realm MPAM_NS/SP selection, PMCG PARTID/PMG filtering, full ATS/PRI
protocol parity, and full event/security/RME/GPC/upstream parity remain open.
