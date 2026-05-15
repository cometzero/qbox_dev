# QBox SMMUv3 ATS Translated split-stage stage-2-only verification — 2026-05-11

## Scope

SMMU-COMP-050/060 ATS Translated split-stage stage-2-only slice.

This slice narrows a previous unsupported EATS_SPLIT Translated path.  QBox now
permits the modeled `STE.EATS==0b10` ATS Translated case when the stream is
configured as stage-2-only (`STE.Config==S2_TRANS`): the incoming Translated
address is treated as an IPA, validated by the existing architectural stage-2
walker, and then forwarded to the downstream target as the resulting PA.
Non-stage2-only split-stage ATS Translated traffic remains rejected
with `F_TRANSL_FORBIDDEN`; the architected Nested split-stage case is now
covered by `doc/verification/qbox-smmuv3-ats-translated-split-stage-nested-verification-2026-05-11.md`.

## Ground truth used

- `sources/smmu/wiki/synthesis/smmu-pcie-ats-integration.md` describes
  `STE.EATS==0b10` split-stage ATS: Translated transactions carry an IPA and the
  SMMU applies stage 2 to obtain the PA.
- `sources/smmu/rust/README.md` records the reference fix for
  `AtsTranslated + ATSCHK=1 + EATS=0b10`: run `translate_stage2_only()` on the
  incoming IPA instead of a full S1+S2 translation.

## Changed implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - `arch_translated_split_stage_supported(uint32_t ste_cfg)` returned true
    for `ARCH_STE_CFG_S2_TRANS` in this slice; the later nested split-stage
    report extends the helper to `ARCH_STE_CFG_NESTED`.
  - `arch_translated_eats_unsupported_by_protocol()` now rejects EATS_SPLIT only
    when the STE configuration is not the modeled stage-2-only case.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Added `AtsTranslatedSplitStageStage2OnlyWalksIpa`.
  - The test stages a stage-2 page table, submits an ATS Translated read with
    `STE.EATS_SPLIT`, and proves the observed payload, `m_arch_last_stage`,
    `m_arch_s2ttb`, and `m_arch_last_pa` come from the stage-2 IPA walk.
- `scripts/check_qbox_smmuv3_compliance.py`
  - Added `tbu:ats-translated-split-stage-s2-walk`.
- `scripts/check_buildroot_arm64_lane.sh`
  - Added lane gates for the stage-2-only helper and component test.
- `doc/spec/qbox-smmuv3-compliance-checklist.md` and
  `doc/analysis/qbox-smmuv3-compliance-gap-plan-2026-05-10.md`
  record this as functional-slice evidence; the later nested split-stage
  report adds architected Nested STE coverage.


## Verification results

All commands below completed successfully on 2026-05-11.

```sh
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)" \
  2>&1 | tee build/verification/smmu-ats-translated-split-stage-s2-build-20260511.log
```

- Result: pass; `apollo-smmu-tbu-tests` rebuilt successfully.
- Evidence: `build/verification/smmu-ats-translated-split-stage-s2-build-20260511.log`.

```sh
./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests \
  --gtest_filter='*AtsTranslatedSplitStageStage2OnlyWalksIpa*:*AtsTranslatedSplitStageUnsupportedRecordsForbidden*:*AtsTranslatedTransactionForbiddenRecordsEvent*' \
  2>&1 | tee build/verification/smmu-ats-translated-split-stage-s2-gtest-20260511.log
```

- Result: pass; GoogleTest reported `3 tests` and `[  PASSED  ] 3 tests.`
- Evidence: `build/verification/smmu-ats-translated-split-stage-s2-gtest-20260511.log`.

```sh
ctest --test-dir sources/qbox/build --output-on-failure -R apollo-smmu-tbu-tests \
  2>&1 | tee build/verification/smmu-ats-translated-split-stage-s2-ctest-20260511.log
```

- Result: pass; CTest reported `100% tests passed, 0 tests failed out of 1`.
- Evidence: `build/verification/smmu-ats-translated-split-stage-s2-ctest-20260511.log`.

```sh
python3 scripts/check_qbox_smmuv3_compliance.py \
  --json build/verification/smmu-ats-translated-split-stage-s2-static-20260511.json \
  2>&1 | tee build/verification/smmu-ats-translated-split-stage-s2-static-20260511.log
```

- Result: pass; static audit summary was `{"pass": 963}`.
- Classification: `full_smmuv3_compliance=not_claimed`.
- Evidence:
  - `build/verification/smmu-ats-translated-split-stage-s2-static-20260511.log`
  - `build/verification/smmu-ats-translated-split-stage-s2-static-20260511.json`

```sh
./scripts/check_buildroot_arm64_lane.sh \
  2>&1 | tee build/verification/smmu-ats-translated-split-stage-s2-lane-20260511.log
```

- Result: pass; lane reported the new
  `QBox Apollo SMMU TBU ATS Translated split-stage stage-2-only component test`
  gate and ended at the standard lane conclusion.
- Evidence: `build/verification/smmu-ats-translated-split-stage-s2-lane-20260511.log`.

## No-overclaim boundary

This remains a functional compliance slice. Full ARM SMMUv3 compliance is not
claimed: the static checker still reports
`full_smmuv3_compliance=not_claimed: current QBox remains a functional/compliance-oriented slice until later SMMU-COMP gates pass`.
Packet-level endpoint ATC state/ordering, complete upstream Linux
`arm-smmu-v3` lifecycle parity, DPT, and full RME/GPT/GPC policy remain open.
