# QBox SMMUv3 configuration-event RES0 payload verification - 2026-05-11

## Scope

SMMU-COMP-050 configuration-event RES0 payload functional slice.

This slice covers non-stall Event queue records for `C_BAD_STREAMID`,
`C_BAD_STE`, `C_BAD_CD`, and `F_STREAM_DISABLED`. It does **not** alter stalled
fault replay records and does not claim full event priority, event merging,
Secure/Realm routing, translated ATS configuration-fault gates, or upstream Linux
recovery parity.

## Ground truth

- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md:26822`:
  `C_BAD_STREAMID` has only StreamID/SubstreamID/SSV in word0 and upper payload
  bits are RES0.
- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md:26884`:
  `C_BAD_STE` carries no InputAddr payload; unspecified bits are RES0.
- `sources/smmu/cpp/src/smmu/smmu.cpp:5929`: pinned reference zeros InputAddr
  and SubstreamID payload for `C_BAD_STREAMID`, `C_BAD_STE`, `C_BAD_CD`, and
  `F_STREAM_DISABLED`, while excluding `C_BAD_SUBSTREAMID` because it defines an
  InputAddr field.

## Implemented QBox behavior

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - Adds `arch_event_record_has_res0_payload()`.
  - Zeros non-stall word1/word2 payloads for `C_BAD_STREAMID`, `C_BAD_STE`,
    `C_BAD_CD`, and `F_STREAM_DISABLED`.
  - Leaves stalled replay records unchanged so STAG/STALL/InputAddr resume flows
    remain intact.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Extends `BadStreamIdHonorsCr2RecInvsidForEventRecording` to verify zero
    payload words for `C_BAD_STREAMID`.
  - Adds `ArchitectedConfigEventPayloadsAreRes0` for non-stall `C_BAD_STE`,
    `C_BAD_CD`, and `F_STREAM_DISABLED` payload words.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh`
  - Add durable static/lane guards for the configuration-event RES0 payload
    slice.

## Verification commands and evidence

```sh
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)" \
  2>&1 | tee build/verification/apollo-smmu-tbu-config-event-res0-build-20260511.log
ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure \
  2>&1 | tee build/verification/apollo-smmu-tbu-config-event-res0-ctest-20260511.log
```

Final static/lane verification is recorded in
`build/verification/smmu-config-event-res0-static-final-20260511.log` and the
JSON checker output is recorded in
`build/verification/qbox-smmuv3-compliance-config-event-res0-final-20260511.json`.

Observed results:

- Build log:
  `build/verification/apollo-smmu-tbu-config-event-res0-build-20260511.log`
  reports `Built target apollo_smmu_tbu` and
  `Built target apollo-smmu-tbu-tests`.
- CTest log:
  `build/verification/apollo-smmu-tbu-config-event-res0-ctest-20260511.log`
  reports `100% tests passed, 0 tests failed out of 1`.
- Static checker JSON summary:
  `{"pass": 420}`.
- Static checker target:
  `tbu:event-record-config-res0-payload` is `pass`.
- Lane guard:
  `build/verification/smmu-config-event-res0-static-final-20260511.log`
  reports both configuration-event RES0 payload guards as `PASS`.

## Current limitation

The aggregate compliance checker still reports `full_smmuv3_compliance` as
`not_claimed`; this slice only corrects non-stall configuration-event payload
layout.
