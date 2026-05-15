# QBox SMMUv3 EVENTQ F_VMS_FETCH Verification - 2026-05-11

## Scope

SMMU-COMP-050 EVENTQ F_VMS_FETCH functional slice.

This component-level slice closes one EVENTQ matrix gap by modeling the
architected `F_VMS_FETCH` event number (`0x25`) and its fetch-address word3
encoding in the Apollo SMMU TBU EVENTQ record path.

The slice is intentionally narrow. It does **not** implement full SMMUv3 VMS,
MPAM `PARTID_MAP`, VMS pointer decode, VMS caching, `CMD_CFGI_VMS_PIDM`, Secure
state `NSIPA`, or RME `GPCF`. Those remain explicit full-compliance blockers.

## Ground-truth references

- `sources/smmu/wiki/concepts/event-queue.md` documents that
  `F_STE_FETCH`, `F_CD_FETCH`, `F_VMS_FETCH`, and `F_WALK_EABT` carry a
  fetch-address field.
- `sources/smmu/wiki/concepts/virtual-machine-structure.md` documents
  speculative VMS access external abort reporting as `F_VMS_FETCH`.
- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
  records `F_VMS_FETCH` as event/fault code `0x25` and describes `FetchAddr` as
  the physical address used for the VMS fetch.

## Implementation evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - adds `ARCH_FAULT_VMS_FETCH`;
  - adds `ARCH_EVENT_F_VMS_FETCH = 0x25`;
  - maps VMS fetch faults through `arch_event_number_for_fault()`;
  - includes `ARCH_EVENT_F_VMS_FETCH` in `arch_event_record_word3()` so the
    masked fetch address is emitted in EVENTQ word3.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - adds `ArchitectedEventRecordVmsFetchCarriesFetchAddress`, covering event
    number `0x25`, SSV/SubstreamID, StreamID, fetch-address word3, and private
    fault detail reason.
- `scripts/check_qbox_smmuv3_compliance.py`
  - adds `tbu:event-record-vms-fetch` and keeps
    `full_smmuv3_compliance=not_claimed`.
- `scripts/check_buildroot_arm64_lane.sh`
  - adds source/test contract greps for the F_VMS_FETCH slice.

## Validation evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Component build | PASS | `build/verification/apollo-smmu-tbu-event-vms-fetch-build-20260511.log`: `Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests` |
| Component CTest | PASS | `build/verification/apollo-smmu-tbu-event-vms-fetch-ctest-20260511.log`: `100% tests passed, 0 tests failed out of 1` |
| Static/checker/lane | PASS | `build/verification/smmu-event-vms-fetch-static-final-20260511.log`: `PASS  tbu:event-record-vms-fetch`, `SUMMARY {"pass": 366}`, Buildroot lane PASS, and superproject/`sources/qbox`/`sources/linux` diff checks PASS. |

## Remaining blockers

- Full VMS/MPAM support: `STE.VMSPtr`, `STE.S1MPAM`, VMS `PARTID_MAP`, VMS
  cache model, `CMD_CFGI_VMS_PIDM`, and priority relative to lower-priority
  events.
- Full EVENTQ byte-exact parity for all Arm SMMUv3 event types.
- Secure-state `NSIPA` and RME `GPCF` event fields.
- Upstream Linux `arm-smmu-v3` event-thread recovery parity.
