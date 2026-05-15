# QBox SMMUv3 CMDQ CERROR Verification - 2026-05-10

## Scope

SMMU-COMP-020 CMDQ CERROR functional slice.

This slice narrows the command queue error reporting gap for IDR3.DPT=0 DPTI commands. `CMD_DPTI_ALL` and `CMD_DPTI_PA` now leave `CMDQ_CONS.RD` pointing at the failing command, expose `CMDQ_CONS.ERR = CERROR_ILL`, assert the existing guest-visible GERROR command-queue error line, and allow software to acknowledge GERROR plus rewrite `CMDQ_CONS` to skip and clear the error.

This is still not full SMMUv3 CMDQ compliance: every illegal-command case, all CERROR classes, queue memory abort ordering, GERRORN/CMDQ_CONS software recovery subtleties, MSI delivery, and true upstream arm-smmu-v3 queue lifecycle parity remain open.

## Ground truth

- `sources/linux/drivers/iommu/arm/arm-smmu-v3/arm-smmu-v3.h` defines `CMDQ_CONS_ERR GENMASK(30, 24)` and CERROR values `NONE=0`, `ILL=1`, `ABT=2`, `ATC_INV=3`.
- `sources/smmu/cpp/include/smmu/types.h` mirrors `CMDQ_CONS_ERR_SHIFT = 24` and `CERROR_ILL = 1`.
- `sources/smmu/cpp/src/smmu/smmu.cpp` preserves CMDQ_CONS.ERR and does not advance RD after a command error.
- `sources/smmu/cpp/tests/unit/test_new_gaps_cpp.cpp` requires IDR3.DPT=0 DPTI commands to raise CERROR_ILL plus GERROR.

## Implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h` adds `FEATURE_ARCH_CMDQ_CERROR`, CMDQ_CONS RD/ERR constants, CERROR constants, `read_cmdq_cons()`, `write_cmdq_cons()`, and `set_cmdq_cerror()`.
- `process_cmdq()` now halts on active CERROR, reports ABT for unconfigured/fetch/stall failures, reports ILL for DPTI/default unsupported commands, and does not advance RD on command errors.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc` extends `DptiCommandsSetGerrorWhenDptUnsupported` to verify CERROR_ILL for DPTI_ALL and DPTI_PA plus software skip/clear via CMDQ_CONS rewrite.
- `sources/linux/drivers/soc/apollo/apollo-hexagon-test.c` decodes CMDQ_CONS.RD and CMDQ_CONS.ERR, requires `APOLLO_TBU_FEATURE_ARCH_CMDQ_CERROR`, verifies DPTI reports RD=4 plus `cerror=1`, then clears/skips with `CMDQ_CONS=5`.
- `scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh` now requires `features=0x7fffff` and `cerror=1`.
- `scripts/check_qbox_smmuv3_compliance.py`, `scripts/check_buildroot_arm64_lane.sh`, and `doc/spec/qbox-smmuv3-compliance-checklist.md` gate the slice.

## Evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Component build | PASS | `build/verification/apollo-smmu-tbu-cmdq-cerror-build-20260510.log`: `Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`. |
| Component CTest | PASS | `build/verification/apollo-smmu-tbu-cmdq-cerror-ctest-20260510.log`: `100% tests passed, 0 tests failed out of 1`. |
| Linux build | PASS | `build/verification/qbox-linux-smmu-cmdq-cerror-20260510.log`: `CC drivers/soc/apollo/apollo-hexagon-test.o`, `Linux Image: /build/qbox_dev/build/linux-a710/arch/arm64/boot/Image`. |
| Artifact staging | PASS | `build/verification/stage-artifacts-smmu-cmdq-cerror-20260510.log`: staged Linux + Buildroot artifacts into the QBox platform artifact directory. |
| QBox platform runtime build | PASS | `build/verification/qbox-platform-smmu-cmdq-cerror-20260510.log`: `QBox Buildroot platform runtime built in /build/qbox_dev/sources/qbox/build`. |
| Guest smoke | PASS | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-cmdq-cerror.driver.log`: `PASS: QBox guest IREE Hexagon tiny-CNN output matched`, `Expected: 1x1x2x2xf32=[[[54 63][90 99]]]`. |
| Runtime CERROR marker | PASS | Runtime log records `features=0x7fffff` and `SMMUv3 DPTI unsupported command selftest ok ... cerror=1`. |
| Static/checker/lane | PASS | `build/verification/smmu-cmdq-cerror-static-final-20260510.log`: `SUMMARY {"pass": 218}`, `Lane conclusion: Buildroot owns rootfs/DTB generation only; Linux Image comes from sources/linux, and libqemu comes from sources/qemu.` |

## Remaining blockers

- Full illegal-command matrix, including all feature-dependent CERROR_ILL cases.
- Full CERROR_ABT and CERROR_ATC_INV_SYNC ordering semantics.
- CMDQ pause/retry, GERRORN/CMDQ_CONS recovery corner cases, and queue memory abort ordering.
- DPT walk tables, DPT_CFG_FAR/DPT_ERR ordering, DPT VMID/TLB/completion semantics, and Secure/Realm DPT separation.
- Full packet-level ATS/PRI, translated transaction re-drive, MSI/GIC ordering, upstream arm-smmu-v3 lifecycle parity, PCIe PASID requester semantics, and true upstream IREE integration.
