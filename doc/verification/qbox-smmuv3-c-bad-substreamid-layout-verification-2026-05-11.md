# QBox SMMUv3 C_BAD_SUBSTREAMID layout verification - 2026-05-11

SMMU-COMP-050 C_BAD_SUBSTREAMID layout functional slice.

## Scope

This slice verifies the non-stall `C_BAD_SUBSTREAMID` Event queue record layout
for modeled S1DSS/SubstreamID faults. It focuses on the fields that are easy to
regress when sharing helpers with other configuration events:

- event number `0x08`,
- StreamID,
- SubstreamID with SSV asserted,
- `InputAddr` in word1,
- word2/word3 RES0 for this modeled non-stall case.

It does **not** claim full Event queue matrix parity, Secure/Realm routing,
RME/GPT/GPC coverage, or upstream recovery parity.

## Ground truth

- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md:26988`:
  `C_BAD_SUBSTREAMID` records the bad SubstreamID condition.
- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md:27004`:
  the SubstreamID field is always valid for this event.
- `sources/smmu/cpp/src/smmu/smmu.cpp:5931` and `:6123`:
  pinned reference comments state that `C_BAD_SUBSTREAMID` defines `InputAddr`
  and must not be zeroed with other configuration-event payloads.

## Implemented QBox behavior

- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Extends `ArchitectedStreamDisabledAndBadSubstreamEvents` with an explicit
    `C_BAD_SUBSTREAMID` payload check.
  - Verifies the bad SubstreamID record keeps `InputAddr` in word1 and leaves
    word2/word3 zero for this non-stall test vector.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh`
  - Add durable static/lane guards for the `C_BAD_SUBSTREAMID` layout slice.

## Verification commands and evidence

```sh
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)" \
  2>&1 | tee build/verification/apollo-smmu-tbu-c-bad-substreamid-layout-build-20260511.log
ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure \
  2>&1 | tee build/verification/apollo-smmu-tbu-c-bad-substreamid-layout-ctest-20260511.log
```

Static/lane verification:

```sh
rm -rf scripts/__pycache__
{
  bash -n scripts/*.sh
  python3 -m py_compile \
    scripts/check_qbox_smmuv3_compliance.py \
    scripts/check_iree_cnn_pipeline_readiness.py \
    scripts/qbox_pty_runner.py
  scripts/check_qbox_smmuv3_compliance.py --self-test-negative \
    --json build/verification/qbox-smmuv3-compliance-c-bad-substreamid-layout-final-20260511.json
  ./scripts/check_buildroot_arm64_lane.sh
  git diff --check
  git -C sources/qbox diff --check
  git -C sources/linux diff --check
} 2>&1 | tee build/verification/smmu-c-bad-substreamid-layout-static-final-20260511.log
rm -rf scripts/__pycache__
```

Observed result:

- Build log: `build/verification/apollo-smmu-tbu-c-bad-substreamid-layout-build-20260511.log`
  - `Built target apollo_smmu_tbu`
  - `Built target apollo-smmu-tbu-tests`
- CTest log: `build/verification/apollo-smmu-tbu-c-bad-substreamid-layout-ctest-20260511.log`
  - `100% tests passed, 0 tests failed out of 1`
- Static/lane log: `build/verification/smmu-c-bad-substreamid-layout-static-final-20260511.log`
  - `PASS  tbu:event-record-c-bad-substreamid-layout`
  - `PASS: QBox Apollo SMMU TBU C_BAD_SUBSTREAMID payload component test present`
  - `SUMMARY {"pass": 425}`
- JSON checker output:
  `build/verification/qbox-smmuv3-compliance-c-bad-substreamid-layout-final-20260511.json`
  - `summary.pass = 425`
  - `classification.full_smmuv3_compliance = not_claimed`

## Current limitation

The aggregate compliance checker is expected to continue reporting
`full_smmuv3_compliance` as `not_claimed`; this slice only hardens the
`C_BAD_SUBSTREAMID` event-record layout.
