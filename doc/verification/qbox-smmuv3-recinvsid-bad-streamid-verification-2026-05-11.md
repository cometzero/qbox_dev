# QBox SMMUv3 C_BAD_STREAMID RECINVSID verification - 2026-05-11

## Scope

SMMU-COMP-050 C_BAD_STREAMID RECINVSID functional slice.

This slice covers normal stream/context probe traffic with an out-of-range
StreamID. It does **not** claim full translated-transaction event gating,
Secure/Realm CR2 banking, event merging, full event priority validation, or
upstream Linux arm-smmu-v3 recovery parity.

## Ground truth

- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md:12543`:
  `SMMU_CR2.RECINVSID` records `C_BAD_STREAMID` from invalid input StreamIDs.
- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md:13905`:
  out-of-range StreamIDs terminate with abort and record `C_BAD_STREAMID` if
  permitted by `SMMU_CR2.RECINVSID`.
- `sources/smmu/cpp/include/smmu/smmu.h:37`: pinned reference documents that
  `RECINVSID=0` suppresses `C_BAD_STREAMID` Event queue recording.

## Implemented QBox behavior

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - Adds `arch_record_bad_streamid_event()` for the normal `RECINVSID` gate.
  - Preserves private `ARCH_FAULT_BAD_STREAM_ID` status when a probe fails.
  - Suppresses EVENTQ recording for normal `C_BAD_STREAMID` when
    `CR2.RECINVSID=0`.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Adds `BadStreamIdHonorsCr2RecInvsidForEventRecording`, verifying
    no producer movement/no event when `RECINVSID=0`, then event number and
    StreamID recording when `RECINVSID=1`.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh`
  - Add durable static/lane guards for the normal `C_BAD_STREAMID` RECINVSID
    slice.

## Verification commands and evidence

```sh
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)" \
  2>&1 | tee build/verification/apollo-smmu-tbu-recinvsid-bad-streamid-build-20260511.log
ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure \
  2>&1 | tee build/verification/apollo-smmu-tbu-recinvsid-bad-streamid-ctest-20260511.log
```

Final static/lane verification is recorded in
`build/verification/smmu-recinvsid-bad-streamid-static-final-20260511.log` and
the JSON checker output is recorded in
`build/verification/qbox-smmuv3-compliance-recinvsid-bad-streamid-final-20260511.json`.

Observed:

- `build/verification/apollo-smmu-tbu-recinvsid-bad-streamid-build-20260511.log`
  contains `Built target apollo_smmu_tbu` and
  `Built target apollo-smmu-tbu-tests`.
- `build/verification/apollo-smmu-tbu-recinvsid-bad-streamid-ctest-20260511.log`
  contains `100% tests passed, 0 tests failed out of 1`.
- `build/verification/smmu-recinvsid-bad-streamid-static-final-20260511.log`
  contains `PASS  tbu:bad-streamid-recinvsid-gate`, `SUMMARY {"pass": 416}`,
  and the Buildroot lane conclusion.

## Current limitation

The aggregate compliance checker still reports `full_smmuv3_compliance` as
`not_claimed`; this slice only closes the normal `C_BAD_STREAMID` RECINVSID
EVENTQ recording gate.
