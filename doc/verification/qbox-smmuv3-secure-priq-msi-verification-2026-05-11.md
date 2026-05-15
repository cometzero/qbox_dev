# QBox SMMUv3 Secure PRIQ MSI bank route verification

- Date: 2026-05-11
- Scope: `/build/qbox_dev`
- Slice: SMMU-COMP-070 Secure PRIQ MSI bank route functional slice (also narrows SMMU-COMP-020/060 Secure PRIQ behavior)
- Result: PASS for this Secure PRIQ MSI functional slice. Full SMMUv3 compliance remains blocked by the open items below.

## What changed

- Secure PRIQ records can now use the guest-visible `SMMU_S_PRIQ_*` register bank
  instead of the Non-secure `SMMU_PRIQ_*` queue state.
- Secure PRIQ notification now records Secure IRQ-bank state and uses
  `SMMU_S_IRQ_CTRL` plus `SMMU_S_PRIQ_IRQ_CFG{0,1,2}` for the modeled IRQ/MSI
  path.
- Failed Secure PRIQ MSI writes now report `S_GERROR.MSI_PRIQ_ABORT` and are
  acknowledged through `S_GERRORN`, without setting the Non-secure GERROR bank.

## Verification evidence

| Check | Evidence | Result |
| --- | --- | --- |
| Focused QBox component build | `build/verification/smmu-secure-priq-msi-build-20260511.log` | PASS: `Built target apollo-smmu-tbu-tests` |
| Focused SMMU TBU CTest | `build/verification/smmu-secure-priq-msi-ctest-20260511.log` | PASS: `100% tests passed, 0 tests failed out of 1` |
| Static/syntax/checker bundle | `build/verification/smmu-secure-priq-msi-static-20260511.log` | PASS: `SUMMARY {"pass": 675}` and `full_smmuv3_compliance=not_claimed` |
| Buildroot/QBox lane contract | `build/verification/smmu-secure-priq-msi-lane-20260511.log` | PASS: lane concluded with Buildroot/QBox ownership statement |
| Guest Hexagon IREE smoke | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-secure-priq-msi.driver.log` | PASS: `1x1x2x2xf32=[[[54 63][90 99]]]` |

## Component coverage

- `SecurePriqMsiAndAbortUseSecureBank` verifies a Secure PRIQ record is written
  to `SMMU_S_PRIQ_*` state and not to the Non-secure PRIQ queue.
- The same test verifies Secure PRIQ MSI delivery uses `SMMU_S_PRIQ_IRQ_CFG1`, a
  bad Secure PRIQ MSI target sets `S_GERROR.MSI_PRIQ_ABORT`, Non-secure GERROR
  remains clear, and `S_GERRORN` acknowledges the Secure abort bit.

## Remaining blockers

This remains a modeled functional slice. Full compliance still requires:

- Remaining Secure IRQ/MSI ordering beyond the modeled CMD_SYNC/EVENTQ/PRIQ/GERROR
  paths, including full wired/MSI coalescing and ordering parity.
- Full Secure command lifecycle parity for all Secure command encodings and
  security-state command parameters.
- Full Secure/Realm endpoint acceptance policy and complete Secure/Realm event
  matrix.
- RME/GPT/GPC behavior, complete Arm reference-vector parity, and upstream
  `arm-smmu-v3` lifecycle parity.
