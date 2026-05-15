# QBox SMMUv3 F_UUT EVENTQ verification - 2026-05-11

## Scope

SMMU-COMP-050 F_UUT unsupported-upstream EVENTQ functional slice.

This slice adds modeled/harness-injected unsupported-upstream transaction event
recording to the Apollo TBU. It does **not** claim full unsupported AMBA/PCIe/CXL
transaction classification, ATS Translated no-event matrix coverage, Secure/Realm
event routing, or upstream Linux arm-smmu-v3 recovery parity.

## Ground truth

- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md:26812`:
  SMMUv3 section 7.3.2 defines `F_UUT` for unsupported upstream transactions.
- `sources/smmu/cpp/include/smmu/types.h:1652`: pinned reference event number
  `F_UUT = 0x01`.
- `sources/smmu/cpp/include/smmu/types.h:1706`: pinned reference documents the
  implementation-defined F_UUT Reason field and uses zero for this software
  model.
- `sources/smmu/cpp/include/smmu/smmu.h:181` and
  `sources/smmu/cpp/src/smmu/smmu.cpp:3471`: pinned reference exposes a harness
  API to inject/report unsupported transactions.

## Implemented QBox behavior

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - Adds `FEATURE_ARCH_F_UUT_EVENT`.
  - Adds private compliance control `ARCH_CTRL_RECORD_F_UUT`.
  - Adds modeled reason `ARCH_FAULT_UNSUPPORTED_UPSTREAM`.
  - Maps that reason to `ARCH_EVENT_F_UUT = 0x01`.
  - Encodes F_UUT word1 as zero Reason/RES0 and word2/word3 as zero.
  - Allows the modeled F_UUT event to be recorded with `CR0.EVENTQEN` even when
    `CR0.SMMUEN` is clear.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Adds `ArchitectedUnsupportedUpstreamEventCanBeInjected`, checking event
    number, StreamID, zero Reason/RES0 words, private fault detail, and Event
    queue producer update.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh`
  - Add durable static/lane guards for the F_UUT slice.

## Verification commands and evidence

```sh
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)" \
  2>&1 | tee build/verification/apollo-smmu-tbu-f-uut-event-build-20260511.log
ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure \
  2>&1 | tee build/verification/apollo-smmu-tbu-f-uut-event-ctest-20260511.log
```

Observed:

- `build/verification/apollo-smmu-tbu-f-uut-event-build-20260511.log` contains
  `Built target apollo_smmu_tbu` and `Built target apollo-smmu-tbu-tests`.
- `build/verification/apollo-smmu-tbu-f-uut-event-ctest-20260511.log` contains
  `100% tests passed, 0 tests failed out of 1`.

Final static/lane verification is recorded in
`build/verification/smmu-f-uut-event-static-final-20260511.log` and the JSON
checker output is recorded in
`build/verification/qbox-smmuv3-compliance-f-uut-event-final-20260511.json`.

Observed:

- `build/verification/smmu-f-uut-event-static-final-20260511.log` contains
  `PASS  tbu:event-record-f-uut`, `SUMMARY {"pass": 412}`, and the Buildroot
  lane conclusion.
- `build/verification/qbox-smmuv3-compliance-f-uut-event-final-20260511.json`
  reports `full_smmuv3_compliance` as `not_claimed`; this is expected because
  this is only one compliance slice.

## Current limitation

This is intentionally an injection/plumbing slice. Remaining open work includes
real unsupported upstream transaction detection, implementation-defined Reason
classification beyond zero, ATS Translated F_UUT no-event handling, event
priority/MEV subtleties, Secure/Realm event queues, RME/GPT/GPC integration, and
upstream arm-smmu-v3 recovery parity.
