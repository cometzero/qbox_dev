# QBox SMMUv3 Secure-only TLBI opcode verification

- Date: 2026-05-11
- Scope: `/build/qbox_dev`
- Slice: SMMU-COMP-020/040 Secure-only TLBI opcode slice
- Ground truth: `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
  lists `CMD_TLBI_S_EL2_ALL`, `CMD_TLBI_S_EL2_ASID`,
  `CMD_TLBI_S_EL2_VA`, `CMD_TLBI_S_EL2_VAA`, `CMD_TLBI_S_S12_VMALL`,
  `CMD_TLBI_S_S2_IPA`, and `CMD_TLBI_SNH_ALL`; the local reference enum in
  `sources/smmu/cpp/include/smmu/types.h` uses the same opcode values.
- Result: PASS for this modeled Secure-only TLBI opcode slice. Full SMMUv3
  compliance remains blocked by the open items below.

## What changed

- Apollo TBU now recognizes Secure-only TLBI command opcodes for S-EL2,
  Secure stage-1+2, Secure stage-2 IPA, and Secure non-Hyp all-scope
  invalidation.
- `cmdq_opcode_is_secure_tlbi()` routes those opcodes as Secure CMDQ-only
  commands and rejects them with `CERROR_ILL` when issued on the Non-secure
  CMDQ.
- Secure CMDQ execution forces Secure security-state targeting for those
  opcodes instead of relying on the `SSec` selector used by shared CFGI/TLBI/ATC
  command forms.
- `SecureOnlyTlbiOpcodesRequireSecureCmdqAndTargetSecureState` verifies
  Non-secure rejection plus Secure ASID, Secure S2 IPA range, and Secure NH
  all-scope invalidation side effects.

## Verification evidence

| Check | Evidence | Result |
| --- | --- | --- |
| Focused QBox component build | `build/verification/smmu-secure-tlbi-build-20260511.log` | PASS: `Built target apollo-smmu-tbu-tests` |
| Focused SMMU TBU CTest | `build/verification/smmu-secure-tlbi-ctest-20260511.log` | PASS: `100% tests passed, 0 tests failed out of 1` |
| Focused Secure TLBI gTest | `build/verification/smmu-secure-tlbi-gtest-20260511.log` | PASS: `SecureOnlyTlbiOpcodesRequireSecureCmdqAndTargetSecureState` |
| Static/syntax/checker bundle | `build/verification/smmu-secure-tlbi-static-20260511.log` | PASS: `SUMMARY {"pass": 724}` and `full_smmuv3_compliance=not_claimed` |
| Buildroot/QBox lane contract | `build/verification/smmu-secure-tlbi-lane-20260511.log` | PASS: lane contract completed |
| Final closure replay | `build/verification/smmu-secure-tlbi-final-closure-check-20260511.log` | PASS: `PASS: final Secure TLBI closure checks completed` |

## Component coverage

- Non-secure CMDQ `CMD_TLBI_SNH_ALL` raises `CERROR_ILL` and preserves modeled
  Secure and Non-secure ATS/TLB entries.
- Secure CMDQ `CMD_TLBI_S_EL2_ASID` clears only Secure ASID/VMID-matched
  entries and preserves Non-secure entries with the same tags.
- Secure CMDQ `CMD_TLBI_S_S2_IPA` clears a Secure VMID-qualified range while
  preserving Non-secure entries in the same range.
- Secure CMDQ `CMD_TLBI_SNH_ALL` clears remaining Secure entries while
  preserving Non-secure entries.

## Remaining blockers

This closes the modeled Secure-only TLBI opcode coverage gap, but it is not full
Arm security-state or RME parity. Full compliance still requires Realm/RME
command encodings and GPT/GPC behavior, byte-exact TLBI TTL/Leaf/RIL reference
vectors for all encodings, full Secure/Realm endpoint acceptance, complete
event-matrix coverage, and upstream `arm-smmu-v3` lifecycle parity.
