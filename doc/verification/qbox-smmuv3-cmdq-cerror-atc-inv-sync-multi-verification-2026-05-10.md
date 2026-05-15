# QBox SMMUv3 CMDQ CERROR_ATC_INV_SYNC Multi-Outstanding Verification - 2026-05-10

## Scope

SMMU-COMP-020 CMDQ CERROR_ATC_INV_SYNC multi-outstanding pause/recovery slice.

This component-level slice extends the modeled ATC invalidation completion
failure path. Multiple outstanding failed `CMD_ATC_INV` completions are tracked
until the next `CMD_SYNC`; that sync reports one architected
`CMDQ_CONS.CERROR_ATC_INV_SYNC`, leaves `CMDQ_CONS.RD` on the failing sync,
raises `GERROR.CMDQ_ABORT`, and pauses later command processing until software
acknowledges GERROR and rewrites `CMDQ_CONS` to skip the failing sync. A later
`CMD_SYNC` is then processed normally.

This is still not a full endpoint ATS/PCIe protocol model. Real ATS Invalidate
Request packets, timeout/UR response semantics, endpoint completion ordering,
MSI delivery, and upstream `arm-smmu-v3` queue lifecycle parity remain open.

## Ground truth

- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
  describes `CERROR_ATC_INV_SYNC` as a `CMD_SYNC` error when completion of
  prior `CMD_ATC_INV` commands cannot be guaranteed.
- The same command-queue error model requires command queue progress to stop on
  command error until software handles the error and advances/rewrites the
  consumer pointer.
- `sources/smmu/TASKS_CPP_OPERATION.md` tracks failed `CMD_ATC_INV` completion
  causing `CMD_SYNC` `CERROR_ATC_INV_SYNC` as an operation requirement.

## Implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  adds `m_arch_atc_inv_sync_pending_count` and
  `m_arch_atc_inv_sync_force_fail_count` so component tests can model multiple
  outstanding failed ATC invalidation completions before one `CMD_SYNC`.
- `handle_cmdq_atc_inv()` increments the pending failure count for each forced
  failed completion while still applying the modeled ATC cache invalidation
  side effect.
- `process_cmdq()` coalesces pending failed ATC completions into one
  `CERROR_ATC_INV_SYNC` on `CMD_SYNC`, clears the pending count, leaves RD on
  the failing sync, and relies on the existing CERROR gate to pause later
  commands until software recovery.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc` adds
  `CmdSyncCoalescesOutstandingAtcInvFailuresAndPauses`.
- `scripts/check_qbox_smmuv3_compliance.py`,
  `scripts/check_buildroot_arm64_lane.sh`, and
  `doc/spec/qbox-smmuv3-compliance-checklist.md` gate the slice.

## Evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Component build | PASS | `build/verification/apollo-smmu-tbu-cmdq-cerror-atc-inv-sync-multi-build-20260510.log`: `Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`. |
| Component CTest | PASS | `build/verification/apollo-smmu-tbu-cmdq-cerror-atc-inv-sync-multi-ctest-20260510.log`: `100% tests passed, 0 tests failed out of 1`. |
| Static/checker/lane | PASS | `build/verification/smmu-cmdq-cerror-atc-inv-sync-multi-static-final-20260510.log`: `PASS  tbu:cmdq-cerror-atc-inv-sync-multi`, `SUMMARY {"pass": 231}`, and `Lane conclusion: Buildroot owns rootfs/DTB generation only; Linux Image comes from sources/linux, and libqemu comes from sources/qemu.` |

## Remaining blockers

- Real endpoint ATS Invalidate Request packet generation and timeout handling.
- UR response semantics and endpoint ATC completion ordering.
- Broader ATC invalidation timeout, retry, and abort ordering beyond the
  modeled forced-failure hook.
- CMDQ error recovery parity for all command error classes, MSI delivery, and
  upstream `arm-smmu-v3` queue lifecycle parity.
