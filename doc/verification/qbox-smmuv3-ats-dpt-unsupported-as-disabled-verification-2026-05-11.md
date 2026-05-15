# QBox SMMUv3 ATS DPT unsupported-as-disabled verification - 2026-05-11

## Scope

SMMU-COMP-050/060 ATS DPT unsupported-as-disabled slice.

This slice corrects the bounded ATS `STE.EATS==0b11` behavior while QBox keeps
`SMMU_IDR3.DPT` clear.  The SMMUv3 architecture treats the DPT EATS encoding as
`EATS disabled` when DPT is not implemented.  QBox therefore must not report this
case as a modeled DPT lookup failure.  ATS Translation Requests and ATS
Translated transactions now observe `m_arch_last_eats == EATS_DISABLED` and use
the existing EATS-disabled rejection path.

## Changed model surfaces

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - Adds `arch_dpt_supported()` as the discovery helper for `ARCH_IDR3_DPT`.
  - Makes `arch_translated_dpt_supported()` reflect the discovery helper.
  - Folds `ARCH_STE_EATS_DPT` to `ARCH_STE_EATS_DISABLED` in
    `arch_effective_eats()` when `IDR3.DPT` remains clear.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Renames the Translated-traffic component test to
    `AtsTranslatedDptUnsupportedActsAsDisabled` and asserts the effective EATS
    value is disabled.
  - Extends `AtsTranslationRequestHonorsCr0AtschkAndSteEats` to cover the same
    DPT-unsupported-as-disabled behavior for ATS Translation Requests.
- `scripts/check_qbox_smmuv3_compliance.py`
  - Updates the static gate to `tbu:ats-translated-dpt-unsupported-disabled`.
- `scripts/check_buildroot_arm64_lane.sh`
  - Updates lane contract greps for the DPT discovery helper and renamed test.

## Verification evidence

| Check | Result | Evidence |
| --- | --- | --- |
| Component build | PASS | `build/verification/smmu-dpt-eats-disabled-build-20260511.log` contains `[100%] Built target apollo-smmu-tbu-tests`. |
| Focused gTest | PASS | `build/verification/smmu-dpt-eats-disabled-gtest-20260511.log` contains `[  PASSED  ] 4 tests.` |
| CTest target | PASS | `build/verification/smmu-dpt-eats-disabled-ctest-20260511.log` contains `100% tests passed, 0 tests failed out of 1`. |
| Static checker | PASS | `build/verification/smmu-dpt-eats-disabled-static-20260511.log` contains `SUMMARY {"pass": 1055}` and `full_smmuv3_compliance` remains `not_claimed`. |
| Buildroot lane contract | PASS | `build/verification/smmu-dpt-eats-disabled-lane-20260511.log` reaches the lane conclusion with the updated DPT EATS-disabled contract greps passing. |
| Syntax / pycompile / diff-check | PASS | `smmu-dpt-eats-disabled-bash-syntax-20260511.log`, `smmu-dpt-eats-disabled-pycompile-20260511.log`, and `smmu-dpt-eats-disabled-diff-check-20260511.log` are empty success logs. |

## Remaining gap classification

This is still a bounded compliance correction, not full DPT support.  Real DPT
table walks, `DPT_WALK_EN`, DPT TLB entries, `DPT_CFG_FAR` fault reporting,
Secure/Realm DPT separation, DPT maintenance completion semantics, and GPT/GPC
ordering remain open.
