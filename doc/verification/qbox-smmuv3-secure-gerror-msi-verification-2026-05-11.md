# QBox SMMUv3 Secure GERROR MSI bank route verification

- Date: 2026-05-11
- Scope: `/build/qbox_dev`
- Slice: SMMU-COMP-070 Secure GERROR MSI bank route functional slice (also narrows SMMU-COMP-020 Secure IRQ/MSI behavior)
- Result: PASS for the implemented functional slice; full ARM SMMUv3 compliance is not claimed.

## What changed

- Secure GERROR sources now keep their IRQ/MSI notification in Secure IRQ state.
- `SMMU_S_GERROR_IRQ_CFG{0,1,2}` is used for Secure GERROR MSI writes instead
  of the Non-secure GERROR MSI configuration.
- Failed Secure GERROR MSI writes now report `S_GERROR.MSI_GERROR_ABORT` and are
  acknowledged through `S_GERRORN`, without setting the Non-secure GERROR bank.
- The slice preserves the existing shared modeled IRQ status while routing
  GERROR active bits and MSI abort reporting to the correct Secure bank.

## Verification evidence

| Check | Evidence | Result |
| --- | --- | --- |
| Focused QBox component build | `build/verification/smmu-secure-gerror-msi-build-20260511.log` | PASS: `Built target apollo-smmu-tbu-tests` |
| Focused SMMU TBU CTest | `build/verification/smmu-secure-gerror-msi-ctest-20260511.log` | PASS: `100% tests passed, 0 tests failed out of 1` |
| Static/syntax/checker bundle | `build/verification/smmu-secure-gerror-msi-static-20260511.log` | PASS: `SUMMARY {"pass": 668}` and `full_smmuv3_compliance=not_claimed` |
| Buildroot/QBox lane contract | `build/verification/smmu-secure-gerror-msi-lane-20260511.log` | PASS: lane conclusion printed |
| Guest Hexagon IREE smoke | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-secure-gerror-msi.driver.log` | PASS: `1x1x2x2xf32=[[[54 63][90 99]]]` |

## Component coverage

- `SecureGerrorMsiAndAbortUseSecureBank` verifies that a Secure GERROR source
  sends the MSI payload programmed in `SMMU_S_GERROR_IRQ_CFG1` and does not write
  the Non-secure GERROR MSI target.
- The same test verifies failed Secure GERROR MSI writes increment MSI abort
  accounting, set `S_GERROR.MSI_GERROR_ABORT` with the original Secure GERROR
  source bit, keep Non-secure GERROR clear, and clear the Secure GERROR status
  through `S_GERRORN` acknowledgement.

## Remaining blockers

This remains a modeled functional slice. Full compliance still requires:

- Remaining Secure IRQ/MSI ordering beyond the modeled CMD_SYNC/EVENTQ/GERROR
  MSI paths, including full wired/MSI coalescing and ordering parity.
- Full Secure command lifecycle parity for all Secure command encodings and
  security-state command parameters.
- Full Secure/Realm endpoint acceptance policy and complete Secure/Realm event
  matrix.
- RME/GPT/GPC behavior, complete Arm reference-vector parity, and upstream
  `arm-smmu-v3` lifecycle parity.
