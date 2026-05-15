# QBox SMMUv3 PRI response SMMUEN-disabled verification — 2026-05-11

## Scope

SMMU-COMP-060 PRI response SMMUEN-disabled no-op slice.

This slice adds explicit regression coverage for the architected rule that
`CMD_PRI_RESP` is silently ignored while `SMMU_CR0.SMMUEN` is clear.  The command
must not consume a pending PRG, must not advance `SMMU_PRIQ_CONS`, and must not
raise `CMDQ_CONS.CERROR_ILL`.

## Ground truth used

- `sources/smmu/cpp/src/smmu/smmu.cpp` documents BUG-AUDIT-03: `CMD_PRI_RESP`
  is silently ignored when `SMMU_CR0.SMMUEN==0`.
- `sources/smmu/cpp/tests/unit/test_bugs_new15.cpp` contains the reference
  regression scenario: disable SMMUEN while keeping CMDQEN, submit
  `CMD_PRI_RESP`, and prove the PRG entry remains with no CERROR.

## Changed implementation

The QBox command queue path already gates processing on
`arch_cmdq_enabled()` (`SMMUEN|CMDQEN`).  This slice adds component coverage and
checker/lane/documentation gates so the no-op behavior is not implicit.

- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Added `CmdPriRespIgnoredWhenSmmuenDisabled`.
  - The test queues a PPR, disables SMMUEN while leaving CMDQEN set, submits
    `CMD_PRI_RESP`, and verifies pending PRG, `SMMU_PRIQ_CONS`, and CERROR are
    unchanged.  It then re-enables the SMMU and proves the same command can
    consume the PRG normally.
- `scripts/check_qbox_smmuv3_compliance.py`
  - Added `tbu:pri-response-smmuen-disabled-noop`.
- `scripts/check_buildroot_arm64_lane.sh`
  - Added a lane grep gate for `CmdPriRespIgnoredWhenSmmuenDisabled`.
- `doc/spec/qbox-smmuv3-compliance-checklist.md` and
  `doc/analysis/qbox-smmuv3-compliance-gap-plan-2026-05-10.md`
  record this as SMMU-COMP-060 functional-slice evidence.


## Verification results

All commands below completed successfully on 2026-05-11.

```sh
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)" \
  2>&1 | tee build/verification/smmu-pri-response-smmuen-disabled-build-20260511.log
```

- Result: pass; `apollo-smmu-tbu-tests` rebuilt successfully.
- Evidence: `build/verification/smmu-pri-response-smmuen-disabled-build-20260511.log`.

```sh
./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests \
  --gtest_filter='*CmdPriRespIgnoredWhenSmmuenDisabled*:*CmdPriRespAdvancesPriqConsForHeadRequest*:*CmdPriRespRequiresHeadPrgOrdering*' \
  2>&1 | tee build/verification/smmu-pri-response-smmuen-disabled-gtest-20260511.log
```

- Result: pass; GoogleTest reported `3 tests` and `[  PASSED  ] 3 tests.`
- Evidence: `build/verification/smmu-pri-response-smmuen-disabled-gtest-20260511.log`.

```sh
ctest --test-dir sources/qbox/build --output-on-failure -R apollo-smmu-tbu-tests \
  2>&1 | tee build/verification/smmu-pri-response-smmuen-disabled-ctest-20260511.log
```

- Result: pass; CTest reported `100% tests passed, 0 tests failed out of 1`.
- Evidence: `build/verification/smmu-pri-response-smmuen-disabled-ctest-20260511.log`.

```sh
python3 scripts/check_qbox_smmuv3_compliance.py \
  --json build/verification/smmu-pri-response-smmuen-disabled-static-20260511.json \
  2>&1 | tee build/verification/smmu-pri-response-smmuen-disabled-static-20260511.log
```

- Result: pass; static audit summary was `{"pass": 960}`.
- Classification: `full_smmuv3_compliance=not_claimed`.
- Evidence:
  - `build/verification/smmu-pri-response-smmuen-disabled-static-20260511.log`
  - `build/verification/smmu-pri-response-smmuen-disabled-static-20260511.json`

```sh
./scripts/check_buildroot_arm64_lane.sh \
  2>&1 | tee build/verification/smmu-pri-response-smmuen-disabled-lane-20260511.log
```

- Result: pass; lane reported the new
  `QBox Apollo SMMU TBU CMD_PRI_RESP SMMUEN-disabled no-op component test`
  gate and ended at the standard lane conclusion.
- Evidence: `build/verification/smmu-pri-response-smmuen-disabled-lane-20260511.log`.

## No-overclaim boundary

This remains a functional compliance slice. Full ARM SMMUv3 compliance is not
claimed: the static checker still reports
`full_smmuv3_compliance=not_claimed: current QBox remains a functional/compliance-oriented slice until later SMMU-COMP gates pass`.
Packet-level ATS/PRI transport, endpoint ATC recovery ordering, complete
upstream Linux `arm-smmu-v3` lifecycle parity, and full RME/GPT/GPC policy remain
open.
