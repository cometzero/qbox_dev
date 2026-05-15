# QBox SMMUv3 Secure PRI response reserved-code verification (2026-05-11)

This report captures the SMMU-COMP-060 Secure PRI response reserved-code slice.

## Scope

The bounded slice extends the reserved `CMD_PRI_RESP` response-code validation
from the Non-secure CMDQ path to the Secure S_CMDQ path. A Secure command queue
entry with an unsupported response encoding must halt at the offending command,
report `S_CMDQ_CONS.CERROR_ILL`, and preserve the pending PRG instead of
issuing a modeled PRI response.

Implemented/verified behavior:

- Secure `ARCH_CMD_PRI_RESP` reuses `arch_pri_response_valid()` before calling
  `complete_prg()`.
- Reserved Secure response codes set Secure `S_CMDQ_CONS.CERROR_ILL` through
  `set_secure_cmdq_cerror()`.
- The Secure command path leaves `S_CMDQ_CONS.RD` at the offending command and
  raises Secure `S_GERROR.CMDQ_ABORT`.
- The pending PRG is not cleared and normal PRI response accounting is not
  incremented.

## Ground truth

- `sources/smmu/wiki/concepts/pcie-ats-pri.md`
  - `§8.3 PRG Response Message Codes`
  - Valid values: `0b0000`, `0b0001`, `0b1111`
- `sources/smmu/TASKS_OPERATION.md`
  - Notes that CMD_PRI_RESP on Secure Command queue is architecturally
    optional/feature-gated; QBox now keeps the modeled Secure command path's
    reserved-response behavior aligned with the Non-secure path.

## Static evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - `secure-pri-resp-reserved-response`
  - `set_secure_cmdq_cerror(ARCH_CMDQ_CERROR_ILL, ...)`
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - `SecureCmdPriRespReservedResponseSetsCerrorIll`

## Verification commands

```bash
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)" \
  2>&1 | tee build/verification/smmu-secure-pri-response-reserved-code-build-20260511.log

./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests \
  --gtest_filter='*SecureCmdPriRespReservedResponseSetsCerrorIll*:*CmdPriRespReservedResponseSetsCerrorIll*' \
  2>&1 | tee build/verification/smmu-secure-pri-response-reserved-code-gtest-20260511.log

ctest --test-dir sources/qbox/build --output-on-failure -R apollo-smmu-tbu-tests \
  2>&1 | tee build/verification/smmu-secure-pri-response-reserved-code-ctest-20260511.log

python3 scripts/check_qbox_smmuv3_compliance.py \
  --json build/verification/smmu-secure-pri-response-reserved-code-static-20260511.json \
  2>&1 | tee build/verification/smmu-secure-pri-response-reserved-code-static-20260511.log

./scripts/check_buildroot_arm64_lane.sh \
  2>&1 | tee build/verification/smmu-secure-pri-response-reserved-code-lane-20260511.log
```

## Expected result

The slice remains a functional compliance increment. It does not claim full
SMMUv3 compliance while packet-level PCIe ATS/PRI transport, complete endpoint
ATC recovery, upstream `arm-smmu-v3` lifecycle parity, full RME/GPT/GPC policy,
and complete Secure/Realm lifecycle parity remain open.
