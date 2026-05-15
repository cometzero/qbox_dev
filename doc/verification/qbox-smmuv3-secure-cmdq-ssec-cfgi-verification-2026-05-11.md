# QBox SMMUv3 Secure CMDQ SSec CFGI verification

- Date: 2026-05-11
- Scope: `/build/qbox_dev`
- Slice: SMMU-COMP-020 Secure CMDQ SSec CFGI functional slice
- Result: PASS for this Secure CMDQ SSec CFGI functional slice. Full SMMUv3 compliance remains blocked by the open items below.

## What changed

- The Apollo TBU decodes the modeled architected command `SSec` bit for
  command-queue entries.
- Secure CMDQ CFGI commands can now target Secure versus Non-secure
  configuration-cache state using `SSec=1` or `SSec=0`.
- Non-secure CMDQ CFGI commands with `SSec=1` now raise `CMDQ_CONS.CERROR_ILL`
  and do not invalidate Secure configuration-cache state.

## Verification evidence

| Check | Evidence | Result |
| --- | --- | --- |
| Focused QBox component build | `build/verification/smmu-secure-cmdq-ssec-cfgi-build-20260511.log` | PASS: `Built target apollo-smmu-tbu-tests` |
| Focused SMMU TBU CTest | `build/verification/smmu-secure-cmdq-ssec-cfgi-ctest-20260511.log` | PASS: `100% tests passed, 0 tests failed out of 1` |
| Static/syntax/checker bundle | `build/verification/smmu-secure-cmdq-ssec-cfgi-static-20260511.log` | PASS: `SUMMARY {"pass": 680}` and `full_smmuv3_compliance=not_claimed` |
| Buildroot/QBox lane contract | `build/verification/smmu-secure-cmdq-ssec-cfgi-lane-20260511.log` | PASS: lane contract checks completed |
| Guest Hexagon IREE smoke | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-secure-cmdq-ssec-cfgi.driver.log` | PASS: `1x1x2x2xf32=[[[54 63][90 99]]]` matched |

## Component coverage

- `SecureCmdqSsecCfgiTargetsSelectedSecurityState` verifies `S_CMDQ` CFGI_STE
  with `SSec=1` invalidates Secure configuration-cache state while leaving the
  Non-secure entry intact, then `SSec=0` targets the Non-secure entry.
- `NonSecureCmdqSsecCfgiIsIllegal` verifies a Non-secure CMDQ CFGI_STE with
  `SSec=1` raises `CERROR_ILL`, activates `GERROR.CMDQ_ABORT`, and preserves the
  Secure configuration-cache entry.

## Remaining blockers

This remains a modeled command-parameter slice. Full command/security-state
compliance still requires:

- All remaining Secure command encodings and SSec/security-state parameters
  beyond the modeled CFGI path.
- Secure CMDQ command effects on all relevant Secure/Non-secure caches and TLBs,
  including exact Arm range/leaf behavior and reference-vector parity.
- Secure/Realm endpoint acceptance policy, RME/GPT/GPC behavior, complete event
  matrix parity, and upstream `arm-smmu-v3` lifecycle parity.
