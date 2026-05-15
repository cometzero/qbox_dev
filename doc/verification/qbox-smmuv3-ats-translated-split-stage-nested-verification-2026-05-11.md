# QBox SMMUv3 ATS Translated nested split-stage verification — 2026-05-11

## Scope

SMMU-COMP-050/060 architected nested ATS Translated split-stage IPA walk slice.

This slice extends the previous QBox split-stage ATS Translated model from the
bounded stage-2-only compatibility case to the architected `STE.Config==Nested`
case.  For `STE.EATS==0b10` with `SMMU_CR0.ATSCHK==1`, an ATS Translated
transaction carries an IPA, so the TBU now latches that split-stage request and
bypasses the nested stage-1 walk.  The incoming IPA is checked through the
existing architectural stage-2 walker and forwarded downstream as the resulting
PA.

## Ground truth used

- `sources/smmu/wiki/synthesis/smmu-pcie-ats-integration.md` describes
  split-stage ATS Translated traffic as carrying an IPA and requiring the SMMU
  to apply stage 2 to translate IPA to PA.
- `sources/smmu/wiki/concepts/stream-table-entry.md` documents
  `STE.EATS==0b10` as the split-stage ATS mode tied to `STE.Config==Nested`.
- `sources/smmu/rust/README.md` records the reference fix for
  `AtsTranslated + ATSCHK=1 + EATS=0b10`: run `translate_stage2_only()` on the
  incoming IPA instead of full S1+S2 translation.

## Changed implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - `arch_translated_split_stage_supported(uint32_t ste_cfg)` now includes
    `ARCH_STE_CFG_NESTED` while retaining the earlier stage-2-only compatibility
    case.
  - `m_arch_translated_split_stage2_request_active` latches an allowed
    EATS_SPLIT ATS Translated request until the data-path translation finishes.
  - `arch_stream_context_walk()` recognizes the latched Nested split-stage
    Translated request and dispatches directly to the stage-2 walker instead of
    fetching a CD or running stage 1.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Added `AtsTranslatedSplitStageNestedWalksIpaWithStage2Only`.
  - The test stages only a stage-2 page table for a Nested STE, submits an ATS
    Translated read, and proves the payload, `m_arch_last_ipa`,
    `m_arch_last_stage`, `m_arch_s2ttb`, and `m_arch_last_pa` come from the
    stage-2-only IPA walk.
- `scripts/check_qbox_smmuv3_compliance.py`
  - Added `tbu:ats-translated-split-stage-nested-s2-walk`.
- `scripts/check_buildroot_arm64_lane.sh`
  - Added static lane gates for the nested split-stage request latch and
    component test.
- `doc/spec/qbox-smmuv3-compliance-checklist.md` and
  `doc/analysis/qbox-smmuv3-compliance-gap-plan-2026-05-10.md`
  record this as functional-slice evidence while keeping packet-level ATS/PRI
  and full upstream driver parity outside the current claim.

## Verification results

All commands below completed successfully on 2026-05-11.

```sh
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)" \
  2>&1 | tee build/verification/smmu-ats-translated-split-stage-nested-build-20260511.log
```

- Result: pass; `apollo-smmu-tbu-tests` rebuilt successfully.
- Evidence: `build/verification/smmu-ats-translated-split-stage-nested-build-20260511.log`.

```sh
./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests \
  --gtest_filter='*AtsTranslatedSplitStageNestedWalksIpaWithStage2Only*:*AtsTranslatedSplitStageStage2OnlyWalksIpa*:*AtsTranslatedSplitStageUnsupportedRecordsForbidden*' \
  2>&1 | tee build/verification/smmu-ats-translated-split-stage-nested-gtest-20260511.log
```

- Result: pass; GoogleTest reported `3 tests` and `[  PASSED  ] 3 tests.`
- Evidence: `build/verification/smmu-ats-translated-split-stage-nested-gtest-20260511.log`.

```sh
ctest --test-dir sources/qbox/build --output-on-failure -R apollo-smmu-tbu-tests \
  2>&1 | tee build/verification/smmu-ats-translated-split-stage-nested-ctest-20260511.log
```

- Result: pass; CTest reported `100% tests passed, 0 tests failed out of 1`.
- Evidence: `build/verification/smmu-ats-translated-split-stage-nested-ctest-20260511.log`.

```sh
python3 scripts/check_qbox_smmuv3_compliance.py \
  --json build/verification/smmu-ats-translated-split-stage-nested-static-20260511.json \
  2>&1 | tee build/verification/smmu-ats-translated-split-stage-nested-static-20260511.log
```

- Result: pass; static audit summary was `{"pass": 966}`.
- Classification: `full_smmuv3_compliance=not_claimed`.
- Evidence:
  - `build/verification/smmu-ats-translated-split-stage-nested-static-20260511.log`
  - `build/verification/smmu-ats-translated-split-stage-nested-static-20260511.json`

```sh
./scripts/check_buildroot_arm64_lane.sh \
  2>&1 | tee build/verification/smmu-ats-translated-split-stage-nested-lane-20260511.log
```

- Result: pass; lane reported the new nested split-stage latch/component-test
  gates and ended at the standard lane conclusion.
- Evidence: `build/verification/smmu-ats-translated-split-stage-nested-lane-20260511.log`.

## No-overclaim boundary

This remains a functional compliance slice. Full ARM SMMUv3 compliance is not
claimed: the static checker still reports
`full_smmuv3_compliance=not_claimed: current QBox remains a functional/compliance-oriented slice until later SMMU-COMP gates pass`.
Packet-level endpoint ATC state/ordering, complete upstream Linux
`arm-smmu-v3` lifecycle parity, full RME/GPT/GPC policy, DPT (`EATS==0b11`),
and complete ATS/PRI protocol coverage remain open.
