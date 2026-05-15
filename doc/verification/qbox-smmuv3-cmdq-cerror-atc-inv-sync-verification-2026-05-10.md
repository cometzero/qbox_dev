# QBox SMMUv3 CMDQ CERROR_ATC_INV_SYNC Verification - 2026-05-10

## Scope

SMMU-COMP-020 CMDQ CERROR_ATC_INV_SYNC functional slice.

This component-level slice models the architected command error where a
`CMD_SYNC` waits for a prior `CMD_ATC_INV` whose endpoint invalidation
completion cannot be guaranteed. A test hook marks the next modeled ATC
invalidation as failed; the following `CMD_SYNC` leaves `CMDQ_CONS.RD` at the
failing sync command, exposes `CMDQ_CONS.ERR = CERROR_ATC_INV_SYNC`, raises the
existing command-queue GERROR line, suppresses the CMDQ_SYNC IRQ, and allows
software to acknowledge GERROR plus rewrite `CMDQ_CONS` to clear/skip the
failed sync.

This is not full endpoint ATC/PCIe protocol compliance: real ATS Invalidate
Request packets, timeout handling, UR response semantics, endpoint ATC
completion ordering, and upstream arm-smmu-v3 queue lifecycle parity remain
open.

## Ground truth

- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
  states that if completion of a prior `CMD_ATC_INV` cannot be guaranteed by
  `CMD_SYNC`, the sync can raise `CERROR_ATC_INV_SYNC`.
- The same section states that the error is associated with outstanding
  `CMD_ATC_INV` commands submitted before the `CMD_SYNC`.
- `sources/smmu/TASKS_CPP_OPERATION.md` tracks `CMD_SYNC waiting for failed
  CMD_ATC_INV completion causes CERROR_ATC_INV_SYNC command error` as an
  operation requirement.
- `sources/linux/drivers/iommu/arm/arm-smmu-v3/arm-smmu-v3.h` defines
  `CMDQ_ERR_CERROR_ATC_INV_IDX = 3`.

## Implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  adds `ARCH_CMDQ_CERROR_ATC_INV_SYNC`, an ATC invalidation sync-failure state,
  and a test hook that marks a modeled `CMD_ATC_INV` as having failed
  completion.
- `process_cmdq()` now reports `CERROR_ATC_INV_SYNC` when a `CMD_SYNC` observes
  the pending modeled ATC invalidation completion failure. It leaves RD on the
  failing sync, raises `GERROR.CMDQ_ABORT`, and does not raise
  `ARCH_IRQ_CMDQ_SYNC`.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc` adds
  `CmdSyncAfterFailedAtcInvSetsCerrorAtcInvSync`.
- `scripts/check_qbox_smmuv3_compliance.py`,
  `scripts/check_buildroot_arm64_lane.sh`, and
  `doc/spec/qbox-smmuv3-compliance-checklist.md` gate the slice.

## Evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Component build | PASS | `build/verification/apollo-smmu-tbu-cmdq-cerror-atc-inv-sync-build-20260510.log`: `Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`. |
| Component CTest | PASS | `build/verification/apollo-smmu-tbu-cmdq-cerror-atc-inv-sync-ctest-20260510.log`: `100% tests passed, 0 tests failed out of 1`. |
| Static/checker/lane | PASS | `build/verification/smmu-cmdq-cerror-atc-inv-sync-static-final-20260510.log`: `PASS  tbu:cmdq-cerror-atc-inv-sync`, `SUMMARY {"pass": 226}`, and `Lane conclusion: Buildroot owns rootfs/DTB generation only; Linux Image comes from sources/linux, and libqemu comes from sources/qemu.` |

## Remaining blockers

- Real endpoint ATS Invalidate Request packet generation and timeout handling.
- UR response semantics and endpoint ATC completion ordering.
- Broader CERROR_ATC_INV_SYNC timeout/retry ordering beyond the component-level
  forced-failure hooks.
- CMDQ pause/retry, GERRORN/CMDQ_CONS recovery corner cases, MSI delivery, and
  upstream `arm-smmu-v3` queue lifecycle parity.
