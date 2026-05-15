# QBox SMMUv3 PRI response head-order verification — 2026-05-11

## Scope

SMMU-COMP-060 PRI response head-ordered exact-PRG slice.

This slice corrects the modeled `CMD_PRI_RESP` completion rule so a response can
retire only the head pending Page Request Group (PRG).  A command that names a
later PRG is preserved as a non-retiring diagnostic (`last_pri_response_unknown`,
`last_pri_response_order_mismatch`, and `last_pri_response_head_prg`) instead of
clearing the later request out of order.  A successful head response now also
advances the modeled `SMMU_PRIQ_CONS` index and clears PRIQ IRQ status when the
queue becomes empty.

## Ground truth used

- `sources/smmu/SPEC_REVIEW.md`: FINDING-M-08 records that `CMD_PRI_RESP` must
  match a PRGIndex to complete a page request response cycle.
- `sources/smmu/cpp/tests/unit/test_bugs_new2.cpp`: BUG-NEW-13 regression notes
  require `CMD_PRI_RESP` not to retire a non-head PRI entry.
- `sources/smmu/cpp/src/smmu/smmu.cpp`: the reference handler documents that the
  PRI response path must preserve non-head entries and retire only the current
  head when the command matches.

## Changed implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - `complete_prg()` now selects only the first pending PRG as the response
    candidate.
  - Responses for later PRGs no longer clear pending state.
  - Unknown diagnostics now include the head PRG and ordering mismatch state.
  - `advance_priq_cons_after_response()` advances PRIQ_CONS for a retired head
    PRG and clears the PRIQ IRQ when the queue becomes empty.
- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_arch_core.h`
  - Added `last_pri_response_order_mismatch` and
    `last_pri_response_head_prg` diagnostic fields.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Added/updated `CmdPriRespRequiresHeadPrgOrdering` to prove later-PRG
    preservation, then valid head completion followed by second PRG completion.
  - Added `CmdPriRespAdvancesPriqConsForHeadRequest` to prove `SMMU_PRIQ_CONS`
    advances on successful head response retirement.
- `scripts/check_qbox_smmuv3_compliance.py`,
  `scripts/check_buildroot_arm64_lane.sh`,
  `doc/spec/qbox-smmuv3-compliance-checklist.md`, and
  `doc/analysis/qbox-smmuv3-compliance-gap-plan-2026-05-10.md`
  now describe the head-ordered exact-PRG behavior instead of the earlier
  out-of-order functional slice.

## Verification commands and evidence

```sh
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)" \
  2>&1 | tee build/verification/smmu-pri-response-priq-cons-build-20260511.log

./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests \
  --gtest_filter='*CmdPriRespRequiresHeadPrgOrdering*:*CmdPriRespAdvancesPriqConsForHeadRequest*:*PriProtocolPrgIndexIsNineBitsAndWraps*:*CmdPriRespHonorsStreamIdQualifier*:*CmdPriRespHonorsSsidQualifier*' \
  2>&1 | tee build/verification/smmu-pri-response-priq-cons-gtest-20260511.log

ctest --test-dir sources/qbox/build --output-on-failure -R apollo-smmu-tbu-tests \
  2>&1 | tee build/verification/smmu-pri-response-priq-cons-ctest-20260511.log

python3 scripts/check_qbox_smmuv3_compliance.py \
  --json build/verification/smmu-pri-response-priq-cons-static-20260511.json \
  2>&1 | tee build/verification/smmu-pri-response-priq-cons-static-20260511.log

./scripts/check_buildroot_arm64_lane.sh \
  2>&1 | tee build/verification/smmu-pri-response-head-order-lane-20260511.log

bash -n scripts/*.sh
python3 -m py_compile scripts/qbox_pty_runner.py scripts/check_qbox_smmuv3_compliance.py
git diff --check
```

Additional closure script:

```sh
./build/verification/smmu-pri-response-head-order-final-closure-check-20260511.sh \
  2>&1 | tee build/verification/smmu-pri-response-head-order-final-closure-check-20260511.log
```

## Results

- Build: PASS (`[100%] Built target apollo-smmu-tbu-tests`).
- Focused gTest: PASS (`[  PASSED  ] 5 tests.`).
- CTest: PASS (`100% tests passed, 0 tests failed out of 1`).
- Static checker: PASS (`SUMMARY {"pass": 957}`) with
  `full_smmuv3_compliance=not_claimed`.
- Buildroot lane contract: PASS, including the new
  `CmdPriRespRequiresHeadPrgOrdering` grep gate.
- Syntax/diff: PASS (`bash -n`, `py_compile`, checklist JSON parse, and
  `git diff --check`).
- Closure check: PASS (`PRI response head-order closure checks completed`).

## No-overclaim boundary

This remains a functional compliance slice.  Full ARM SMMUv3 compliance is not
claimed: packet-level ATS/PRI transport, endpoint ATC recovery ordering,
complete upstream Linux `arm-smmu-v3` lifecycle parity, and full RME/GPT/GPC
policy remain open.
