# QBox SMMUv3 S1DSS policy verification - 2026-05-10

## Scope

Functional SMMU-COMP-030 slice for explicit context-descriptor table STEs when
no SubstreamID/PASID is selected. The Apollo TBU now models:

- `ARCH_STE_S1DSS_SSID0`: preserve CD0 fallback compatibility.
- `ARCH_STE_S1DSS_TERMINATE`: report an S1 context-descriptor fault.
- `ARCH_STE_S1DSS_BYPASS`: record `m_arch_last_cd_bypass` and perform an
  identity S1-bypass translation in the component model.

This is not a full SMMUv3 compliance claim. Nested S2 translation after S1DSS
bypass, endpoint PASID plumbing, byte-exact event records, reserved-bit
validation, and Linux arm-smmu-v3 generated CD invalidation remain open.

## Changed implementation surfaces

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - `arch_cd_address()` now returns a bypass decision for no-SSID explicit
    CD-table STEs.
  - `m_arch_last_cd_bypass` is exposed through `REG_ARCH_CD_DETAIL` bit 31.
  - S1DSS terminate records `ARCH_FAULT_CD_INVALID` at stage S1.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - `ArchitectedContextDescriptorTableIndexesSelectedSsid` covers
    `ARCH_STE_S1DSS_TERMINATE` and `ARCH_STE_S1DSS_BYPASS`.

## Verification evidence

| Command | Evidence | Result |
| --- | --- | --- |
| `cmake --build sources/qbox/build --target apollo-smmu-tbu-tests apollo_smmu_tbu -j$(nproc)` | `build/verification/apollo-smmuv3-s1dss-policy-build-20260510.log` | PASS: `Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests` |
| `ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure` | `build/verification/apollo-smmuv3-s1dss-policy-ctest-20260510.log` | PASS: `100% tests passed, 0 tests failed out of 1` |
| `scripts/check_qbox_smmuv3_compliance.py --self-test-negative --json build/verification/qbox-smmuv3-compliance-s1dss-policy-final-20260510.json` | `build/verification/smmu-s1dss-policy-static-final-20260510.log` | PASS: checklist and negative self-test passed. |
| `./scripts/check_buildroot_arm64_lane.sh` | `build/verification/smmu-s1dss-policy-static-final-20260510.log` | PASS: Buildroot ARM64 lane contracts passed. |
| `./scripts/build_qbox_buildroot_platform.sh` | `build/verification/qbox-platform-smmu-s1dss-policy-20260510.log` | PASS: `QBox Buildroot platform runtime built`. |
| `./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh` | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-s1dss-policy.driver.log` | PASS: tiny-CNN output matched `1x1x2x2xf32=[[[54 63][90 99]]]`. |

## Remaining blockers

- Full PASID/SSID propagation from endpoint transactions into CD-table lookup.
- Stage-2 translation after an S1DSS bypass decision in nested configurations.
- Byte-exact SMMUv3 event/fault queue records for S1DSS terminate.
- Reserved-bit and illegal encoding validation across STE/CD formats.
- Linux `arm-smmu-v3` driven CD invalidation and replay coverage.
