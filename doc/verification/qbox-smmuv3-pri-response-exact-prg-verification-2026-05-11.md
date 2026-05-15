# QBox SMMUv3 PRI response exact-PRG verification (2026-05-11)

This report captures the SMMU-COMP-060 PRI response exact-PRG slice.

## Scope

The bounded slice tightens the modeled `CMD_PRI_RESP` completion path. The
model must complete the pending PRI request group identified by the command PRG,
not just the oldest outstanding request, and it must leave enough observable
metadata for regression tests and future driver-recovery comparisons.

Implemented/verified behavior:

- `complete_prg()` records the last successful response StreamID, response code,
  and original ATS status in `arch_fault_replay_state`.
- Unknown PRG responses set an explicit `last_pri_response_unknown` diagnostic.
- A component test creates two pending PRGs and completes the second one first,
  verifying exact-PRG matching, reject accounting, and preserved ATS status.
- A follow-up response then completes the first PRG, proving out-of-order
  completion does not clear the wrong pending entry.

## Static evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_arch_core.h`
  - `last_pri_response_stream_id`
  - `last_pri_response_code`
  - `last_pri_response_ats_status`
  - `last_pri_response_unknown`
- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - `complete_prg()` response metadata updates
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - `CmdPriRespMatchesExactPrgOutOfOrder`

## Verification commands

```bash
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)" \
  2>&1 | tee build/verification/smmu-pri-response-exact-prg-build-20260511.log

./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests \
  --gtest_filter='*CmdPriRespMatchesExactPrgOutOfOrder*:*CmdPriRespUnknownPrgIsAccounted*' \
  2>&1 | tee build/verification/smmu-pri-response-exact-prg-gtest-20260511.log

ctest --test-dir sources/qbox/build --output-on-failure -R apollo-smmu-tbu-tests \
  2>&1 | tee build/verification/smmu-pri-response-exact-prg-ctest-20260511.log

python3 scripts/check_qbox_smmuv3_compliance.py \
  --json build/verification/smmu-pri-response-exact-prg-static-20260511.json \
  2>&1 | tee build/verification/smmu-pri-response-exact-prg-static-20260511.log

./scripts/check_buildroot_arm64_lane.sh \
  2>&1 | tee build/verification/smmu-pri-response-exact-prg-lane-20260511.log
```

## Expected result

The slice remains a functional compliance increment. It does not claim full
SMMUv3 compliance while packet-level PCIe ATS/PRI transport, full ATC recovery,
upstream `arm-smmu-v3` parity, and complete RME/GPT/GPC policy remain open.
