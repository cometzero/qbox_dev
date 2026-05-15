# QBox SMMUv3 Secure MPAM register-bank verification

- Date: 2026-05-11
- Scope: `/build/qbox_dev`
- Slice: SMMU-COMP-020/050 Secure GBPMPAM/GMPAM register-bank attribute slice
- Result: PASS for modeled Secure MPAM register-bank attribute selection. Full
  SMMUv3/RME/GPT/GPC compliance remains open.

## What changed

- `arch_gbpmpam_for_security_state()` selects `SMMU_S_GBPMPAM` for modeled
  Secure endpoint transactions and the Non-secure `SMMU_GBPMPAM` bank for the
  current Non-secure/Realm/Root fallback path.
- `arch_gmpam_for_security_state()` selects `SMMU_S_GMPAM` for modeled Secure
  SMMU-originated fetch/write attributes and the Non-secure `SMMU_GMPAM` bank
  for the current fallback path.
- `SecureMpamRegisterBanksDriveAttributes` verifies Secure client GBPMPAM and
  Secure SMMU-originated GMPAM attributes propagate into downstream TLM
  extensions with Secure PARTID-space tagging.

## Verification evidence

| Check | Evidence | Result |
| --- | --- | --- |
| Focused QBox component build | `build/verification/smmu-secure-mpam-bank-build-20260511.log` | PASS: `Built target apollo-smmu-tbu-tests` |
| Focused SMMU TBU CTest | `build/verification/smmu-secure-mpam-bank-ctest-20260511.log` | PASS: `100% tests passed, 0 tests failed out of 1` |
| Focused Secure MPAM register-bank gTest | `build/verification/smmu-secure-mpam-bank-gtest-20260511.log` | PASS: `[  PASSED  ] 2 tests.` |
| Static/syntax/checker bundle | `build/verification/smmu-secure-mpam-bank-static-20260511.log` | PASS: `SUMMARY {"pass": 742}` |
| Buildroot/QBox lane contract | `build/verification/smmu-secure-mpam-bank-lane-20260511.log` | PASS: lane conclusion emitted after contract checks |
| Final closure replay | `build/verification/smmu-secure-mpam-bank-final-closure-check-20260511.log` | PASS: `git diff --check`, checklist JSON validation, and final checker replay passed |

## Remaining blockers

This closes the modeled Secure GBPMPAM/GMPAM attribute-bank gap for the current
QBox endpoint path. Realm/Root MPAMIDR/GPT/GPC banking, full SMMU-originated
transaction ordering, packet-level ATS/PRI parity, and upstream `arm-smmu-v3`
lifecycle parity remain open.
