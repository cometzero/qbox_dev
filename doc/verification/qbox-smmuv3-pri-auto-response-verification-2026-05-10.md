# QBox SMMUv3 PRI Auto-Response Verification - 2026-05-10

## Scope

SMMU-COMP-060 PRI auto-response functional slice.

This slice changes the Apollo SMMUv3 TBU so protocol-level PRI requests that
cannot be made visible in PRIQ receive a modeled automatic failure response and
do not leave stale pending PRGs behind. Covered unavailable cases are PRIQ full
or overflow, CR0.PRIQEN-disabled, and active `SMMU_GERROR.PRIQ_ABT_ERR`.

This remains a functional compliance slice. It does not implement byte-exact PCIe
PPR/PRG response packets, PASID-prefix response selection, Stop-PASID markers,
secure/realm PRI routing, or interleaved multi-entry PRG lifecycle semantics.

## Ground truth

- `sources/smmu/wiki/concepts/pcie-ats-pri.md` documents that PRIQ overflow
toggles `SMMU_PRIQ_PROD.OVFLG`, Last==1 PPRs receive automatic PRG responses,
and disabled PRIQ or active `PRIQ_ABT_ERR` returns automatic failure.
- `sources/smmu/cpp/src/smmu/smmu.cpp` contains the reference
`submitPageRequest()` behavior for effective PRIQEN, overflow-active, and
Last==1 auto-response handling.

## Implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  adds `FEATURE_ARCH_PRI_AUTO_RESPONSE`.
- `push_pri_protocol_record()` now detects disabled PRIQ, active `PRIQ_ABT_ERR`,
  and unwritable PRIQ and calls `record_pri_auto_response()`.
- `record_pri_auto_response()` records response counters, captures the last PRG
  and response code, and clears the matching pending PRG.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc` adds
  `PriProtocolAutoRespondsOnOverflowDisabledAndAbort`.
- `sources/linux/drivers/soc/apollo/apollo-hexagon-test.c` requires the new
  feature bit in the guest feature probe.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh` gate the slice.

## Evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Component build | PASS | `build/verification/apollo-smmu-tbu-pri-auto-response-build-20260510.log`: `Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`. |
| Component CTest | PASS | `build/verification/apollo-smmu-tbu-pri-auto-response-ctest-20260510.log`: `100% tests passed, 0 tests failed out of 1`; `PriProtocolAutoRespondsOnOverflowDisabledAndAbort` verifies overflow, disabled, and `PRIQ_ABT_ERR` PRI auto-response cases. |
| Linux build | PASS | `build/verification/qbox-linux-smmu-pri-auto-response-20260510.log`: `Linux Image: /build/qbox_dev/build/linux-a710/arch/arm64/boot/Image`. |
| Artifact staging | PASS | `build/verification/stage-artifacts-smmu-pri-auto-response-20260510.log`: `Staged Linux + Buildroot artifacts into /build/qbox_dev/sources/qbox/platforms/buildroot/fw/Artifacts`. |
| Platform build | PASS | `build/verification/qbox-platform-smmu-pri-auto-response-20260510.log`: `QBox Buildroot platform runtime built in /build/qbox_dev/sources/qbox/build`. |
| Guest smoke | PASS | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-pri-auto-response.driver.log`: `PASS: QBox guest IREE Hexagon tiny-CNN output matched`; runtime log records `features=0x3ffffff`, `architected PRI auto-response`, and `1x1x2x2xf32=[[[54 63][90 99]]]`. |
| Static/checker/lane | PASS | `build/verification/smmu-pri-auto-response-static-final-20260510.log`: `PASS  tbu:pri-auto-response`, `SUMMARY`, and lane check passed. |

## Remaining blockers

- Full PCIe PRI PPR and PRG response packet encoding is not implemented.
- PASID-prefix response selection, Stop-PASID markers, and secure/realm PRI
  routing remain open.
- Multi-entry PRG interleaving and endpoint-visible response delivery remain
  modeled through counters rather than a packet-level endpoint protocol.
