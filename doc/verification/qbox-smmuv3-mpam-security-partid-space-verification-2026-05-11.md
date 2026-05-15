# QBox SMMUv3 MPAM security PARTID-space verification

- Date: 2026-05-11
- Scope: `/build/qbox_dev`
- Slice: SMMU-COMP-020/050 MPAM security PARTID-space slice
- Result: PASS for modeled MPAM PARTID-space derivation from endpoint security
  state. Full SMMUv3/RME/GPT/GPC compliance remains open.

## What changed

- `arch_mpam_partid_space_for_security_state()` maps endpoint security states to
  the modeled MPAM PARTID spaces:
  - Non-secure -> `ARCH_MPAM_SPACE_NONSECURE`
  - Secure -> `ARCH_MPAM_SPACE_SECURE`
  - Realm -> `ARCH_MPAM_SPACE_REALM`
  - Root -> `ARCH_MPAM_SPACE_ROOT`
- GBPMPAM, STE-derived MPAM, CD/VMS-remapped MPAM, and GMPAM-originated
  attributes now use the current modeled security state instead of forcing the
  Non-secure PARTID space.
- `MpamAttributesCarrySecurityPartidSpace` verifies downstream TLM extension
  propagation and `REG_ARCH_MPAM_STATUS` reporting for all four modeled endpoint
  security states.

## Verification evidence

| Check | Evidence | Result |
| --- | --- | --- |
| Focused QBox component build | `build/verification/smmu-mpam-security-space-build-20260511.log` | PASS: `Built target apollo-smmu-tbu-tests` |
| Focused SMMU TBU CTest | `build/verification/smmu-mpam-security-space-ctest-20260511.log` | PASS: `100% tests passed, 0 tests failed out of 1` |
| Focused MPAM security PARTID-space gTest | `build/verification/smmu-mpam-security-space-gtest-20260511.log` | PASS: `[  PASSED  ] 2 tests.` |
| Static/syntax/checker bundle | `build/verification/smmu-mpam-security-space-static-20260511.log` | PASS: `SUMMARY {"pass": 733}` |
| Buildroot/QBox lane contract | `build/verification/smmu-mpam-security-space-lane-20260511.log` | PASS: lane conclusion emitted after contract checks |
| Final closure replay | `build/verification/smmu-mpam-security-space-final-closure-check-20260511.log` | PASS: `git diff --check`, checklist JSON validation, and final checker replay passed |

## Remaining blockers

This closes the prior Non-secure-only MPAM PARTID-space modeling gap for the
modeled endpoint path. It is still not complete MPAM/RME/GPT/GPC compliance:
complete Realm/Root GPT/GPC policy, Secure/Realm MPAMIDR banking, packet-level
ATS/PRI parity, and upstream `arm-smmu-v3` lifecycle parity remain open.
