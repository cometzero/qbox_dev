# QBox SMMUv3 Secure CMDQ SSec TLBI/ATC verification

- Date: 2026-05-11
- Scope: `/build/qbox_dev`
- Slice: SMMU-COMP-020 Secure CMDQ SSec TLBI/ATC functional slice
- Result: PASS for this Secure CMDQ SSec TLBI/ATC functional slice. Full SMMUv3 compliance remains blocked by the open items below.

## What changed

- The Apollo TBU now tags modeled ATS/TLB cache entries with a security state.
- Secure CMDQ `TLBI_NH_*` and `ATC_INV` commands now route invalidation through
  the modeled `SSec` selector, so `SSec=1` targets Secure entries and `SSec=0`
  targets Non-secure entries.
- Non-secure CMDQ `TLBI_NH_*` and `ATC_INV` commands with `SSec=1` now raise
  `CMDQ_CONS.CERROR_ILL` before consuming the command and preserve Secure
  ATS/TLB state.

## Verification evidence

| Check | Evidence | Result |
| --- | --- | --- |
| Focused QBox component build | `build/verification/smmu-secure-cmdq-ssec-tlbi-atc-build-20260511.log` | PASS: `Built target apollo-smmu-tbu-tests` |
| Focused SMMU TBU CTest | `build/verification/smmu-secure-cmdq-ssec-tlbi-atc-ctest-20260511.log` | PASS: `100% tests passed, 0 tests failed out of 1` |
| Static/syntax/checker bundle | `build/verification/smmu-secure-cmdq-ssec-tlbi-atc-static-20260511.log` | PASS: `SUMMARY {"pass": 681}` before docs; final doc replay `SUMMARY {"pass": 686}` and `full_smmuv3_compliance=not_claimed` |
| Buildroot/QBox lane contract | `build/verification/smmu-secure-cmdq-ssec-tlbi-atc-lane-20260511.log` | PASS: lane contract checks completed |
| Guest Hexagon IREE smoke | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-secure-cmdq-ssec-tlbi-atc.driver.log` | PASS: `1x1x2x2xf32=[[[54 63][90 99]]]` matched |

## Component coverage

- `SecureCmdqSsecTlbiAtcTargetsSelectedSecurityState` verifies S_CMDQ
  `TLBI_NH_VA` with `SSec=1` invalidates only Secure ATS/TLB state and a later
  `ATC_INV` with `SSec=0` invalidates Non-secure ATS/TLB state.
- `NonSecureCmdqSsecTlbiAtcAreIllegal` verifies Non-secure CMDQ TLBI/ATC with
  `SSec=1` raises `CERROR_ILL`, leaves `CMDQ_CONS.RD` on the failing command,
  and preserves Secure ATS/TLB state.

## Remaining blockers

This remains a modeled command-parameter slice. Full command/security-state
compliance still requires:

- All remaining Secure command encodings and SSec/security-state parameters
  beyond the modeled CFGI/TLBI/ATC path.
- Secure CMDQ command effects on all relevant Secure/Non-secure caches and TLBs,
  including exact Arm range/leaf behavior and reference-vector parity.
- Secure/Realm endpoint acceptance policy, RME/GPT/GPC behavior, complete event
  matrix parity, and upstream `arm-smmu-v3` lifecycle parity.
