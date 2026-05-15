# QBox SMMUv3 PRI response unknown-PRG verification (2026-05-11)

This report captures the SMMU-COMP-060 PRI response unknown-PRG diagnostic slice.

## Scope

The bounded slice tightens observability for `CMD_PRI_RESP` commands that name a
PRI Request Group (PRG) not present in the pending request table. This is useful
for later upstream driver recovery parity because the model must distinguish an
architected completion from a software response to an already-cleared or invalid
PRG.

Implemented/verified behavior:

- Unknown PRG responses increment `m_arch_pri_unknown` while leaving no pending
  PRG entries.
- `arch_fault_replay_state.last_pri_response_unknown` becomes true.
- `last_pri_response_valid` remains false because no pending PRG was completed.
- The command response code is still preserved in `last_pri_response_code` for
  diagnostic comparison.
- StreamID and ATS-status metadata are cleared to zero for the unknown path.

## Static evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_arch_core.h`
  - `last_pri_response_unknown`
  - `last_pri_response_valid`
  - `last_pri_response_code`
- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - `complete_prg()` unknown-PRG diagnostic updates
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - `CmdPriRespUnknownPrgIsAccounted`

## Verification commands

```bash
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)" \
  2>&1 | tee build/verification/smmu-pri-response-unknown-prg-build-20260511.log

./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests \
  --gtest_filter='*CmdPriRespUnknownPrgIsAccounted*:*CmdPriRespMatchesExactPrgOutOfOrder*' \
  2>&1 | tee build/verification/smmu-pri-response-unknown-prg-gtest-20260511.log

ctest --test-dir sources/qbox/build --output-on-failure -R apollo-smmu-tbu-tests \
  2>&1 | tee build/verification/smmu-pri-response-unknown-prg-ctest-20260511.log

python3 scripts/check_qbox_smmuv3_compliance.py \
  --json build/verification/smmu-pri-response-unknown-prg-static-20260511.json \
  2>&1 | tee build/verification/smmu-pri-response-unknown-prg-static-20260511.log

./scripts/check_buildroot_arm64_lane.sh \
  2>&1 | tee build/verification/smmu-pri-response-unknown-prg-lane-20260511.log
```

## Expected result

The slice remains a functional compliance increment. It does not claim full
SMMUv3 compliance while packet-level PCIe ATS/PRI transport, complete ATC
recovery, upstream `arm-smmu-v3` lifecycle parity, and full RME/GPT/GPC policy
remain open.
