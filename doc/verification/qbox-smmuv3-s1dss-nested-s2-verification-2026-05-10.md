# QBox SMMUv3 nested S1DSS-bypass S2 verification - 2026-05-10

## Scope

Functional SMMU-COMP-030/040 slice for nested configurations where the stream
entry selects `STE.S1DSS=BYPASS` and no SubstreamID/PASID is selected. The
Apollo TBU now keeps the existing S1-only identity-bypass behavior, but for
`STE.Config=NESTED` it treats the bypassed S1 result as an IPA and applies the
stage-2 descriptor walk from the STE S2 table pointer.

This is not a full SMMUv3 compliance claim. Endpoint PASID/SSID plumbing,
full Arm reserved-matrix parity, byte-exact event records, Linux arm-smmu-v3 generated
CD invalidation, and full reference-vector parity remain open.

## Changed implementation surfaces

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - The S1DSS bypass path now detects `ARCH_STE_CFG_NESTED` and logs
    `architectural nested S1DSS bypass stage-2 walk`.
  - Nested bypass uses `arch_descriptor_walk()` with the S2 table pointer from
    `ARCH_STE_S2TTB_MASK` instead of returning identity as the final PA.
  - S1-only S1DSS bypass remains identity translated for compatibility tests.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - `ArchitectedWalkerStage2AndNestedMatrix` now includes the `bypass_s2ttb`
    vector for nested S1DSS-bypass/S2 translation.
  - The existing negative S2 page-invalid replay path is restored to the normal
    nested STE/CD setup before fault injection, preventing test-state bleed.

## Verification evidence

| Command | Evidence | Result |
| --- | --- | --- |
| `cmake --build sources/qbox/build --target apollo-smmu-tbu-tests apollo_smmu_tbu -j$(nproc)` | `build/verification/apollo-smmuv3-s1dss-nested-s2-build-20260510.log` | PASS: `Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests` |
| `ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure` | `build/verification/apollo-smmuv3-s1dss-nested-s2-ctest-20260510.log` | PASS: `100% tests passed, 0 tests failed out of 1` |
| `scripts/check_qbox_smmuv3_compliance.py --self-test-negative --json build/verification/qbox-smmuv3-compliance-s1dss-nested-s2-final-20260510.json` | `build/verification/smmu-s1dss-nested-s2-static-final-20260510.log` | PASS: `SUMMARY {"pass": 147}` and Buildroot lane PASS. |
| `./scripts/check_buildroot_arm64_lane.sh` | `build/verification/smmu-s1dss-nested-s2-static-final-20260510.log` | PASS: `SUMMARY {"pass": 147}` and Buildroot lane PASS. |
| `./scripts/build_qbox_buildroot_platform.sh` | `build/verification/qbox-platform-smmu-s1dss-nested-s2-20260510.log` | PASS: `QBox Buildroot platform runtime built`. |
| `./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh` | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-s1dss-nested-s2.driver.log` | PASS: tiny-CNN output matched `1x1x2x2xf32=[[[54 63][90 99]]]`. |

## Remaining blockers

- Full PASID/SSID propagation from endpoint transactions into CD-table lookup.
- Reserved-bit and illegal encoding validation across STE/CD formats.
- Byte-exact SMMUv3 event/fault queue records for S1DSS terminate and nested S2
  faults.
- Linux `arm-smmu-v3` driven CD invalidation and replay coverage.
- Full Arm reference-vector parity across start levels, attributes, permissions,
  faults, and S2 encodings.
