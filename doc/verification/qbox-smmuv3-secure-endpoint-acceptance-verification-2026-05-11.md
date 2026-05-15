# QBox SMMUv3 Secure/Realm/Root endpoint acceptance verification

- Date: 2026-05-11
- Scope: `/build/qbox_dev`
- Slice: SMMU-COMP-030/050 Secure/Realm/Root endpoint acceptance slice
- Ground truth: the local SMMUv3 reference tracks Non-secure, Secure, Realm,
  and Root security states separately, with Secure state using its own register
  and queue banks. Realm and Root now use the modeled endpoint translation path;
  complete RME/GPT/GPC behavior remains out of scope for this slice.
- Result: PASS for this modeled Secure/Realm/Root endpoint acceptance slice. Full SMMUv3
  compliance remains blocked by the open items below.

## What changed

- `arch_security_state_supported()` now accepts `ARCH_SECURITY_SECURE`,
  `ARCH_SECURITY_REALM`, and `ARCH_SECURITY_ROOT` in addition to
  `ARCH_SECURITY_NONSECURE`.
- Secure, Realm, and Root endpoint transactions use the existing mapped
  translation/data path and report the supported bit in
  `REG_ARCH_SECURITY_STATUS`.
- Invalid security-state endpoint transactions remain rejected before translation
  with `F_UUT`/unsupported-upstream event records.
- `SecureRealmRootEndpointAcceptedInvalidRejectedBeforeTranslation` verifies
  Secure/Realm/Root read and debug-read success plus invalid-state event-record
  rejection.

## Verification evidence

| Check | Evidence | Result |
| --- | --- | --- |
| Focused QBox component build | `build/verification/smmu-root-endpoint-build-20260511.log` | PASS: `Built target apollo-smmu-tbu-tests` |
| Focused SMMU TBU CTest | `build/verification/smmu-root-endpoint-ctest-20260511.log` | PASS: `100% tests passed, 0 tests failed out of 1` |
| Focused Secure/Realm/Root endpoint gTest | `build/verification/smmu-root-endpoint-gtest-20260511.log` | PASS: 3 focused Secure/Realm/Root endpoint/EVENTQ tests passed |
| Static/syntax/checker bundle | `build/verification/smmu-root-endpoint-static-20260511.log` | PASS: `SUMMARY {"pass": 726}` |
| Buildroot/QBox lane contract | `build/verification/smmu-root-endpoint-lane-20260511.log` | PASS: lane conclusion emitted after contract checks |
| Final closure replay | `build/verification/smmu-root-endpoint-final-closure-check-20260511.log` | PASS: `git diff --check`, checklist JSON validation, and final checker replay passed |

## Component coverage

- Secure, Realm, and Root endpoint reads and debug reads resolve through the dynamic
  SMMU map and preserve `REG_ARCH_SECURITY_STATUS` supported-state reporting.
- Invalid security-state endpoint transactions generate unsupported-upstream
  `F_UUT` records before translation and preserve the unsupported-event path.

## Remaining blockers

This closes the modeled four-state endpoint acceptance gap, but it is not full
RME endpoint compliance. Complete Realm/Root GPT/GPC behavior still requires the
RME/GPT/GPC model; full compliance also requires byte-exact TLBI
reference-vector
matrices, complete event-matrix coverage, and upstream `arm-smmu-v3` lifecycle
parity.
