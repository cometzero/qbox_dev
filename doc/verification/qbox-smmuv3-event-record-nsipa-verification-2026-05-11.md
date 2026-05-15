# QBox SMMUv3 EVENTQ NSIPA Verification - 2026-05-11

## Scope

SMMU-COMP-050 EVENTQ NSIPA functional slice.

This component-level slice adds modeled EVENTQ `NSIPA` bit plumbing for stalled
stage-2 records when the Apollo TBU is explicitly supplied a modeled Non-secure
IPA indication. It covers field encoding only.

This is **not** full Secure-state SMMUv3 compliance. QBox still does not
implement Secure Event queue selection, Secure/Non-secure stream-table banks,
Secure STE `NSCFG`/`S2TTB` versus `S_S2TTB` routing, or complete per-security
state command/event queue lifecycle.

## Ground-truth references

- `sources/smmu/wiki/concepts/event-queue.md` records `NSIPA` as a common
  EVENTQ field that is zero unless an event is recorded on the Secure event
  queue with `S2 == 1`.
- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
  §7.3 states that `NSIPA` differentiates Secure versus Non-secure IPA space for
  IPA-recording stage-2 faults on Secure streams.
- The local Arm spec figure for `F_TRANSLATION` places `NSIPA` in EVENTQ word1
  at architectural bit 102, i.e. word1 bit `38`.

## Implementation evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - adds `ARCH_EVENT_NSIPA_SHIFT` for the EVENTQ bit position;
  - adds `m_arch_fault_nsipa` modeled fault-cause state;
  - resets the modeled `NSIPA` state across fault/probe/replay paths;
  - emits `NSIPA` from `arch_event_record_word1()` only for modeled stage-2
    records.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - adds `ArchitectedEventRecordNsipaBitIsEncoded`, covering a stalled
    `F_TRANSLATION` stage-2 record with `STALL`, `S2`, `NSIPA`, `CLASS=IN`,
    `InputAddr`, and IPA word3 populated.
- `scripts/check_qbox_smmuv3_compliance.py`
  - adds `tbu:event-record-nsipa` and keeps
    `full_smmuv3_compliance=not_claimed`.
- `scripts/check_buildroot_arm64_lane.sh`
  - adds source/test contract greps for the NSIPA field-plumbing slice.

## Validation evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Component build | PASS | `build/verification/apollo-smmu-tbu-event-nsipa-build-20260511.log`: `Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests` |
| Component CTest | PASS | `build/verification/apollo-smmu-tbu-event-nsipa-ctest-20260511.log`: `100% tests passed, 0 tests failed out of 1` |
| Static/checker/lane | PASS | `build/verification/smmu-event-nsipa-static-final-20260511.log`: `PASS  tbu:event-record-nsipa`, `SUMMARY {"pass": 374}`, lane conclusion passed; JSON `build/verification/qbox-smmuv3-compliance-event-nsipa-final-20260511.json` keeps `full_smmuv3_compliance=not_claimed`. |

## Remaining blockers

- Full Secure event queue/security-state routing: Secure stream-table banks,
  Secure event queue selection, Secure `NSCFG`, `S2TTB`/`S_S2TTB`, and queue
  lifecycle parity.
- Full EVENTQ byte-exact parity for every Arm SMMUv3 event type and security
  state.
- Full RME/GPT/GPC model: Root/Realm controls, GPT walks, SMMU-originated GPC
  checks, GPF/GPT fault registers, interrupt/observability rules, and
  `CMD_SYNC` ordering guarantees.
- Upstream Linux `arm-smmu-v3` event-thread recovery parity.
