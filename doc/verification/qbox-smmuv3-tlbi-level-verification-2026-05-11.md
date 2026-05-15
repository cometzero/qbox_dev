# QBox SMMUv3 TLBI TTL/Leaf level-aware verification

- Date: 2026-05-11
- Scope: `/build/qbox_dev`
- Slice: SMMU-COMP-020/040 TLBI TTL/Leaf level-aware invalidation slice
- Ground truth: `sources/smmu/wiki/concepts/command-formats.md` records that
  address-based TLBI commands carry `TG`, `TTL`, and `Leaf` hints, that
  `TG == 0b00` gives no range or TTL hint, and that `Leaf == 0` includes
  table-descriptor invalidation while `Leaf == 1` targets leaf entries.
- Result: PASS for this modeled level-aware slice. Full SMMUv3 compliance
  remains blocked by the open items below.

## What changed

- Modeled ATS/TLB entries now carry translation leaf level and granule metadata.
- `TLBI_NH_VA` and `TLBI_NH_VAA` use non-zero effective `TTL` plus `TG` to
  filter modeled leaf translation invalidations by cached level/granule.
- `TG == 0` still suppresses the effective TTL hint and performs the addressed
  page invalidation without level filtering.
- `Leaf == 0` now records separate table-walk cache invalidation accounting via
  `m_arch_last_cmd_table_invalidated` and `m_arch_cmd_table_invalidations`.

## Verification evidence

| Check | Evidence | Result |
| --- | --- | --- |
| Focused QBox component build | `build/verification/smmu-tlbi-level-build-20260511.log` | PASS: `Built target apollo-smmu-tbu-tests` |
| Focused SMMU TBU CTest | `build/verification/smmu-tlbi-level-ctest-20260511.log` | PASS: `100% tests passed, 0 tests failed out of 1` |
| Focused TLBI gTest | `build/verification/smmu-tlbi-level-gtest-20260511.log` | PASS: `CmdqTlbiTtlLeafHintsFollowRangeTg` |
| Static/syntax/checker bundle | `build/verification/smmu-tlbi-level-static-20260511.log` | PASS: `SUMMARY {"pass": 703}` and `full_smmuv3_compliance=not_claimed` |
| Buildroot/QBox lane contract | `build/verification/smmu-tlbi-level-lane-20260511.log` | PASS |
| Guest Hexagon IREE smoke | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-tlbi-level.driver.log` | PASS: `1x1x2x2xf32=[[[54 63][90 99]]]` |

## Component coverage

- A `TG=4K`, `TTL=2`, `Leaf=1` TLBI invalidates cached level-2 leaf entries
  inside the modeled range while preserving a same-tag level-3 entry in the
  same address range.
- A `TG=0`, `TTL=3`, `Leaf=1` TLBI suppresses TTL filtering and invalidates the
  addressed page.
- A `TG=4K`, `TTL=2`, `Leaf=0` TLBI invalidates matching level-2 leaves and
  records one modeled table-walk cache invalidation.

## Remaining blockers

This narrows the previous hint-accounting-only gap but is not full Arm TLBI
parity. Full compliance still requires RIL advertisement with Linux range-command
stress, additional TLBI opcodes/security-state encodings, byte-exact Arm
reference vectors for all TTL/Leaf combinations, full Secure/Realm endpoint
acceptance, complete event-matrix coverage, RME/GPT/GPC behavior, and upstream
`arm-smmu-v3` lifecycle parity.
