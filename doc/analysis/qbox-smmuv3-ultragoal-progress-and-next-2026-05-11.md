# QBox SMMUv3 ultragoal progress and remaining work (2026-05-11)

## Stop condition

This note records the state at the user's requested stop point for this turn.
Implementation is intentionally stopped here.  The aggregate ultragoal remains
incomplete and **full ARM SMMUv3 compliance is not claimed**.

Current durable status:

- OMX ultragoal: `0/1 complete, 0 pending, 0 in progress, 1 failed`.
- Goal: `G001-implement-the-reviewed-smmuv3-compli`.
- Classification gate: `full_smmuv3_compliance=not_claimed`.
- Commit: not created in this turn.

## Verified progress completed in this turn

### 1. ATS Translation Request config-response slice

Status: **implemented and verified**.

Purpose:

- Split ATS Translation Request response coding from the older compatibility
  ATS/PRI response helper.
- Return `CA` for ATS TR configuration lookup faults.
- Return `UR` plus `F_BAD_ATS_TREQ` for explicit `STE.Config==0b100` protocol
  abort.

Key files:

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
- `scripts/check_qbox_smmuv3_compliance.py`
- `scripts/check_buildroot_arm64_lane.sh`
- `doc/verification/qbox-smmuv3-ats-treq-config-response-verification-2026-05-11.md`

Evidence:

- `build/verification/smmu-ats-treq-config-response-build-20260511.log`
  - `[100%] Built target apollo-smmu-tbu-tests`
- `build/verification/smmu-ats-treq-config-response-gtest-20260511.log`
  - `[  PASSED  ] 3 tests.`
- `build/verification/smmu-ats-treq-config-response-ctest-20260511.log`
  - `100% tests passed, 0 tests failed out of 1`
- `build/verification/smmu-ats-treq-config-response-static-20260511.log`
  - `PASS  tbu:ats-treq-config-response-codes`
  - `SUMMARY {"pass": 1058}`
- `build/verification/smmu-ats-treq-config-response-lane-20260511.log`
  - lane passed; conclusion preserved Buildroot/Linux/libqemu ownership split
- `build/verification/smmu-ats-treq-config-response-evidence-summary-20260511.log`
- `build/verification/ultragoal-checkpoint-ats-treq-config-response-20260511.log`
  - checkpointed as failed/no-overclaim because aggregate remains incomplete

### 2. ATS Translation Request HTTU write-intent slice

Status: **implemented and verified**.

Purpose:

- Add a bounded ATS TR write-intent path (`NW==0`) using
  `ARCH_CTRL_ATS_TRANSLATION_REQUEST_WRITE`.
- Feed write intent into the existing stream/context/table walker so HTTU
  leaf updates apply to ATS Translation Requests.
- Verify CD.HA/CD.HD marks DBM writable-clean pages writable-dirty before a
  success response, while CD.HA-only write intent stays on the modeled
  `W==0`/no-event path.

Key files:

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
- `scripts/check_qbox_smmuv3_compliance.py`
- `scripts/check_buildroot_arm64_lane.sh`
- `doc/spec/qbox-smmuv3-compliance-checklist.md`
- `doc/verification/qbox-smmuv3-ats-treq-httu-write-intent-verification-2026-05-11.md`

Evidence:

- `build/verification/smmu-ats-treq-httu-write-intent-build-20260511.log`
  - `[100%] Built target apollo-smmu-tbu-tests`
- `build/verification/smmu-ats-treq-httu-write-intent-gtest-20260511.log`
  - `[  PASSED  ] 3 tests.`
  - log includes `nw=0 httu-dirty=1`
  - log includes HA-only `reason=permission` success/no-event path
- `build/verification/smmu-ats-treq-httu-write-intent-ctest-20260511.log`
  - `100% tests passed, 0 tests failed out of 1`
- `build/verification/smmu-ats-treq-httu-write-intent-static-20260511.log`
  - `PASS  tbu:ats-treq-httu-write-intent`
  - `SUMMARY {"pass": 1059}`
- `build/verification/smmu-ats-treq-httu-write-intent-lane-20260511.log`
  - lane passed
- `build/verification/smmu-ats-treq-httu-write-intent-evidence-summary-20260511.log`
- `build/verification/ultragoal-checkpoint-ats-treq-httu-write-intent-20260511.log`
  - checkpointed as failed/no-overclaim because aggregate remains incomplete

## Implemented but not yet verified at this stop point

### ATS Translation Request substream configuration-fault CA slice

Status: **implemented, verification pending**.

Purpose:

- Refine ATS TR `ARCH_FAULT_STREAM_DISABLED` response handling:
  - `STE.Config==0` disabled-stream remains `UR` with no event.
  - S1DSS/CD lookup-derived `F_STREAM_DISABLED` is a configuration fault and
    returns `CA`.
- Add component coverage for:
  - selected SSID out of `S1CDMax` -> `C_BAD_SUBSTREAMID`, `CA`, EVENTQ record;
  - S1DSS `SSID0` with PASID/SSID zero -> `F_STREAM_DISABLED`, `CA`, EVENTQ
    record.

Changed files currently carrying this unverified slice:

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
- `doc/verification/qbox-smmuv3-ats-treq-substream-ca-verification-2026-05-11.md`
- `doc/analysis/qbox-smmuv3-compliance-gap-plan-2026-05-10.md`

Required next verification commands:

