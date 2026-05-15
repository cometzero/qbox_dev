# QBox SMMUv3 Secure register bank verification

- Date: 2026-05-11
- Scope: `/build/qbox_dev`
- Slice: SMMU-COMP-020/030 guest-visible `SMMU_S_*` Secure register banking
- Result: PASS for the implemented functional slice; full ARM SMMUv3 compliance is not claimed.

## What changed

- Expanded the Apollo TBU SMMUv3 register aperture to cover the architected
  Secure page at SMMUv3 PAGE_0 + `0x8000`.
- Added `SMMU_S_IDR1.SECURE_IMPL` and `SMMU_S_IDR1.SEL2` discovery bits for the
  modeled Secure programming interface.
- Added guest-visible Secure register dispatch for `SMMU_S_*` control, STRTAB,
  CMDQ, EVENTQ, GERROR IRQ config, EVENTQ IRQ config, and MPAM registers.
- Wired `SMMU_S_STRTAB_BASE{,_CFG}` writes into the modeled Secure stream-table
  bank and `SMMU_S_EVENTQ_BASE/PROD/CONS` writes into the modeled Secure EVENTQ
  bank without clobbering the existing Non-secure register state.
- Expanded both QBox Buildroot TBU MMIO windows from `0x2000` to `0x10000` so
  the Secure page is guest-visible in the platform configuration.

## Verification evidence

| Check | Evidence | Result |
| --- | --- | --- |
| Focused QBox component build | `build/verification/smmu-secure-register-bank-build-20260511.log` | PASS: `Built target apollo-smmu-tbu-tests` |
| Focused SMMU TBU CTest | `build/verification/smmu-secure-register-bank-ctest-20260511.log` | PASS: `100% tests passed, 0 tests failed out of 1` |
| Shell syntax | `build/verification/smmu-secure-register-bank-bashn-20260511.log` | PASS: `bash -n scripts/*.sh` returned 0 |
| Python syntax | `build/verification/smmu-secure-register-bank-pycompile-20260511.log` | PASS: `python3 -m py_compile scripts/qbox_pty_runner.py scripts/check_qbox_smmuv3_compliance.py` returned 0 |
| Static compliance checker | `build/verification/smmu-secure-register-bank-static-final-20260511.log` and `.json` | PASS: `SUMMARY {"pass": 652}` |
| Buildroot lane contract | `build/verification/smmu-secure-register-bank-lane-20260511.log` | PASS: new Secure register-bank platform/TBU/test guards passed |
| QBox guest smoke | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-secure-register-bank.driver.log` | PASS: `1x1x2x2xf32=[[[54 63][90 99]]]` |

## Component coverage

- `SecureRegisterBankConfiguresStrtabCmdqAndEventq` verifies guest-visible
  `SMMU_S_*` writes configure independent Secure STRTAB, CMDQ, and EVENTQ bank
  state, while Non-secure STRTAB/EVENTQ registers remain unchanged.
- `SecureStreamTableBankSelectsSecureSte` now configures the Secure stream table
  through `SMMU_S_STRTAB_BASE{,_CFG}` instead of direct helper-only setup, then
  proves Secure probes consume the Secure STE/CD and Non-secure probes still use
  the Non-secure STRTAB path.
- `SecureEventsUseConfiguredEventqBank` now configures the Secure event queue via
  `SMMU_S_EVENTQ_BASE` and proves Secure rejected traffic records `F_UUT` in the
  Secure EVENTQ bank without advancing the Non-secure EVENTQ producer.

## Remaining blockers

This is still a QBox functional/compliance-oriented slice. The following remain
open before any full SMMUv3 compliance claim:

- Full Secure command-queue lifecycle semantics, including Secure command
  stream security-state parameters and invalidation parity.
- Full Secure/Realm endpoint acceptance policy rather than the current modeled
  Secure/Realm/Root rejection path for endpoint traffic.
- RME/GPT/GPC behavior and the complete Secure/Realm event matrix.
- Full Arm reference-vector parity and upstream `arm-smmu-v3` lifecycle parity.
- True upstream IREE HAL source integration parity remains outside this SMMU
  register-bank slice.
