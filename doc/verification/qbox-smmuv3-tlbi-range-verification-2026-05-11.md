# QBox SMMUv3 TLBI range invalidation verification

- Date: 2026-05-11
- Scope: `/build/qbox_dev`
- Slice: SMMU-COMP-020/040 TLBI range invalidation functional slice
- Result: PASS for this TLBI range invalidation functional slice. Full SMMUv3 compliance remains blocked by the open items below.

## What changed

- The Apollo TBU decodes modeled address-based TLBI `NUM`, `SCALE`, and `TG`
  range fields for `TLBI_NH_VA` and `TLBI_NH_VAA` commands.
- `TLBI_NH_VA` now invalidates ASID/VMID-qualified modeled ATS/TLB entries
  across the selected range instead of only the base page.
- `TLBI_NH_VAA` now invalidates VMID-qualified modeled ATS/TLB entries across
  the selected range.

## Verification evidence

| Check | Evidence | Result |
| --- | --- | --- |
| Focused QBox component build | `build/verification/smmu-tlbi-range-build-20260511.log` | PASS: `Built target apollo-smmu-tbu-tests` |
| Focused SMMU TBU CTest | `build/verification/smmu-tlbi-range-ctest-20260511.log` | PASS: `100% tests passed, 0 tests failed out of 1` |
| Static/syntax/checker bundle | `build/verification/smmu-tlbi-range-static-20260511.log` | PASS: `SUMMARY {"pass": 692}` and `full_smmuv3_compliance=not_claimed` |
| Buildroot/QBox lane contract | `build/verification/smmu-tlbi-range-lane-20260511.log` | PASS |
| Guest Hexagon IREE smoke | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-tlbi-range.driver.log` | PASS: `1x1x2x2xf32=[[[54 63][90 99]]]` |

## Component coverage

- `CmdqTlbiRangeInvalidatesModeledAtsSpan` verifies `TLBI_NH_VA` with a modeled
  4-page range invalidates only matching ASID/VMID entries inside the span.
- The same test verifies `TLBI_NH_VAA` with a modeled 2-page range invalidates
  all ASIDs for the selected VMID inside the span while preserving another VMID.

## Remaining blockers

This remains a modeled range-invalidation slice. Full Arm parity still requires
leaf/TTL/RIL reserved-field behavior, additional TLBI encodings, complete
reference-vector parity, and the broader full SMMUv3 compliance blockers tracked
in the checklist.
