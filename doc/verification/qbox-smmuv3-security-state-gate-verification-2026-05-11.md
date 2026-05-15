# QBox SMMUv3 security-state gate verification - 2026-05-11

## Scope

SMMU-COMP-030/050 security-state unsupported-gate functional slice.

Evidence pattern: SMMU-COMP-030/050 security-state unsupported-gate functional
slice, including Secure/Realm/Root negative matrix coverage.

This slice prevents QBox from silently treating endpoint traffic tagged as
Secure, Realm, or Root as ordinary Non-secure traffic. The current QBox Apollo
TBU model remains Non-secure-only, but endpoint TLM transactions can now carry a
`security_state` tag. The TBU records that tag, accepts only
`ARCH_SECURITY_NONSECURE`, and rejects unsupported security states before stream
selection, dynamic-map lookup, ATS fill, or downstream data movement. The
component test now covers Secure, Realm, and Root tags as a negative matrix. The
reject path records an architected `F_UUT` event with zero implementation-defined
reason, matching the existing unsupported-upstream event slice. The same guard is
also applied to `transport_dbg()` so debug reads cannot bypass the unsupported
security-state policy.

Ground truth used for this slice:

- `sources/smmu/wiki/concepts/security-states.md`
  - Non-secure state is always present; Secure/Realm/Root require separate
    architectural state and routing.
- `sources/smmu/wiki/synthesis/smmu-security-states.md`
  - A full implementation qualifies stream-table, event-queue, command, and
    output-PA behavior by security state.

## Implementation evidence

- `sources/qbox/systemc-components/common/include/tlm-extensions/apollo-smmu-stream-id.h`
  - `security_state`
  - `copy_from()` preserves `security_state` with the rest of the extension.
- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - `ARCH_SECURITY_NONSECURE`, `ARCH_SECURITY_SECURE`,
    `ARCH_SECURITY_REALM`, `ARCH_SECURITY_ROOT`
  - `transaction_security_state()`
  - `arch_security_state_supported()`
  - `REG_ARCH_SECURITY_STATUS`
  - `b_transport()` and `transport_dbg()` security-state gates
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - `stream_read32_security()`
  - `stream_dbg_read32_security()`
  - `unsupported_states` matrix for Secure/Realm/Root
  - `UnsupportedSecurityStateIsRejectedBeforeTranslation`

## Validation evidence

| Check | Evidence |
| --- | --- |
| Build | `build/verification/apollo-smmu-tbu-security-state-matrix-build-20260511.log` (`Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`) |
| Component CTest | `build/verification/apollo-smmu-tbu-security-state-matrix-ctest-20260511.log` (`100% tests passed, 0 tests failed out of 1`) |
| Focused gTest | `build/verification/apollo-smmu-tbu-security-state-matrix-gtest-20260511.log` (`[  PASSED  ] 1 test.`) |
| Syntax checks | `build/verification/smmu-security-state-gate-syntax-20260511.log` |
| Static/lane checker | `build/verification/smmu-security-state-gate-static-final-20260511.log` (`PASS  tbu:unsupported-security-state-gate`, `SUMMARY {"pass": 585}`) |
| Compliance JSON | `build/verification/qbox-smmuv3-compliance-security-state-gate-final-20260511.json` (`full_smmuv3_compliance: not_claimed`) |

## Result

`UnsupportedSecurityStateIsRejectedBeforeTranslation` proves Secure, Realm, and
Root tagged endpoint traffic is rejected with `TLM_ADDRESS_ERROR_RESPONSE`,
records `ARCH_FAULT_UNSUPPORTED_UPSTREAM`, emits one `F_UUT` EVENTQ entry per
state, and leaves the mapped downstream memory untouched. The same test then
sends an explicitly Non-secure transaction over the same StreamID/IOVA and
verifies it translates to the staged payload, proving the guard does not break
the current Non-secure path.

The focused test also verifies the debug path: Secure/Realm/Root tagged
`transport_dbg()` calls return zero bytes and record unsupported security-state
status, while a Non-secure debug read over the same StreamID/IOVA returns the
staged payload.

Remaining blockers: actual Secure and Realm stream-table banks, Secure/Realm
command and event queues, Root/Realm RME/GPC routing, Secure/Realm MPAM_NS/SP
selection, IDE/SEC_SID packet decoding, and upstream Linux recovery parity
remain open.
