# QBox SMMUv3 SMMU-COMP-030 verification report

- Date: 2026-05-10
- Scope: `/build/qbox_dev`
- Story: stream/context descriptor decode functional slice
- Source plan: `doc/analysis/qbox-smmuv3-compliance-gap-plan-2026-05-10.md`
- Checklist: `doc/spec/qbox-smmuv3-compliance-checklist.md`

## Result

SMMU-COMP-030 remains `functional-slice`, but the slice was expanded beyond the
single Apollo Linux probe StreamID path.

Implemented in QBox:

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - Adds `REG_ARCH_STREAM_ID` so component and future guest tests can select the
    StreamID used by the architected probe path without changing the existing
    compatibility map StreamID.
  - Decodes architected `STRTAB_BASE_CFG` fields for bounded linear and two-level
    stream table lookup.
  - Fetches a two-level STRTAB L1 descriptor and selects the L2 STE by StreamID
    split/index.
  - Accepts spec-bitfield stage-1 STE/CD pointers (`STE.Config=S1_TRANS`,
    `STE.S1ContextPtr`, `CD.V`, `CD.TTB0`) while preserving the legacy Apollo
    Linux smoke-test descriptor encoding.
  - Adds `ARCH_FAULT_BAD_STREAM_ID` for out-of-range StreamID probes.
  - Tags descriptor-walk ATS/protocol/fault accounting with the selected
    architectural StreamID.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Adds `ArchitectedLinearStreamTableUsesSelectedStreamId`.
  - Adds `ArchitectedTwoLevelStreamTableSelectsL2Ste`.

This is not full ARM SMMUv3 stream/context descriptor compliance. PASID/SSID,
`S1DSS`, `S1CDMax`, two-level CD tables, stage-2/nested STE fields, descriptor
full Arm reserved-matrix parity and command-driven STRTAB/CD invalidation remain open; modeled STE/CD reserved/illegal checks are covered by the follow-up reserved-encoding report.

## Verification evidence

### Component unit regression

Command:

```sh
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)"
ctest --test-dir sources/qbox/build -R '^apollo-smmu-tbu-tests$' --output-on-failure
```

Evidence:

- `build/verification/apollo-smmuv3-strtab-streamid-ctest-20260510.log`

Observed result:

- Target build reached `Built target apollo-smmu-tbu-tests`.
- CTest reached `100% tests passed, 0 tests failed out of 1`.
- New tests verify:
  - selected StreamID `0x3` indexes a bounded linear STRTAB and populates the
    ATS cache under SID `0x3`;
  - StreamID `0x8` against LOG2SIZE `3` reports `ARCH_FAULT_BAD_STREAM_ID`;
  - selected StreamID `0x15` indexes a two-level STRTAB L1/L2 path and fetches
    the expected L2 STE.

### Platform build regression

Command:

```sh
./scripts/build_qbox_buildroot_platform.sh
```

Evidence:

- `build/verification/qbox-platform-smmu-comp-030-strtab-streamid-20260510.log`

Observed result:

- Build reached `QBox Buildroot platform runtime built in /build/qbox_dev/sources/qbox/build`.

### Guest IREE smoke regression

Command:

```sh
QBOX_HEXAGON_GUEST_SMOKE_STAMP=20260510-smmu-comp-030-strtab-streamid \
QBOX_BOOT_TIMEOUT=180 \
QBOX_IREE_LOGIN_DELAY=24 \
QBOX_IREE_AFTER_COMMAND_DELAY=25 \
./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh
```

Evidence:

- `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-comp-030-strtab-streamid.driver.log`
- `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-comp-030-strtab-streamid.log`
- `build/verification/qbox-iree-tiny-cnn-hexagon-guest-boot-20260510-smmu-comp-030-strtab-streamid.log`

Observed result:

- Driver reached `PASS: QBox guest IREE Hexagon tiny-CNN output matched`.
- Expected tensor matched: `1x1x2x2xf32=[[[54 63][90 99]]]`.
- Runtime log retains the existing Linux probe markers:
  - `SMMUv3 stream/context descriptor probe ok stream-id=0x1`
  - `SMMUv3 negative fault replay ok`
  - `SMMUv3 architected queue register selftest ok`

## Remaining blockers

- Guest Linux still stages the legacy compact STE/CD encoding; component tests
  now cover spec-bitfield S1 descriptors, but guest spec-bitfield STRTAB/CD
  staging is future work.
- No PASID/SSID or two-level CD table selection exists yet.
- No stage-2 or nested STE/CD decode exists yet.
- CMDQ `CFGI_*`/TLBI invalidation does not yet drive full STRTAB/CD cache state.
- Full invalid/reserved descriptor negative replay matrix remains open.