```bash
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests \
  2>&1 | tee build/verification/smmu-ats-treq-substream-ca-build-20260511.log

./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests \
  --gtest_filter='*AtsTranslationRequestSubstreamConfigFaultsReturnCa*:*AtsTranslationRequestConfigFaultsUseArchitectedResponses*' \
  2>&1 | tee build/verification/smmu-ats-treq-substream-ca-gtest-20260511.log

ctest --test-dir sources/qbox/build/tests/components/apollo_smmu_tbu \
  --output-on-failure \
  2>&1 | tee build/verification/smmu-ats-treq-substream-ca-ctest-20260511.log

python3 scripts/check_qbox_smmuv3_compliance.py --self-test-negative \
  2>&1 | tee build/verification/smmu-ats-treq-substream-ca-static-20260511.log

./scripts/check_buildroot_arm64_lane.sh \
  > build/verification/smmu-ats-treq-substream-ca-lane-20260511.log 2>&1

bash -n scripts/*.sh \
  2>&1 | tee build/verification/smmu-ats-treq-substream-ca-bash-syntax-20260511.log

python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py scripts/qbox_pty_runner.py \
  2>&1 | tee build/verification/smmu-ats-treq-substream-ca-pycompile-20260511.log

git diff --check \
  2>&1 | tee build/verification/smmu-ats-treq-substream-ca-diff-check-20260511.log
```

After those pass, add a static checker gate such as
`tbu:ats-treq-substream-ca-config-faults`, update
`check_buildroot_arm64_lane.sh`, write an evidence summary, then checkpoint
with a fresh `get_goal` snapshot.  Keep checkpoint status failed/no-overclaim
unless all remaining aggregate compliance stories are truly complete.

## Important previously verified slices to preserve

The following recent slices are already evidence-backed and should not be
regressed while continuing work:

- S2PTW Device descriptor-fetch permission:
  - `doc/verification/qbox-smmuv3-s2ptw-device-fetch-verification-2026-05-11.md`
  - `build/verification/smmu-s2ptw-device-fetch-evidence-summary-20260511.log`
- DPT unsupported-as-disabled for ATS EATS:
  - `doc/verification/qbox-smmuv3-ats-dpt-unsupported-as-disabled-verification-2026-05-11.md`
  - `build/verification/smmu-dpt-eats-disabled-*20260511.log`
- ATS TR translation fault success/no-event:
  - `doc/verification/qbox-smmuv3-ats-treq-translation-fault-success-verification-2026-05-11.md`
  - `build/verification/smmu-ats-treq-translation-fault-evidence-summary-20260511.log`
- ATS TR nested split-stage IPA walk:
  - `doc/verification/qbox-smmuv3-ats-treq-split-stage-nested-verification-2026-05-11.md`
  - `build/verification/smmu-ats-treq-split-stage-nested-evidence-summary-20260511.log`
- HTTU AF/Dirty and HAFT table-descriptor updates:
  - `doc/verification/qbox-smmuv3-httu-af-dirty-verification-2026-05-11.md`
  - `doc/verification/qbox-smmuv3-httu-haft-verification-2026-05-11.md`

## Remaining major goals and issues

### High-priority next steps

1. **Finish the unverified substream CA slice**
   - Run the verification commands above.
   - Add checker/lane gates and evidence summary if the build and tests pass.

2. **ATS Completion Data Entry fidelity**
   - Model/verify R/W/U/Global/T/XT/TE fields and translation-size/STU behavior.
   - PASID-tagged ATS TR must force Global bit to zero.
   - Realm/TE/CXL.io behavior remains out of scope today and must stay
     explicitly unclaimed until implemented.

3. **Broader ATS/PRI protocol parity**
   - Packet-level ATS Translation Completion request/response correlation.
   - ATC invalidation timeout/error behavior and ordering.
   - PRI page-request flag-update behavior beyond current bounded PPR/response
     queue slices.

4. **DPT real implementation**
   - Current model largely treats DPT as unsupported or disabled.
   - Remaining work includes DPT tables, `DPT_WALK_EN`, DPT TLB entries,
     `DPT_CFG_FAR`, permission checks, dirty-page tracking, and full DPTI
     invalidation semantics.

5. **Full RME/GPT/GPC model**
   - Current Secure/Realm/Root handling is bounded and functional-slice level.
   - GPT/GPC checks, GPC fault payloads, and Realm PA/Non-secure PA ATS
     completion behavior remain open.

6. **ECMDQ protocol**
   - Current ECMDQ surface is intentionally RES0/WI/unsupported.
   - Full command queue scaling and protocol behavior remain open.

7. **Upstream Linux `arm-smmu-v3` lifecycle parity**
   - Configuration invalidation, fault recovery, stall/replay, ATS/PRI enable
     and disable ordering, and queue interrupt/MSI ordering need broader parity
     testing against the upstream driver model.

8. **IREE upstream HAL device registry integration**
   - Current IREE work is a repo-local upstream-style registry/dispatch slice.
   - True upstream IREE source integration, plugin registration API hardening,
     packaging, and end-to-end guest/runtime validation remain open.

### Validation debt before any final/full-compliance claim

- Re-run the complete static checker and lane checks after the pending
  substream CA slice is verified.
- Re-run component `ctest` for the Apollo SMMU TBU after each SMMU slice.
- Re-run Buildroot/QBox boot smoke only when boot-facing scripts/platform DTS or
  staged runtime artifacts are changed.
- Keep `full_smmuv3_compliance=not_claimed` until every checklist row no longer
  contains open matrix/protocol/upstream gaps.

## Recommended resume point

Resume from the pending substream CA slice:

1. Build `apollo-smmu-tbu-tests`.
2. Run the focused gtest filter for
   `AtsTranslationRequestSubstreamConfigFaultsReturnCa`.
3. If it passes, add static/lane checker gates.
4. Run full validation set and checkpoint with fresh `get_goal` JSON.
5. Then continue into ATS Completion Data Entry bit fidelity.
