# QBox SMMUv3 PRI STE.PPAR lookup event verification — 2026-05-11

## Scope

SMMU-COMP-060 PRI STE.PPAR lookup event-recording slice.

When a PASID-prefixed Last PPR is discarded because PRIQ overflow is active and
`SMMU_IDR3.PPS==0`, the SMMU checks the associated `STE.PPAR`.  This slice
models the event-recording gates for faults observed during that `STE.PPAR`
lookup:

- `C_BAD_STREAMID` is recorded only when both `CR2.REC_CFG_ATS` and
  `CR2.RECINVSID` are set.
- `F_STE_FETCH`, `F_VMS_FETCH`, `C_BAD_STE`, and modeled configuration-fault
  cases are recorded when `CR2.REC_CFG_ATS` is set.
- Otherwise the auto-response still returns Response Failure, but the EVENTQ
  record is suppressed.

This verifies the modeled `C_BAD_STE` path with REC_CFG_ATS on/off.

## Ground truth

Local reference:
`sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
states that STE.PPAR lookup failures during PRI overflow may be recorded in the
Event queue according to `CR2.REC_CFG_ATS` and `CR2.RECINVSID` gates.

## Implementation evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - `arch_pri_ppar_lookup_fault_recordable()`
  - `record_pri_ppar_lookup_fault()`
  - `m_arch_pri_ppar_lookup_fault_records`
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - `PriProtocolPparLookupFaultHonorsRecCfgAts`
- `scripts/check_qbox_smmuv3_compliance.py`
- `scripts/check_buildroot_arm64_lane.sh`

## Verification evidence

Expected durable logs for this slice:

- `build/verification/smmu-pri-ppar-lookup-event-build-20260511.log`
- `build/verification/smmu-pri-ppar-lookup-event-gtest-20260511.log`
- `build/verification/smmu-pri-ppar-lookup-event-ctest-20260511.log`
- `build/verification/smmu-pri-ppar-lookup-event-static-20260511.json`
- `build/verification/smmu-pri-ppar-lookup-event-lane-20260511.log`
- `build/verification/smmu-pri-ppar-lookup-event-final-closure-check-20260511.log`
- `build/verification/smmu-pri-ppar-lookup-event-evidence-summary-final-20260511.log`

## No-overclaim boundary

`full_smmuv3_compliance` must remain `not_claimed`.  This slice does not provide
full PCIe packet transport, complete upstream arm-smmu-v3 recovery parity,
RME/GPT/GPC policy, or complete Secure/Realm command/event lifecycle parity.
