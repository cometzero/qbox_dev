# QBox SMMUv3 IDR0 stage/TTF/CD2L discovery verification

- Date: 2026-05-11
- Scope: `SMMU-COMP-020/030/040 IDR0 S1P/TTF/CD2L discovery slice`
- Target: `/build/qbox_dev`
- Ground truth: Arm SMMUv3 IHI0070G.b `SMMU_IDR0` fields for `S1P`, `S2P`, `TTF`, `CD2L`, and `ST_LEVEL`.

## Implemented behavior

The Apollo TBU now advertises IDR0 fields that match the already-modeled
translation pipeline:

- `SMMU_IDR0.S1P` and `S2P` are both set, matching the stage-1, stage-2, and
  nested translation paths covered by component tests.
- `SMMU_IDR0.TTF` reports AArch64/VMSAv8-64 translation tables, matching the
  modeled 64-bit descriptor walker.
- `SMMU_IDR0.CD2L` is set, matching the bounded 64K L2 context-descriptor table
  indexing model.
- `SMMU_IDR0.ST_LEVEL` remains the two-level Stream Table setting introduced for
  the IDR1 StreamID-size alignment.
- The Apollo Linux selftest constant now expects `APOLLO_SMMUV3_ARCH_IDR0 ==
  0x098db70b`.

This is a discovery-register alignment slice.  It does not add a new walker; it
advertises only the modeled stage/format/CD-table behavior already present in
bounded component coverage.

## Verification evidence

| Command | Log | Result |
| --- | --- | --- |
| `cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j4` | `build/verification/smmu-idr0-stage-ttf-cd2l-build-20260511.log` | `Built target apollo-smmu-tbu-tests` |
| `./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests --gtest_filter='*ArchitectedRegisterMmioSurface:*ArchitectedWalkerGranuleBlockAndFaultMatrix:*ArchitectedContextDescriptorTableIndexesSelectedSsid*'` | `build/verification/smmu-idr0-stage-ttf-cd2l-gtest-20260511.log` | `[  PASSED  ] 3 tests.` |
| `ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure` | `build/verification/smmu-idr0-stage-ttf-cd2l-ctest-20260511.log` | `100% tests passed` |
| `python3 scripts/check_qbox_smmuv3_compliance.py --json build/verification/smmu-idr0-stage-ttf-cd2l-static-20260511.json` | `build/verification/smmu-idr0-stage-ttf-cd2l-static-20260511.log` / `.json` | `SUMMARY {"pass": 1018}` and `tbu:idr0-stage-ttf-cd2l-discovery` passed; full compliance remains `not_claimed` |
| `./scripts/check_buildroot_arm64_lane.sh` | `build/verification/smmu-idr0-stage-ttf-cd2l-lane-20260511.log` | `Lane conclusion:` present and new IDR0 greps passed |
| `bash -n scripts/*.sh` | `build/verification/smmu-idr0-stage-ttf-cd2l-bash-syntax-20260511.log` | exit 0, empty log |
| `python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py` | `build/verification/smmu-idr0-stage-ttf-cd2l-pycompile-20260511.log` | exit 0, empty log |
| `{ git diff --check; git -C sources/qbox diff --check; git -C sources/linux diff --check; }` | `build/verification/smmu-idr0-stage-ttf-cd2l-diff-check-20260511.log` | exit 0, empty log |

## No-overclaim boundary

Full ARM SMMUv3 compliance remains `not_claimed`.  This slice only aligns IDR0
stage/format/CD-table discovery with existing bounded behavior; full descriptor
matrix parity, upstream Linux `arm-smmu-v3` lifecycle parity, VMSAv8-32 support,
ECMDQ, DPT, and complete RME/GPT/GPC remain open.
