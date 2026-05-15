# QBox SMMUv3 STE/CD Reserved Encoding Verification - 2026-05-10

## Scope

This report records the SMMU-COMP-030 follow-up functional slice for modeled
STE/CD reserved-bit and illegal-encoding validation in the Apollo SMMU TBU.

This is not full Arm SMMUv3 compliance. It covers the local modeled STE/CD
fields currently consumed by QBox and leaves endpoint PASID/SSID plumbing,
byte-exact event/fault record layouts, Linux `arm-smmu-v3` generated CD
invalidation, complete Arm reserved-field parity across all STE/CD formats, and
external reference-vector parity open.

## Implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - advertises `FEATURE_ARCH_RESERVED_ENCODING_CHECKS`;
  - rejects unsupported `STE.Config` with `illegal STE.Config encoding`;
  - rejects modeled reserved bits in STE words with `reserved STE encoding`;
  - rejects modeled reserved bits in CD words with `reserved CD encoding`;
  - rejects illegal `S1DSS=0x3` with `illegal S1DSS encoding`;
  - rejects modeled 64K-L2 CD L1 reserved bits with `reserved CD L1 encoding`.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  adds `ArchitectedSteCdReservedEncodingFaults` negative vectors for illegal
  STE config, reserved STE words, illegal S1DSS, reserved CD words, and reserved
  64K-L2 CD L1 descriptors.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh` gate the new modeled
  reserved/illegal encoding coverage.

## Evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Component build | PASS | `build/verification/apollo-smmuv3-reserved-encoding-build-20260510.log`: `Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests` |
| Component CTest | PASS | `build/verification/apollo-smmuv3-reserved-encoding-ctest-20260510.log`: `100% tests passed, 0 tests failed out of 1` |
| Platform build | PASS | `build/verification/qbox-platform-smmu-reserved-encoding-20260510.log`: `QBox Buildroot platform runtime built in /build/qbox_dev/sources/qbox/build` |
| Guest smoke | PASS | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-reserved-encoding.driver.log`: `PASS: QBox guest IREE Hexagon tiny-CNN output matched`; runtime log includes `features=0xffff` |
| Static/checker/lane | PASS | `build/verification/smmu-reserved-encoding-static-final-20260510.log`: shell/Python syntax passed; SMMUv3 checker `SUMMARY {"pass": 157}`; Buildroot lane passed; `git diff --check` passed for superproject, `sources/qbox`, and `sources/linux`. |

## Remaining blockers

- Endpoint-derived PASID/SSID plumbing.
- Byte-exact SMMUv3 event/fault records.
- Linux `arm-smmu-v3` generated CD invalidation.
- Complete Arm reserved-field parity for all STE/CD formats.
- External reference-vector parity against the `sources/smmu` ground-truth tree.
- Full multi-master platform runtime with real endpoint stream/PASID traffic.
- True upstream IREE source integration for dynamic HAL device registration.
