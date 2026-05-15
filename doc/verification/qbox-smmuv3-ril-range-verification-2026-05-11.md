# QBox SMMUv3 IDR3.RIL Linux range-command verification

- Date: 2026-05-11
- Scope: `/build/qbox_dev`
- Slice: SMMU-COMP-020/040/080 IDR3.RIL Linux range-command stress slice
- Ground truth: `sources/smmu/rust/smmu/src/smmu/mod.rs` documents
  `SMMU_IDR3.RIL` bit 10 as range-based invalidation support, and QEMU's
  `sources/qemu/hw/arm/smmuv3-internal.h` models `IDR3.RIL` at bit 10.
- Result: PASS for this modeled IDR3.RIL Linux range-command stress slice. Full SMMUv3 compliance remains blocked by the open items below.

## What changed

- Apollo TBU now advertises `ARCH_IDR3_RIL` in `SMMUV3_IDR3` alongside MPAM.
- The Linux Apollo Hexagon probe expects `APOLLO_SMMUV3_ARCH_IDR3_RIL` and the
  updated `APOLLO_SMMUV3_ARCH_IDR3` value.
- The >64KB SG DMA stress path now issues a guest-visible `CMD_TLBI_NH_VA`
  range invalidation with `TG=4K`, `NUM=31`, and `Leaf=1` after DMA traffic has
  populated modeled ATS/TLB state.
- The QBox guest smoke requires the Linux log marker
  `SMMUv3 RIL TLBI_NH_VA range selftest ok`.

## Verification evidence

| Check | Evidence | Result |
| --- | --- | --- |
| Focused QBox component build | `build/verification/smmu-ril-range-build-20260511.log` | PASS: `Built target apollo-smmu-tbu-tests` |
| Focused SMMU TBU CTest | `build/verification/smmu-ril-range-ctest-20260511.log` | PASS: `100% tests passed, 0 tests failed out of 1` |
| Focused IDR3.RIL gTest | `build/verification/smmu-ril-range-gtest-20260511.log` | PASS: `MpamDiscoveryAdvertisesVmsPrerequisites` and `CmdqTlbiRangeInvalidatesModeledAtsSpan` |
| Linux incremental build | `build/verification/smmu-ril-range-linux-build-20260511.log` | PASS: `Linux Image: /build/qbox_dev/build/linux-a710/arch/arm64/boot/Image` |
| Artifact staging | `build/verification/smmu-ril-range-stage-20260511.log` | PASS: staged Linux + Buildroot artifacts |
| Static/syntax/checker bundle | `build/verification/smmu-ril-range-static-20260511.log` | PASS: `SUMMARY {"pass": 710}` and `full_smmuv3_compliance=not_claimed` |
| Buildroot/QBox lane contract | `build/verification/smmu-ril-range-lane-20260511.log` | PASS |
| Guest Hexagon IREE smoke | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-ril-range.driver.log` | PASS: `SMMUv3 RIL TLBI_NH_VA range selftest ok` and `1x1x2x2xf32=[[[54 63][90 99]]]` |

## Remaining blockers

This slice advertises and guest-stresses the modeled RIL range path, but it is
not full TLBI parity. Full compliance still requires additional TLBI opcodes and
security-state encodings, byte-exact Arm reference vectors for all TTL/Leaf/RIL
combinations, full Secure/Realm endpoint acceptance, complete event-matrix
coverage, RME/GPT/GPC behavior, and upstream `arm-smmu-v3` lifecycle parity.
