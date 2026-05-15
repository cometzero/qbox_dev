# QBox SMMUv3 ATS Translation Request nested split-stage verification — 2026-05-11

## Scope

SMMU-COMP-060 architected nested ATS Translation Request split-stage IPA walk slice.

This slice applies the same split-stage IPA rule to ATS Translation Requests as
the previous ATS Translated data-path slice.  For `STE.Config==Nested`,
`STE.EATS==0b10`, and `SMMU_CR0.ATSCHK==1`, the request address is an IPA and
must be translated through stage 2 only.  QBox now latches this ATS Translation
Request split-stage state and bypasses nested stage-1/CD lookup for the request
path before producing the modeled ATS success response.

## Ground truth used

- `sources/smmu/wiki/synthesis/smmu-pcie-ats-integration.md` describes
  split-stage ATS Translation Requests as applying stage 2 only (IPA to PA).
- `sources/smmu/wiki/concepts/stream-table-entry.md` documents
  `STE.EATS==0b10` as split-stage ATS associated with `STE.Config==Nested`.
- `sources/smmu/rust/README.md` records the reference split-stage fix as using
  `translate_stage2_only()` for `EATS==0b10` split-stage ATS paths.

## Changed implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - Added `m_arch_ats_treq_split_stage2_request_active` for the ATS Translation
    Request path.
  - `run_arch_ats_translation_request()` latches the split-stage request before
    the stream-context walk and clears it after the walk.
  - `arch_stream_context_walk()` recognizes the latched ATS Translation Request
    split-stage case and performs a Nested STE stage-2-only walk with path label
    `ats-translation-request-split-stage2`.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Added `AtsTranslationRequestSplitStageNestedWalksIpaWithStage2Only`.
  - The test stages only a stage-2 page table for a Nested STE, runs
    `ARCH_CTRL_ATS_TRANSLATION_REQUEST`, and proves `m_arch_last_ipa`,
    `m_arch_last_stage`, `m_arch_s2ttb`, `m_arch_last_pa`, and ATS cache state
    reflect the stage-2-only IPA walk.
- `scripts/check_qbox_smmuv3_compliance.py`
  - Added `tbu:ats-treq-split-stage-nested-s2-walk`.
- `scripts/check_buildroot_arm64_lane.sh`
  - Added static lane gates for the ATS Translation Request split-stage latch
    and component test.

## Verification results

All commands below completed successfully on 2026-05-11.

```sh
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)" \
  2>&1 | tee build/verification/smmu-ats-treq-split-stage-nested-build-20260511.log
```

- Result: pass; `apollo-smmu-tbu-tests` rebuilt successfully.
- Evidence: `build/verification/smmu-ats-treq-split-stage-nested-build-20260511.log`.

```sh
./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests \
  --gtest_filter='*AtsTranslationRequestSplitStageNestedWalksIpaWithStage2Only*:*AtsTranslatedSplitStageNestedWalksIpaWithStage2Only*:*AtsTranslationRequestHonorsCr0AtschkAndSteEats*' \
  2>&1 | tee build/verification/smmu-ats-treq-split-stage-nested-gtest-20260511.log
```

- Result: pass; GoogleTest reported `3 tests` and `[  PASSED  ] 3 tests.`
- Evidence: `build/verification/smmu-ats-treq-split-stage-nested-gtest-20260511.log`.

```sh
ctest --test-dir sources/qbox/build --output-on-failure -R apollo-smmu-tbu-tests \
  2>&1 | tee build/verification/smmu-ats-treq-split-stage-nested-ctest-20260511.log
```

- Result: pass; CTest reported `100% tests passed, 0 tests failed out of 1`.
- Evidence: `build/verification/smmu-ats-treq-split-stage-nested-ctest-20260511.log`.

```sh
python3 scripts/check_qbox_smmuv3_compliance.py \
  --json build/verification/smmu-ats-treq-split-stage-nested-static-20260511.json \
  2>&1 | tee build/verification/smmu-ats-treq-split-stage-nested-static-20260511.log
```

- Result: pass; static audit summary was `{"pass": 969}`.
- Classification: `full_smmuv3_compliance=not_claimed`.
- Evidence:
  - `build/verification/smmu-ats-treq-split-stage-nested-static-20260511.log`
  - `build/verification/smmu-ats-treq-split-stage-nested-static-20260511.json`

```sh
./scripts/check_buildroot_arm64_lane.sh \
  2>&1 | tee build/verification/smmu-ats-treq-split-stage-nested-lane-20260511.log
```

- Result: pass; lane reported the new ATS Translation Request nested
  split-stage latch/component-test gates and ended at the standard lane
  conclusion.
- Evidence: `build/verification/smmu-ats-treq-split-stage-nested-lane-20260511.log`.

## No-overclaim boundary

This remains a functional compliance slice. Full ARM SMMUv3 compliance is not
claimed: the static checker still reports
`full_smmuv3_compliance=not_claimed: current QBox remains a functional/compliance-oriented slice until later SMMU-COMP gates pass`.
Packet-level endpoint ATC state/ordering, DPT (`EATS==0b11`), complete upstream
Linux `arm-smmu-v3` lifecycle parity, full PRI/ATS protocol coverage, and
RME/GPT/GPC policy remain open.
