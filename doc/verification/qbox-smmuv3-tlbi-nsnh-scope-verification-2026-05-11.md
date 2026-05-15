# QBox SMMUv3 TLBI_NSNH_ALL scoped invalidation verification

- Date: 2026-05-11
- Scope: `/build/qbox_dev`
- Slice: SMMU-COMP-020/040 TLBI_NSNH_ALL reference-vector scope slice
- Result: PASS for modeled Non-secure Non-Hyp TLBI_NSNH_ALL scoping. Full
  TLBI/RME/reference-vector parity remains open.

## What changed

- Added a modeled `ARCH_TLBI_REGIME_NSNH`/`ARCH_TLBI_REGIME_EL2` tag to ATS
  cache entries so command tests can distinguish Non-secure Non-Hyp entries from
  EL2-regime entries.
- Added `clear_ats_cache_nsnh()`, used by `CMD_TLBI_NSNH_ALL`, so the opcode no
  longer behaves as a blanket Non-secure cache flush for explicitly tagged EL2
  entries.
- Added `CmdqTlbiNsnhAllPreservesEl2RegimeEntries`, which verifies
  `CMD_TLBI_NSNH_ALL` invalidates one NSNH-tagged ATS entry and preserves an
  EL2-regime ATS entry with the same ASID/VMID.

## Verification evidence

| Check | Evidence | Result |
| --- | --- | --- |
| Focused QBox component build | `build/verification/smmu-tlbi-nsnh-scope-build-20260511.log` | PASS: `Built target apollo-smmu-tbu-tests` |
| Focused SMMU TBU CTest | `build/verification/smmu-tlbi-nsnh-scope-ctest-20260511.log` | PASS: `100% tests passed, 0 tests failed out of 1` |
| Focused TLBI_NSNH scope gTest | `build/verification/smmu-tlbi-nsnh-scope-gtest-20260511.log` | PASS: `[  PASSED  ] 2 tests.` |
| Static/syntax/checker bundle | `build/verification/smmu-tlbi-nsnh-scope-static-20260511.log` | PASS: `SUMMARY {"pass": 747}` |
| Buildroot/QBox lane contract | `build/verification/smmu-tlbi-nsnh-scope-lane-20260511.log` | PASS: lane conclusion emitted after contract checks |

## Remaining blockers

This narrows one TLBI reference-vector parity gap but does not claim full TLBI
coverage. Remaining work includes byte-exact TTL/Leaf/RIL matrices for all
command encodings, real stream-world derivation from STE/CD/security state,
Realm/RME command encodings, GPT/GPC behavior, and upstream `arm-smmu-v3`
lifecycle parity.
