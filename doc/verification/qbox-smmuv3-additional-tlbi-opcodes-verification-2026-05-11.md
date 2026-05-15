# QBox SMMUv3 additional TLBI opcode verification

- Date: 2026-05-11
- Scope: `/build/qbox_dev`
- Slice: SMMU-COMP-020/040 additional TLBI opcode slice
- Ground truth: `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
  lists `CMD_TLBI_EL3_ALL`, `CMD_TLBI_EL3_VA`, `CMD_TLBI_EL2_ALL`,
  `CMD_TLBI_EL2_ASID`, `CMD_TLBI_EL2_VA`, `CMD_TLBI_EL2_VAA`,
  `CMD_TLBI_S12_VMALL`, `CMD_TLBI_S2_IPA`, and `CMD_TLBI_NSNH_ALL` in the
  architected command opcode table; `sources/smmu/cpp/include/smmu/types.h`
  provides the same opcode values in the reference `CommandType` enum.
- Result: PASS for this modeled additional TLBI opcode slice. Full SMMUv3
  compliance remains blocked by the open items below.

## What changed

- Apollo TBU now recognizes the additional architected TLBI opcodes used by the
  reference model: `TLBI_EL3_*`, `TLBI_EL2_*`, `TLBI_S12_VMALL`,
  `TLBI_S2_IPA`, and `TLBI_NSNH_ALL`.
- Address-based TLBI commands are classified through `cmdq_opcode_is_address_tlbi`
  before range reserved-field validation and invalidation dispatch.
- The modeled side effects now cover security-state-wide invalidation,
  VMID-scoped invalidation, ASID+VMID invalidation, and VMID-qualified range
  invalidation for the new opcodes.
- `CmdqAdditionalTlbiOpcodesInvalidateModeledAts` fixes the behavior in
  component tests with representative NSNH, S12, S2 IPA, EL2 ASID, and EL2 VAA
  commands.

## Verification evidence

| Check | Evidence | Result |
| --- | --- | --- |
| Focused QBox component build | `build/verification/smmu-additional-tlbi-build-20260511.log` | PASS: `Built target apollo-smmu-tbu-tests` |
| Focused SMMU TBU CTest | `build/verification/smmu-additional-tlbi-ctest-20260511.log` | PASS: `100% tests passed, 0 tests failed out of 1` |
| Focused additional TLBI gTest | `build/verification/smmu-additional-tlbi-gtest-20260511.log` | PASS: `CmdqAdditionalTlbiOpcodesInvalidateModeledAts` |
| Static/syntax/checker bundle | `build/verification/smmu-additional-tlbi-static-20260511.log` | PASS: `SUMMARY {"pass": 717}` and `full_smmuv3_compliance=not_claimed` |
| Buildroot/QBox lane contract | `build/verification/smmu-additional-tlbi-lane-20260511.log` | PASS: lane contract completed |
| Final closure replay | `build/verification/smmu-additional-tlbi-final-closure-check-20260511.log` | PASS: `PASS: final additional TLBI closure checks completed` |

## Component coverage

- `TLBI_NSNH_ALL` clears modeled non-secure ATS/TLB entries for the selected
  command security state.
- `TLBI_S12_VMALL` clears modeled ATS/TLB entries for the selected VMID while
  preserving other VMIDs.
- `TLBI_S2_IPA` clears a VMID-qualified address range while preserving entries
  outside the range or under a different VMID.
- `TLBI_EL2_ASID` clears only entries matching both ASID and VMID.
- `TLBI_EL2_VAA` clears a VMID-qualified address range across ASIDs.

## Remaining blockers

This closes the previously open modeled additional-TLBI-opcode coverage gap for
representative NSNH/EL2/EL3/S12/S2 command forms, but it is not byte-exact full
Arm TLBI parity. Full compliance still requires security-state encodings for the
remaining Secure/Realm command variants, full TTL/Leaf/RIL reference-vector
matrices, full Secure/Realm endpoint acceptance, complete event-matrix coverage,
RME/GPT/GPC behavior, and upstream `arm-smmu-v3` lifecycle parity.
