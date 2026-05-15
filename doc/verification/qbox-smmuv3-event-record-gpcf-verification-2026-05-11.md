# QBox SMMUv3 EVENTQ GPCF Verification - 2026-05-11

## Scope

SMMU-COMP-050 EVENTQ GPCF functional slice.

This component-level slice adds modeled EVENTQ `GPCF` bit plumbing for fetch-event
records when the Apollo TBU is explicitly supplied a modeled Granule Protection
Check fault cause. It covers the event-record bit plumbing only.

This is **not** full RME/GPT/GPC compliance. The QBox model still does not
implement Root/Realm register banks, GPT walks, SMMU-originated GPC checks,
client-originated GPC behavior, GPF/GPT fault registers, or complete GPC
ordering/observability rules.

## Ground-truth references

- `sources/smmu/wiki/concepts/event-queue.md` identifies `GPCF` as a common
  EVENTQ field for Granule Protection Check Fault indication.
- `sources/smmu/wiki/concepts/granule-protection-check.md` states that
  `F_STE_FETCH`, `F_CD_FETCH`, `F_VMS_FETCH`, and `F_WALK_EABT` records have a
  `GPCF` field at bit 80.
- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
  records that those fetch events can report `GPCF==1` when they arise from a
  GPC fault.

## Implementation evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - adds `ARCH_EVENT_GPCF_SHIFT` for the EVENTQ bit position;
  - adds `m_arch_fault_gpcf` modeled fault-cause state;
  - extends `set_arch_fetch_fault(..., gpcf)` to mark fetch records that arose
    from a modeled GPC fault;
  - emits `GPCF` in `arch_event_record_word1()` for fetch-event records while
    preserving the existing `FetchAddr` word3 path.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - adds `ArchitectedEventRecordFetchGpcfBitIsEncoded`, covering a stalled
    `F_WALK_EABT` record with `STALL`, `GPCF`, and `FetchAddr` populated.
- `scripts/check_qbox_smmuv3_compliance.py`
  - adds `tbu:event-record-gpcf` and keeps
    `full_smmuv3_compliance=not_claimed`.
- `scripts/check_buildroot_arm64_lane.sh`
  - adds source/test contract greps for the GPCF field-plumbing slice.

## Validation evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Component build | PASS | `build/verification/apollo-smmu-tbu-event-gpcf-build-20260511.log`: `Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests` |
| Component CTest | PASS | `build/verification/apollo-smmu-tbu-event-gpcf-ctest-20260511.log`: `100% tests passed, 0 tests failed out of 1` |
| Static/checker/lane | PASS | `build/verification/smmu-event-gpcf-static-final-20260511.log`: `PASS  tbu:event-record-gpcf`, `SUMMARY {"pass": 370}`, lane conclusion passed; JSON `build/verification/qbox-smmuv3-compliance-event-gpcf-final-20260511.json` keeps `full_smmuv3_compliance=not_claimed`. |

## Remaining blockers

- Full RME/GPT/GPC model: Root/Realm controls, GPT walks, SMMU-originated GPC
  checks, GPF/GPT fault registers, interrupt/observability rules, and
  `CMD_SYNC` ordering guarantees.
- Full EVENTQ byte-exact parity for every Arm SMMUv3 event type and security
  state.
- Secure-state `NSIPA` event field and Secure event queue selection.
- Upstream Linux `arm-smmu-v3` event-thread recovery parity.
