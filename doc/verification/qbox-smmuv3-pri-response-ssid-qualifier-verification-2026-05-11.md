# QBox SMMUv3 PRI response SSID qualifier verification (2026-05-11)

This report captures the SMMU-COMP-060 PRI response SSID qualifier slice
(PASID/SSID qualifier handling).

## Scope

The bounded slice tightens `CMD_PRI_RESP` matching beyond PRG-only and
StreamID-qualified completion. When the modeled command word carries SSV plus a
SubstreamID/PASID, the Apollo TBU now treats the response as matching only a
pending PRI request with the named PRG, matching StreamID when supplied, and the
same PASID/SSID. This prevents software from clearing a PASID-specific PPR with
a response that names the correct PRG but the wrong PASID.

Implemented/verified behavior:

- Pending PRI requests retain modeled PASID/SSID metadata from `allocate_prg()`
  and the memory-backed PPR path.
- `ARCH_CMD_PRI_RESP` handling passes `cmdq_ssid_valid(word0)` and
  `cmdq_ssid(word0)` into `complete_prg()` for both Non-secure and Secure CMDQ
  paths.
- A PRG match with a different command PASID/SSID leaves the pending request
  intact.
- The mismatch path records `last_pri_response_ssid_mismatch`, command SSID
  validity, and the command SSID in architected fault/replay state.
- A later response with the correct PASID/SSID clears the pending PRG and
  records normal completion metadata, including the matched request SSID.
- Legacy command words without SSV remain compatibility wildcards for existing
  tests and guest-facing slices.

## Static evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_arch_core.h`
  - `last_pri_response_ssid_mismatch`
  - `last_pri_response_cmd_ssid_valid`
  - `last_pri_response_cmd_ssid`
  - `last_pri_response_ssid_valid`
  - `last_pri_response_ssid`
- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - `arch_pri_request::ssid_valid`
  - `arch_pri_request::ssid`
  - `complete_prg(..., cmdq_ssid_valid(word0), cmdq_ssid(word0))`
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - `CmdPriRespHonorsSsidQualifier`

## Verification commands

```bash
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)" \
  2>&1 | tee build/verification/smmu-pri-response-ssid-qualifier-build-20260511.log

./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests \
  --gtest_filter='*CmdPriRespHonorsSsidQualifier*:*CmdPriRespHonorsStreamIdQualifier*:*CmdPriRespMatchesExactPrgOutOfOrder*' \
  2>&1 | tee build/verification/smmu-pri-response-ssid-qualifier-gtest-20260511.log

ctest --test-dir sources/qbox/build --output-on-failure -R apollo-smmu-tbu-tests \
  2>&1 | tee build/verification/smmu-pri-response-ssid-qualifier-ctest-20260511.log

python3 scripts/check_qbox_smmuv3_compliance.py \
  --json build/verification/smmu-pri-response-ssid-qualifier-static-20260511.json \
  2>&1 | tee build/verification/smmu-pri-response-ssid-qualifier-static-20260511.log

./scripts/check_buildroot_arm64_lane.sh \
  2>&1 | tee build/verification/smmu-pri-response-ssid-qualifier-lane-20260511.log
```

## Expected result

The slice remains a functional compliance increment. It does not claim full
SMMUv3 compliance while packet-level PCIe ATS/PRI transport, complete endpoint
ATC recovery, upstream `arm-smmu-v3` lifecycle parity, full RME/GPT/GPC policy,
and complete Secure/Realm lifecycle parity remain open.
