# QBox SMMUv3 TLBI range reserved encoding verification

- Date: 2026-05-11
- Scope: `/build/qbox_dev`
- Slice: SMMU-COMP-020/040 TLBI range reserved-encoding functional slice
- Ground truth: `sources/smmu/wiki/concepts/command-formats.md` records that
  `TG == 0b00` means no range invalidation and `NUM == SCALE == 0, TG != 0`
  is Reserved and must produce `CERROR_ILL`.
- Result: PASS for this TLBI range reserved-encoding slice. Full SMMUv3
  compliance remains blocked by the open items below.

## What changed

- The Apollo TBU now detects the modeled address-based TLBI reserved range
  encoding where `TG != 0`, `NUM == 0`, and `SCALE == 0`.
- Non-secure CMDQ `TLBI_NH_VA`/`TLBI_NH_VAA` with that encoding now pauses the
  queue at the failing command and reports `CMDQ_CONS.CERROR_ILL`.
- Secure CMDQ applies the same reserved-encoding rejection through the Secure
  `S_CMDQ_CONS`/`S_GERROR` bank.
- The illegal command is not counted as a TLBI and does not invalidate modeled
  ATS/TLB entries.

## Verification evidence

| Check | Evidence | Result |
| --- | --- | --- |
| Focused QBox component build | `build/verification/smmu-tlbi-range-reserved-build-20260511.log` | PASS: `Built target apollo-smmu-tbu-tests` |
| Focused SMMU TBU CTest | `build/verification/smmu-tlbi-range-reserved-ctest-20260511.log` | PASS: `100% tests passed, 0 tests failed out of 1` |
| Static/syntax/checker bundle | `build/verification/smmu-tlbi-range-reserved-static-20260511.log` | PASS: `SUMMARY {"pass": 695}` and `full_smmuv3_compliance=not_claimed` |
| Buildroot/QBox lane contract | `build/verification/smmu-tlbi-range-reserved-lane-20260511.log` | PASS |
| Guest Hexagon IREE smoke | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-tlbi-range-reserved.driver.log` | PASS: `1x1x2x2xf32=[[[54 63][90 99]]]` |

## Component coverage

- `CmdqTlbiRangeReservedEncodingIsIllegal` verifies Non-secure CMDQ rejects the
  reserved range encoding with `CERROR_ILL`, leaves `CMDQ_CONS.RD` at the
  failing entry, raises the modeled GERROR active bit, preserves ATS/TLB state,
  and does not increment the modeled TLBI counter.
- The same test verifies the Secure CMDQ path rejects the same reserved encoding
  through Secure `S_CMDQ_CONS`/`S_GERROR` while preserving Secure ATS/TLB state
  and SSec-derived Secure command-state accounting.

## Remaining blockers

This remains a modeled reserved-encoding slice. Full Arm parity still requires
remaining TTL/Leaf/RIL interactions, additional TLBI encodings, complete
reference-vector parity, Secure/Realm endpoint acceptance, the complete event
matrix, RME/GPT/GPC behavior, and upstream `arm-smmu-v3` lifecycle parity.
