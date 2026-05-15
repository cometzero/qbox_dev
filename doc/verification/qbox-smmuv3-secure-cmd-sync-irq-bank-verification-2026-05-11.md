# QBox SMMUv3 Secure CMD_SYNC IRQ bank route verification

- Date: 2026-05-11
- Scope: `/build/qbox_dev`
- Slice: SMMU-COMP-070 Secure CMD_SYNC IRQ bank route functional slice (also narrows SMMU-COMP-020 Secure CMDQ behavior)
- Result: PASS for the implemented functional slice; full ARM SMMUv3 compliance is not claimed.

## What changed

- Secure `S_CMD_SYNC` completion IRQ status now records Secure IRQ-bank state.
- Secure command-sync wired visibility is gated by `SMMU_S_IRQ_CTRL` and reflected
  in `SMMU_S_IRQ_CTRLACK`, rather than being exposed by the Non-secure
  `SMMU_IRQ_CTRL` bank.
- The existing Secure `CMD_SYNC CS=IRQ` MSI success/abort path remains unchanged;
  this slice covers the modeled wired IRQ visibility path for completed Secure
  command syncs.

## Verification evidence

| Check | Evidence | Result |
| --- | --- | --- |
| Focused QBox component build | `build/verification/smmu-secure-cmd-sync-irq-bank-build-20260511.log` | PASS: `Built target apollo-smmu-tbu-tests` |
| Focused SMMU TBU CTest | `build/verification/smmu-secure-cmd-sync-irq-bank-ctest-20260511.log` | PASS: `100% tests passed, 0 tests failed out of 1` |
| Static/syntax/checker bundle | `build/verification/smmu-secure-cmd-sync-irq-bank-static-20260511.log` | PASS: `SUMMARY {"pass": 671}` and `full_smmuv3_compliance=not_claimed` |
| Buildroot/QBox lane contract | `build/verification/smmu-secure-cmd-sync-irq-bank-lane-20260511.log` | PASS: lane conclusion printed |
| Guest Hexagon IREE smoke | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-secure-cmd-sync-irq-bank.driver.log` | PASS: `1x1x2x2xf32=[[[54 63][90 99]]]` |

## Component coverage

- `SecureCmdSyncIrqUsesSecureCtrlBank` verifies a Secure `S_CMD_SYNC` completed
  while only Non-secure `IRQ_CTRL.CMDQ_SYNC` is enabled does not assert the
  modeled IRQ line.
- The same test then enables `SMMU_S_IRQ_CTRL.CMDQ_SYNC` and verifies the modeled
  line asserts and `SMMU_S_IRQ_CTRLACK` mirrors the Secure enable bit.

## Remaining blockers

This remains a modeled functional slice. Full compliance still requires:

- Remaining Secure IRQ/MSI ordering beyond the modeled CMD_SYNC/EVENTQ/GERROR
  paths, including full wired/MSI coalescing and ordering parity.
- Full Secure command lifecycle parity for all Secure command encodings and
  security-state command parameters.
- Full Secure/Realm endpoint acceptance policy and complete Secure/Realm event
  matrix.
- RME/GPT/GPC behavior, complete Arm reference-vector parity, and upstream
  `arm-smmu-v3` lifecycle parity.
