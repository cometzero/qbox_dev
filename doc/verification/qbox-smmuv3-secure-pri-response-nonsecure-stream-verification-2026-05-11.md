# QBox SMMUv3 Secure PRI response Non-secure StreamID verification (2026-05-11)

This report captures the SMMU-COMP-060 Secure CMD_PRI_RESP Non-secure StreamID slice.

## Scope

The bounded slice aligns the Secure command-queue `CMD_PRI_RESP` path with the
architectural rule that an accepted Secure CMDQ PRI response targets a
Non-secure StreamID. `CMD_PRI_RESP` has no SSec selector, so a guest-visible
RES0 bit[10] value must not retag the PRI response as Secure.

Implemented/verified behavior:

- Secure CMDQ command decode uses `secure_cmdq_command_security_state()`.
- Accepted `ARCH_CMD_PRI_RESP` from `S_CMDQ` is recorded as
  `ARCH_SECURITY_NONSECURE` even when the `ARCH_CMDQ_SSEC` bit is set.
- The command consumes the matching Non-secure pending PRG, advances
  `S_CMDQ_CONS.RD`, and does not raise Secure `S_GERROR.CMDQ_ABORT`.
- Existing Secure reserved-response validation remains intact and still reports
  `S_CMDQ_CONS.CERROR_ILL` before clearing a pending PRG.

## Ground truth

- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
  - `§4.5.2 CMD_PRI_RESP(StreamID, SubstreamID, SSV, PRGIndex, Resp)`
  - If the command is accepted from a Secure command queue, the StreamID is
    considered Non-secure.
- `sources/smmu/wiki/concepts/command-formats.md`
  - `CMD_PRI_RESP` fields are StreamID, SubstreamID, SSV, PRGIndex, and Resp;
    there is no SSec selector for this command.

## Static evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - `secure_cmdq_command_security_state()`
  - `opcode == ARCH_CMD_PRI_RESP`
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - `SecureCmdPriRespIgnoresSsecAndTargetsNonSecure`

## Verification commands

```bash
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)" \
  2>&1 | tee build/verification/smmu-secure-pri-response-nonsecure-stream-build-20260511.log

./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests \
  --gtest_filter='*SecureCmdPriRespIgnoresSsecAndTargetsNonSecure*:*SecureCmdPriRespReservedResponseSetsCerrorIll*:*CmdPriRespReservedResponseSetsCerrorIll*' \
  2>&1 | tee build/verification/smmu-secure-pri-response-nonsecure-stream-gtest-20260511.log

ctest --test-dir sources/qbox/build --output-on-failure -R apollo-smmu-tbu-tests \
  2>&1 | tee build/verification/smmu-secure-pri-response-nonsecure-stream-ctest-20260511.log

python3 scripts/check_qbox_smmuv3_compliance.py \
  --json build/verification/smmu-secure-pri-response-nonsecure-stream-static-20260511.json \
  2>&1 | tee build/verification/smmu-secure-pri-response-nonsecure-stream-static-20260511.log

./scripts/check_buildroot_arm64_lane.sh \
  2>&1 | tee build/verification/smmu-secure-pri-response-nonsecure-stream-lane-20260511.log
```

## Expected result

The slice remains a functional compliance increment. It does not claim full
SMMUv3 compliance while packet-level PCIe ATS/PRI transport, complete endpoint
ATC recovery, upstream `arm-smmu-v3` lifecycle parity, full RME/GPT/GPC policy,
and complete Secure/Realm lifecycle parity remain open.
