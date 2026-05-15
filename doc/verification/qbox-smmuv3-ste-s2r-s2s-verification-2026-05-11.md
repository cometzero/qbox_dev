# QBox SMMUv3 STE.S2R/S2S stage-2 fault-policy verification

- Date: 2026-05-11
- Scope: `/build/qbox_dev`
- Slice: SMMU-COMP-030/050 STE.S2R/S2S stage-2 record/stall policy
- Result: PASS for the modeled QBox stage-2 fault record/stall policy slice.
  Full SMMUv3 event, stall, RME/GPT/GPC, and upstream arm-smmu-v3 parity
  remain open.

## What changed

- Added modeled `ARCH_STE_S2R` and `ARCH_STE_S2S` bits to STE word 1 and the
  STE reserved-bit acceptance mask.
- Added `apply_arch_stage2_fault_policy()` and `m_arch_fault_stage2_stall` so
  stage-2 faults use STE.S2R for event-record suppression and STE.S2S for
  stall-vs-terminate selection.
- Applied the policy to stage-2-only faults, nested CD/L1CD/TT-fetch stage-2
  faults, nested S1DSS-bypass stage-2 faults, and final nested stage-2 walks.
- Added `Stage2SteS2rS2sControlsRecordAndStall`, verifying:
  - `S2R=0,S2S=0` suppresses the modeled EVENTQ record.
  - `S2R=1,S2S=0` records a non-stall stage-2 fault event.
  - `S2R=0,S2S=1` records a stalled stage-2 fault with a pending STAG.

## Verification evidence

| Check | Evidence | Result |
| --- | --- | --- |
| Focused QBox component build | `build/verification/smmu-ste-s2r-s2s-build-20260511.log` | PASS: `Built target apollo-smmu-tbu-tests` |
| Focused SMMU TBU CTest | `build/verification/smmu-ste-s2r-s2s-ctest-20260511.log` | PASS: `100% tests passed, 0 tests failed out of 1` |
| Focused STE.S2R/S2S and nested S2 gTest | `build/verification/smmu-ste-s2r-s2s-gtest-20260511.log` | PASS: `[  PASSED  ] 4 tests.` |
| Static/syntax/checker bundle | `build/verification/smmu-ste-s2r-s2s-static-20260511.log` | PASS: `SUMMARY {"pass": 754}` |
| Buildroot/QBox lane contract | `build/verification/smmu-ste-s2r-s2s-lane-20260511.log` | PASS: lane conclusion emitted after contract checks |
| Final closure replay | `build/verification/smmu-ste-s2r-s2s-final-closure-check-20260511.log` | PASS: `PASS: final STE.S2R/S2S closure checks completed` |

## Remaining blockers

This is a focused modeled stage-2 fault-policy slice. It does not close full
SMMUv3 compliance. Remaining work includes byte-exact event-record parity across
all stage-2 fault causes, STALL_MODEL validation, complete Realm/RME/GPT/GPC
policy, complete PRI/ATS packet-level behavior, and upstream `arm-smmu-v3`
lifecycle parity.
