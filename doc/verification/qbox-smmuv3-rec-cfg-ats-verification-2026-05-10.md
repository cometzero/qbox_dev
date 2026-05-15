# QBox SMMUv3 REC_CFG_ATS Verification - 2026-05-10

## Scope

SMMU-COMP-060 functional slice for CR2.REC_CFG_ATS and CR2.RECINVSID
event-recording gates on ATS Translation Requests.

This slice uses the pinned `sources/smmu` reference as ground truth for
CR2 bit placement and ATS event-recording policy. The Apollo TBU now
advertises `FEATURE_ARCH_REC_CFG_ATS_GATES`, reports IDR0.ATSRECERR, and
models two ATS Translation Request recording gates:

- SMMUEN-disabled ATS Translation Request returns UR/BAD_ATS_TREQ; the
  fault/event record is suppressed until CR2.REC_CFG_ATS is set.
- Bad StreamID on an ATS Translation Request records C_BAD_STREAMID only
  when CR2.REC_CFG_ATS and CR2.RECINVSID are both set.

This remains a functional slice. It does not yet claim full byte-exact
ATS/PRI packet protocol, secure-stream routing, complete translated
transaction re-drive, endpoint ATC ordering, or upstream arm-smmu-v3 PASID
lifecycle parity.

## Implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  adds `FEATURE_ARCH_REC_CFG_ATS_GATES`, `ARCH_CR2_REC_CFG_ATS`,
  `ARCH_CR2_RECINVSID`, IDR0.ATSRECERR, and ATS Translation Request
  recording suppression helpers.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  adds `AtsTranslationRequestHonorsCr2RecCfgAtsAndRecInvsid`.
- `sources/linux/drivers/soc/apollo/apollo-hexagon-test.c` validates
  REC_CFG_ATS-disabled suppression and REC_CFG_ATS-enabled recording at
  boot.
- `scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh` gates runtime on
  `features=0x1fffff` and
  `SMMUv3 REC_CFG_ATS translation request selftest ok`.
- `scripts/check_qbox_smmuv3_compliance.py`,
  `scripts/check_buildroot_arm64_lane.sh`, and
  `doc/spec/qbox-smmuv3-compliance-checklist.md` record the gate.

## Evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Checker preflight | PASS | `build/verification/qbox-smmuv3-compliance-rec-cfg-ats-preflight-20260510.log`: `SUMMARY {"pass": 207}`, `tbu:rec-cfg-ats-gates`, `linux:rec-cfg-ats-probe`. |
| Component build | PASS | `build/verification/apollo-smmu-tbu-rec-cfg-ats-build-20260510.log`: `Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`. |
| Component CTest | PASS | `build/verification/apollo-smmu-tbu-rec-cfg-ats-ctest-20260510.log`: `100% tests passed, 0 tests failed out of 1`. |
| Linux build | PASS | `build/verification/qbox-linux-smmu-rec-cfg-ats-20260510.log`: `CC drivers/soc/apollo/apollo-hexagon-test.o`, `Linux Image: /build/qbox_dev/build/linux-a710/arch/arm64/boot/Image`. |
| Artifact staging | PASS | `build/verification/stage-artifacts-smmu-rec-cfg-ats-20260510.log`: staged Linux + Buildroot artifacts into QBox platform artifact directory. |
| QBox platform runtime build | PASS | `build/verification/qbox-platform-smmu-rec-cfg-ats-20260510.log`: `QBox Buildroot platform runtime built in /build/qbox_dev/sources/qbox/build`. |
| Guest smoke | PASS | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-rec-cfg-ats.driver.log`: `PASS: QBox guest IREE Hexagon tiny-CNN output matched`, `Expected: 1x1x2x2xf32=[[[54 63][90 99]]]`. |
| Runtime REC_CFG_ATS marker | PASS | Runtime log records `features=0x1fffff` and `SMMUv3 REC_CFG_ATS translation request selftest ok`. |
| Static/checker/lane | PASS | `build/verification/smmu-rec-cfg-ats-static-final-20260510.log`: final checker `SUMMARY {"pass": 207}`, Buildroot lane pass, and diff checks passed. |

## Remaining blockers

- Full packet-level ATS/PRI and translated-transaction handling.
- Secure stream ATS/PRI routing and Secure Event Queue parity.
- Split-stage EATS IPA-return semantics and DPT checks.
- Endpoint ATC completion ordering and transaction re-drive.
- MSI/GIC interrupt delivery and ordering.
- Upstream `arm-smmu-v3` CD invalidation/PASID lifecycle.
- True upstream IREE source integration.
