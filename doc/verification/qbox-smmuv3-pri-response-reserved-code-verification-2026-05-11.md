# QBox SMMUv3 PRI response reserved-code verification (2026-05-11)

This report captures the SMMU-COMP-060 PRI response reserved-code slice.

## Scope

The bounded slice hardens `CMD_PRI_RESP` response-code validation. The local
SMMUv3 reference material under `sources/smmu` summarizes §8.3 PRG response
message codes as Success (`0b0000`), Invalid Request (`0b0001`), and Response
Failure (`0b1111`). QBox now rejects other modeled `CMD_PRI_RESP` response
codes before clearing any pending PRG.

Implemented/verified behavior:

- `arch_pri_response_valid()` accepts only `ARCH_PRI_RESP_ACCEPT`,
  `ARCH_PRI_RESP_REJECT`, and `ARCH_PRI_RESP_FAILURE`.
- Non-secure CMDQ `ARCH_CMD_PRI_RESP` with a reserved response code sets
  `CMDQ_CONS.CERROR_ILL`, raises `GERROR.CMDQ_ABORT`, leaves `CONS.RD` at the
  offending command, and preserves the pending PRG.
- Secure CMDQ uses the same validation path and reports Secure
  `S_CMDQ_CONS.CERROR_ILL` for reserved response codes.
- Reserved-code commands do not increment modeled PRI response counters and do
  not update normal completion metadata.

## Ground truth

- `sources/smmu/wiki/concepts/pcie-ats-pri.md`
  - `§8.3 PRG Response Message Codes`
  - Valid values: `0b0000`, `0b0001`, `0b1111`
- `sources/smmu/TASKS_BUGS.md`
  - `§4.5.2 | CMD_PRI_RESP`
  - Reserved response encodings require `CERROR_ILL` handling.

## Static evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - `arch_pri_response_valid`
  - `pri-resp-reserved-response`
  - `secure-pri-resp-reserved-response`
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - `CmdPriRespReservedResponseSetsCerrorIll`

## Verification commands

```bash
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)" \
  2>&1 | tee build/verification/smmu-pri-response-reserved-code-build-20260511.log

./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests \
  --gtest_filter='*CmdPriRespReservedResponseSetsCerrorIll*:*CmdPriRespHonorsSsidQualifier*:*CmdPriRespMatchesExactPrgOutOfOrder*' \
  2>&1 | tee build/verification/smmu-pri-response-reserved-code-gtest-20260511.log

ctest --test-dir sources/qbox/build --output-on-failure -R apollo-smmu-tbu-tests \
  2>&1 | tee build/verification/smmu-pri-response-reserved-code-ctest-20260511.log

python3 scripts/check_qbox_smmuv3_compliance.py \
  --json build/verification/smmu-pri-response-reserved-code-static-20260511.json \
  2>&1 | tee build/verification/smmu-pri-response-reserved-code-static-20260511.log

./scripts/check_buildroot_arm64_lane.sh \
  2>&1 | tee build/verification/smmu-pri-response-reserved-code-lane-20260511.log
```

## Expected result

The slice remains a functional compliance increment. It does not claim full
SMMUv3 compliance while packet-level PCIe ATS/PRI transport, complete endpoint
ATC recovery, upstream `arm-smmu-v3` lifecycle parity, full RME/GPT/GPC policy,
and complete Secure/Realm lifecycle parity remain open.
