# QBox SMMUv3 EVENTQ fetch-fault word1 verification

- Date: 2026-05-11
- Workspace: `/build/qbox_dev`
- Scope: SMMU-COMP-050 EVENTQ fetch-fault word1 functional slice.

## Result

PASS for this incremental slice. The Apollo SMMU TBU now encodes non-stall
`F_STE_FETCH`, `F_CD_FETCH`, `F_WALK_EABT`, and `F_VMS_FETCH` EVENTQ word1 as
the implementation-defined fetch-fault Reason field with Reason=0 plus the
modeled GPCF bit, rather than reusing the transaction InputAddr. FetchAddr
remains encoded in EVENTQ word3.

This is not a full SMMUv3 compliance claim. Full fetch-event parity still needs
complete implementation-defined Reason values, Secure/Realm routing, real
RME/GPT/GPC causality, and upstream Linux `arm-smmu-v3` event-thread recovery
parity.

## Changed coverage

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - Added `arch_event_record_has_fetch_reason()`.
  - Updated non-stall EVENTQ word1 encoding so fetch-fault events report
    Reason=0 plus modeled GPCF.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Extended `ArchitectedEventRecordFetchAddressIsEncoded` to verify
    `F_STE_FETCH` word1 is zero and `F_CD_FETCH` word1 carries GPCF while
    word3 carries FetchAddr.
- `scripts/check_qbox_smmuv3_compliance.py`
  - Added `tbu:event-record-fetch-reason-gpcf`.
- `scripts/check_buildroot_arm64_lane.sh`
  - Added a static lane guard for the fetch-fault Reason/GPCF encoder.

## Verification evidence

| Check | Evidence |
| --- | --- |
| Build | `build/verification/apollo-smmu-tbu-event-fetch-reason-build-20260511.log` |
| Component test | `build/verification/apollo-smmu-tbu-event-fetch-reason-ctest-20260511.log` |
| Static/checker/lane | `build/verification/smmu-event-fetch-reason-static-final-20260511.log` |
| JSON report | `build/verification/qbox-smmuv3-compliance-event-fetch-reason-final-20260511.json` |

Observed markers:

- Build log: `Built target apollo_smmu_tbu` and
  `Built target apollo-smmu-tbu-tests`.
- CTest log: `100% tests passed, 0 tests failed out of 1`.
- Static/checker/lane log: `PASS  tbu:event-record-fetch-reason-gpcf`.
- Static/checker/lane log: `full_smmuv3_compliance=not_claimed` in the checker
  classification, preserving the no-overclaiming gate.
