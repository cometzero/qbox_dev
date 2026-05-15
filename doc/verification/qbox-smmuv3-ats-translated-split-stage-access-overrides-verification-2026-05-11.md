# QBox SMMUv3 ATS Translated split-stage access-override verification (2026-05-11)

## Scope

SMMU-COMP-050/060 ATS Translated split-stage access-override slice.

This slice follows the pinned `sources/smmu` BUG-13.7 reference note: for
split-stage ATS Translated traffic, `STE.INSTCFG` and `STE.PRIVCFG` effective
access overrides must be applied before the stage-2-only translation path uses
the incoming IPA.

## Implementation evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  adds `arch_ste_effective_privileged()` and
  `arch_ste_effective_instruction()`.
- The ATS Translated gate records effective access metadata when
  `STE.EATS==Split` is accepted for the modeled stage-2-only path.
- The downstream TLM payload temporarily carries the effective
  privileged/instruction attributes while the routed memory transaction is in
  flight, then restores the caller extension.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  adds `AtsTranslatedSplitStageNestedAppliesAccessOverrides`.

## Verification evidence

Logs are under `build/verification/` with prefix
`smmu-ats-translated-split-stage-access-overrides-*20260511.*`.

Commands:

```sh
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j4
./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests \
  --gtest_filter='*AtsTranslatedSplitStageNestedAppliesAccessOverrides:*AtsTranslatedSplitStageNestedWalksIpaWithStage2Only:*AtsTranslationRequestSplitStageNestedWalksIpaWithStage2Only'
ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure
python3 scripts/check_qbox_smmuv3_compliance.py --json build/verification/smmu-ats-translated-split-stage-access-overrides-static-20260511.json
./scripts/check_buildroot_arm64_lane.sh
```

## No-overclaim boundary

This is a bounded functional slice. It does not claim full ARM SMMUv3
compliance, full PCIe ATS packet semantics, DPT support, complete PRI ordering,
upstream Linux `arm-smmu-v3` lifecycle parity, or complete RME/GPT/GPC policy.
The static checker must continue to report `full_smmuv3_compliance` as
`not_claimed` until those items are implemented and verified.
