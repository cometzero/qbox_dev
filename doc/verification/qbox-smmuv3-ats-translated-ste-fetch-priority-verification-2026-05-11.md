# QBox SMMUv3 ATS Translated F_STE_FETCH priority verification

- Date: 2026-05-11
- Workspace: `/build/qbox_dev`
- Scope: SMMU-COMP-050/060 ATS Translated F_STE_FETCH priority functional slice.

## Result

PASS for this incremental slice. The component suite now proves that ATS
Translated traffic with `CR0.SMMUEN==1` and `CR0.ATSCHK==1` reports an STE fetch
abort as `F_STE_FETCH` before decoding the STE or applying an `STE.EATS` based
`F_TRANSL_FORBIDDEN` decision.

The test also proves the `CR2.REC_CFG_ATS` event-recording gate for this
Translated-transaction configuration fetch fault:

- `REC_CFG_ATS==0`: private fault reason is `ARCH_FAULT_STE_FETCH`, but no
  EVENTQ entry is produced.
- `REC_CFG_ATS==1`: EVENTQ records event `F_STE_FETCH`, Reason word1 is zero,
  and FetchAddr is encoded in word3.

This is not a full SMMUv3 compliance claim. Remaining parity gaps include
Secure/Realm priority cases, real `F_VMS_FETCH` priority from VMS pointer walks,
configuration-cache conflict detection, DPT/GPC ordering, and upstream Linux
`arm-smmu-v3` recovery behavior.

## Changed coverage

- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Added `AtsTranslatedSteFetchRecordsBeforeSteDecode`.
- `scripts/check_qbox_smmuv3_compliance.py`
  - Added `tbu:ats-translated-priority-ste-fetch`.
- `scripts/check_buildroot_arm64_lane.sh`
  - Added a static guard for the ATS Translated `F_STE_FETCH` priority vector.
- `doc/spec/qbox-smmuv3-compliance-checklist.md`
  - Updated SMMU-COMP-050/060 evidence while preserving `functional-slice` status.

## Verification evidence

| Check | Evidence |
| --- | --- |
| Build | `build/verification/apollo-smmu-tbu-ats-translated-ste-fetch-priority-build-20260511.log` |
| Component test | `build/verification/apollo-smmu-tbu-ats-translated-ste-fetch-priority-ctest-20260511.log` |
| Static/checker/lane | `build/verification/smmu-ats-translated-ste-fetch-priority-static-final-20260511.log` |
| JSON report | `build/verification/qbox-smmuv3-compliance-ats-translated-ste-fetch-priority-final-20260511.json` |

Observed markers:

- Build log: `Built target apollo_smmu_tbu` and
  `Built target apollo-smmu-tbu-tests`.
- CTest log: `100% tests passed, 0 tests failed out of 1`.
- Static/checker/lane log: `PASS  tbu:ats-translated-priority-ste-fetch`.
- Checker classification remains `full_smmuv3_compliance=not_claimed`.
