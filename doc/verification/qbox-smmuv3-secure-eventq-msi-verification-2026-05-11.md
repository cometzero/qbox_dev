# QBox SMMUv3 Secure EVENTQ MSI bank route verification

- Date: 2026-05-11
- Scope: `/build/qbox_dev`
- Slice: SMMU-COMP-070 Secure EVENTQ MSI bank route functional slice (also narrows SMMU-COMP-020/050 Secure EVENTQ behavior)
- Result: PASS for the implemented functional slice; full ARM SMMUv3 compliance is not claimed.

## What changed

- Secure EVENTQ records routed through a configured `SMMU_S_EVENTQ_*` bank now
  carry their IRQ/MSI notification through Secure IRQ state.
- `SMMU_S_EVENTQ_IRQ_CFG{0,1,2}` is used for Secure EVENTQ MSI writes instead
  of the Non-secure EVENTQ MSI configuration.
- Failed Secure EVENTQ MSI writes now report
  `S_GERROR.MSI_EVENTQ_ABORT` and are acknowledged through `S_GERRORN`, without
  setting the Non-secure GERROR bank.
- Secure EVENTQ/GERROR IRQ_CFG writes now follow the same IRQ_CTRL guard model as
  the Non-secure bank for this modeled slice.

## Verification evidence

| Check | Evidence | Result |
| --- | --- | --- |
| Focused QBox component build | `build/verification/smmu-secure-eventq-msi-build-20260511.log` | PASS: `Built target apollo-smmu-tbu-tests` |
| Focused SMMU TBU CTest | `build/verification/smmu-secure-eventq-msi-ctest-20260511.log` | PASS: `100% tests passed, 0 tests failed out of 1` |
| Static/syntax/checker bundle | `build/verification/smmu-secure-eventq-msi-static-20260511.log` | PASS: `SUMMARY {"pass": 664}` and `full_smmuv3_compliance=not_claimed` |
| Buildroot/QBox lane contract | `build/verification/smmu-secure-eventq-msi-lane-20260511.log` | PASS: lane conclusion printed |
| Guest Hexagon IREE smoke | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-secure-eventq-msi.driver.log` | PASS: `1x1x2x2xf32=[[[54 63][90 99]]]` |

## Component coverage

- `SecureEventqMsiAndAbortUseSecureBank` verifies that a Secure rejected
  transaction records into the configured Secure EVENTQ bank and sends the MSI
  payload programmed in `SMMU_S_EVENTQ_IRQ_CFG1`.
- The same test verifies the Non-secure EVENTQ MSI target is not written for the
  Secure event, a failed Secure EVENTQ MSI increments MSI abort accounting,
  `S_GERROR.MSI_EVENTQ_ABORT` becomes active, Non-secure GERROR remains clear,
  and `S_GERRORN` acknowledgement clears the Secure GERROR status.

## Remaining blockers

This remains a modeled functional slice. Full compliance still requires:

- Remaining Secure IRQ/MSI ordering beyond the modeled CMD_SYNC and EVENTQ MSI
  paths, including full wired/MSI coalescing and ordering parity.
- Full Secure command lifecycle parity for all Secure command encodings and
  security-state command parameters.
- Full Secure/Realm endpoint acceptance policy and complete Secure/Realm event
  matrix.
- RME/GPT/GPC behavior, complete Arm reference-vector parity, and upstream
  `arm-smmu-v3` lifecycle parity.
