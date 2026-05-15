# QBox SMMUv3 DPTI Unsupported Command Verification - 2026-05-10

## Scope

SMMU-COMP-020 DPTI unsupported-command functional slice.

The Apollo TBU reports `ARCH_IDR3 = 0`, so dirty page tracking is not
advertised. The pinned `sources/smmu` reference treats `CMD_DPTI_ALL` and
`CMD_DPTI_PA` as illegal when IDR3.DPT is not implemented. This slice models
that condition by routing both commands to a guest-visible GERROR command-abort
path instead of silently accepting them as no-ops.

This is still not full DPT compliance: DPT walk tables, DPT_CFG_FAR, DPT_ERR
ordering, DPT TLB, VMID matching, DPTI completion semantics, and full byte-exact
CMDQ_CONS.CERROR reporting remain open.

## Implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  adds `FEATURE_ARCH_DPTI_UNSUPPORTED`, `ARCH_CMD_DPTI_ALL`,
  `ARCH_CMD_DPTI_PA`, and `handle_cmdq_dpti_unsupported()`.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  adds `DptiCommandsSetGerrorWhenDptUnsupported`.
- `sources/linux/drivers/soc/apollo/apollo-hexagon-test.c` checks `IDR3==0`,
  drives `CMD_DPTI_ALL`, validates GERROR, and prints
  `SMMUv3 DPTI unsupported command selftest ok`.
- `scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh` requires
  `features=0x3fffff` and the DPTI selftest marker.
- `scripts/check_qbox_smmuv3_compliance.py`,
  `scripts/check_buildroot_arm64_lane.sh`, and
  `doc/spec/qbox-smmuv3-compliance-checklist.md` gate the slice.

## Evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Component build | PASS | `build/verification/apollo-smmu-tbu-dpti-unsupported-build-20260510.log`: `Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`. |
| Component CTest | PASS | `build/verification/apollo-smmu-tbu-dpti-unsupported-ctest-20260510.log`: `100% tests passed, 0 tests failed out of 1`. |
| Linux build | PASS | `build/verification/qbox-linux-smmu-dpti-unsupported-20260510.log`: `CC drivers/soc/apollo/apollo-hexagon-test.o`, `Linux Image: /build/qbox_dev/build/linux-a710/arch/arm64/boot/Image`. |
| Artifact staging | PASS | `build/verification/stage-artifacts-smmu-dpti-unsupported-20260510.log`: staged Linux + Buildroot artifacts into QBox platform artifact directory. |
| QBox platform runtime build | PASS | `build/verification/qbox-platform-smmu-dpti-unsupported-20260510.log`: `QBox Buildroot platform runtime built in /build/qbox_dev/sources/qbox/build`. |
| Guest smoke | PASS | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-dpti-unsupported.driver.log`: `PASS: QBox guest IREE Hexagon tiny-CNN output matched`, `Expected: 1x1x2x2xf32=[[[54 63][90 99]]]`. |
| Runtime DPTI marker | PASS | Runtime log records `features=0x3fffff` and `SMMUv3 DPTI unsupported command selftest ok`. |
| Static/checker/lane | PASS | `build/verification/smmu-dpti-unsupported-static-final-20260510.log`: final checker summary, Buildroot lane pass, and diff checks passed. |

## Remaining blockers

- Full dirty-page tracking table walk and register state.
- DPT_CFG_FAR and DPT_ERR ordering.
- Byte-exact CMDQ_CONS.CERROR encoding for DPTI.
- DPT VMID matching, DPT TLB, and DPTI completion semantics.
- Secure/Realm DPT separation.
- Full packet-level ATS/PRI, translated-transaction re-drive, MSI/GIC ordering,
  upstream arm-smmu-v3 lifecycle, PCIe PASID requester semantics, and true
  upstream IREE integration.
