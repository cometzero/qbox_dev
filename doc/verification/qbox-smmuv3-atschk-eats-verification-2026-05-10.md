# QBox SMMUv3 ATSCHK/EATS Verification - 2026-05-10

## Scope

SMMU-COMP-060 functional slice for CR0.ATSCHK plus STE.EATS gating of
ATS Translation Requests.

This slice adds a dedicated `ARCH_CTRL_ATS_TRANSLATION_REQUEST` path in
the Apollo SMMUv3 TBU model. It rejects ATS Translation Requests with UR
and an `F_BAD_ATS_TREQ` event when SMMUEN is disabled, when effective
STE.EATS is disabled, and when split/DPT EATS encodings are used while
CR0.ATSCHK is clear. It accepts Full ATS when CR0.ATSCHK is enabled and
the stream/context/table walk succeeds.

This remains a functional slice, not full ATS/PRI compliance. Full
packet-level ATS, translated-transaction re-drive, secure stream routing,
REC_CFG_ATS/CR2 policy, EATS split-stage IPA return semantics, DPT
checks, endpoint ATC completion ordering, and upstream arm-smmu-v3
lifecycle coverage remain open.

## Implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  adds `FEATURE_ARCH_ATSCHK_EATS_GATES`,
  `ARCH_CTRL_ATS_TRANSLATION_REQUEST`, STE.EATS decoding,
  effective-EATS logic, `ARCH_FAULT_BAD_ATS_TREQ`, and `F_BAD_ATS_TREQ`
  event mapping.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  adds `AtsTranslationRequestHonorsCr0AtschkAndSteEats`.
- `sources/linux/drivers/soc/apollo/apollo-hexagon-test.c` adds a Linux
  boot probe that checks split-without-ATSCHK UR, EATS-disabled UR, and
  EATS-full success.
- `scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh` gates runtime
  on `features=0xfffff` and
  `SMMUv3 ATSCHK/EATS translation request selftest ok`.
- `scripts/check_qbox_smmuv3_compliance.py`,
  `scripts/check_buildroot_arm64_lane.sh`, and
  `doc/spec/qbox-smmuv3-compliance-checklist.md` record the new gate.

## Evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Component build | PASS | `build/verification/apollo-smmu-tbu-atschk-eats-build-20260510.log`: `Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`. |
| Component CTest | PASS | `build/verification/apollo-smmu-tbu-atschk-eats-ctest-20260510.log`: `100% tests passed, 0 tests failed out of 1`. |
| Checker preflight | PASS | `build/verification/qbox-smmuv3-compliance-atschk-eats-preflight-20260510.json`: checker includes `tbu:atschk-eats-gates` and `linux:atschk-eats-probe`; console preflight reported `SUMMARY {"pass": 202}`. |
| Linux build | PASS | `build/verification/qbox-linux-smmu-atschk-eats-20260510.log`: `CC drivers/soc/apollo/apollo-hexagon-test.o`, `Linux Image: /build/qbox_dev/build/linux-a710/arch/arm64/boot/Image`. |
| Artifact staging | PASS | `build/verification/stage-artifacts-smmu-atschk-eats-20260510.log`: staged Linux + Buildroot artifacts into QBox platform artifact directory. |
| QBox platform runtime build | PASS | `build/verification/qbox-platform-smmu-atschk-eats-20260510.log`: `QBox Buildroot platform runtime built in /build/qbox_dev/sources/qbox/build`. |
| Guest smoke | PASS | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-atschk-eats.driver.log`: `PASS: QBox guest IREE Hexagon tiny-CNN output matched`, `Expected: 1x1x2x2xf32=[[[54 63][90 99]]]`. |
| Runtime ATSCHK/EATS marker | PASS | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-atschk-eats.log`: records `features=0xfffff` and `SMMUv3 ATSCHK/EATS translation request selftest ok`. |
| Static/checker/lane | PASS | `build/verification/smmu-atschk-eats-static-final-20260510.log`: final checker `SUMMARY {"pass": 202}`, Buildroot lane pass, and diff checks passed. |

## Remaining blockers

- Full packet-level ATS/PRI and translated-transaction handling.
- Secure stream ATS/PRI routing and Secure Event Queue parity.
- `SMMU_CR2.REC_CFG_ATS`/`RECINVSID` policy.
- Split-stage EATS IPA-return semantics and DPT checks.
- Endpoint ATC completion ordering and transaction re-drive.
- MSI/GIC interrupt delivery and ordering.
- Upstream `arm-smmu-v3` CD invalidation/PASID lifecycle.
- True upstream IREE source integration.
