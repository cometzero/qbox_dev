# QBox SMMUv3 TLBI TTL/Leaf hint verification

- Date: 2026-05-11
- Scope: `/build/qbox_dev`
- Slice: SMMU-COMP-020/040 TLBI TTL/Leaf hint functional slice
- Ground truth: `sources/smmu/wiki/concepts/command-formats.md` records that
  address-based TLBI commands carry `TTL`, `TG`, and `Leaf` hints, and that
  `TG == 0b00` means no range invalidation and no TTL hint.
- Result: PASS for this TLBI TTL/Leaf hint slice. Full SMMUv3 compliance
  remains blocked by the open items below.

## What changed

- The Apollo TBU now decodes modeled address-based TLBI `TTL` and `Leaf` fields
  in addition to the existing `NUM`/`SCALE`/`TG` range fields.
- The model records the most recently consumed TLBI `TG`, effective `TTL`, and
  `Leaf` values for verification and future level-aware invalidation work.
- When `TG == 0`, the model still performs the single-page invalidation but
  records effective `TTL=0`, matching the no-TTL-hint behavior for non-range
  commands.

## Verification evidence

| Check | Evidence | Result |
| --- | --- | --- |
| Focused QBox component build | `build/verification/smmu-tlbi-ttl-leaf-build-20260511.log` | PASS: `Built target apollo-smmu-tbu-tests` |
| Focused SMMU TBU CTest | `build/verification/smmu-tlbi-ttl-leaf-ctest-20260511.log` | PASS: `100% tests passed, 0 tests failed out of 1` |
| Static/syntax/checker bundle | `build/verification/smmu-tlbi-ttl-leaf-postguest-closure-check-20260511.log` | PASS: `SUMMARY {"pass": 700}` and `full_smmuv3_compliance=not_claimed` |
| Buildroot/QBox lane contract | `build/verification/smmu-tlbi-ttl-leaf-postguest-lane-20260511.log` | PASS |
| Guest Hexagon IREE smoke | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-tlbi-ttl-leaf.driver.log` | PASS: `1x1x2x2xf32=[[[54 63][90 99]]]` |

## Component coverage

- `CmdqTlbiTtlLeafHintsFollowRangeTg` verifies a 4K range TLBI records
  `TG=4K`, the supplied `TTL`, and `Leaf=1` while invalidating the modeled ATS
  span.
- The same test verifies a `TG=0` single-page TLBI suppresses effective TTL
  accounting (`TTL=0`) while preserving `Leaf=1` accounting and invalidating the
  targeted page.

## Remaining blockers

This remains a hint-accounting slice, not full level-aware TLBI parity. Full Arm
parity still requires RIL feature advertisement with Linux range-command stress,
level-aware invalidation semantics for TTL/Leaf, additional TLBI encodings,
complete reference-vector parity, Secure/Realm endpoint acceptance, complete
event-matrix coverage, RME/GPT/GPC behavior, and upstream `arm-smmu-v3`
lifecycle parity.
