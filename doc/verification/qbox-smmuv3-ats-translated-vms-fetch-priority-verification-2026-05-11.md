# QBox SMMUv3 ATS Translated F_VMS_FETCH priority verification

- Date: 2026-05-11
- Scope: `/build/qbox_dev`
- Slice: SMMU-COMP-050/060 ATS Translated F_VMS_FETCH priority functional slice
- Ground truth used: `sources/smmu/wiki/concepts/virtual-machine-structure.md`

## Implemented slice

The Apollo SMMUv3 TBU now has a narrow, modeled VMS fetch path:

- `FEATURE_ARCH_VMS_FETCH` advertises the functional slice.
- `ARCH_STE_S1MPAM`, `ARCH_STE_VMSPTR_OFFSET`, and
  `ARCH_STE_VMSPTR_MASK` model the minimum STE fields needed to make a
  VMS pointer visible to the compliance harness.
- `arch_fetch_vms_if_enabled()` reads the modeled STE.VMSPtr word when a
  valid nested STE has S1MPAM enabled, then fetches the first VMS word.
- A failed VMS memory access is reported as `ARCH_FAULT_VMS_FETCH` and
  `ARCH_EVENT_F_VMS_FETCH`, with the VMS fetch address in EVENTQ word 3.
- ATS Translated traffic calls this check before falling through to
  `F_TRANSL_FORBIDDEN`, and records/suppresses the configuration event
  according to `SMMU_CR2.REC_CFG_ATS`.

This is intentionally a functional slice. It does not claim full MPAM/VMS,
VMS cache, `CMD_CFGI_VMS_PIDM`, or Secure/Realm VMS semantics.

## Component test

`AtsTranslatedVmsFetchRecordsBeforeForbidden` validates:

1. With `CR2.REC_CFG_ATS == 0`, an ATS Translated transaction targeting a
   nested STE with active modeled VMSPtr aborts with `ARCH_FAULT_VMS_FETCH`
   but does not push an EVENTQ record.
2. With `CR2.REC_CFG_ATS == 1`, the same transaction pushes one EVENTQ
   record with event `ARCH_EVENT_F_VMS_FETCH`.
3. The non-stall fetch-fault word1 remains the implementation-defined zero
   Reason value, and word3 carries the modeled VMS fetch address.
4. The test comment records the event priority: `F_VMS_FETCH` is checked
   before `F_TRANSL_FORBIDDEN`.

## Verification evidence

| Command | Evidence |
| --- | --- |
| `cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j$(nproc)` | `build/verification/apollo-smmu-tbu-ats-translated-vms-fetch-priority-build-20260511.log` |
| `ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure` | `build/verification/apollo-smmu-tbu-ats-translated-vms-fetch-priority-ctest-20260511.log` |
| `bash -n scripts/check_buildroot_arm64_lane.sh` | `build/verification/smmu-ats-translated-vms-fetch-priority-static-final-20260511.log` |
| `python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py` | `build/verification/smmu-ats-translated-vms-fetch-priority-static-final-20260511.log` |
| `python3 scripts/check_qbox_smmuv3_compliance.py --self-test-negative --json build/verification/qbox-smmuv3-compliance-ats-translated-vms-fetch-priority-final-20260511.json` | `build/verification/qbox-smmuv3-compliance-ats-translated-vms-fetch-priority-final-20260511.json` |
| `./scripts/check_buildroot_arm64_lane.sh` | `build/verification/smmu-ats-translated-vms-fetch-priority-static-final-20260511.log` |

## Result

- Build: `Built target apollo_smmu_tbu` and `Built target apollo-smmu-tbu-tests`.
- CTest: `100% tests passed, 0 tests failed out of 1`.
- Static checker/lane: `SUMMARY {"pass": 463}` and lane conclusion passed in `build/verification/smmu-ats-translated-vms-fetch-priority-static-final-20260511.log`.
- Aggregate classification remains `full_smmuv3_compliance=not_claimed`.
