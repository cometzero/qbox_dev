# QBox SMMUv3 GATOS_PAR output-attribute verification

- Date: 2026-05-11
- Scope: SMMU-COMP-030/080 GATOS_PAR STE output-attribute return path
- Reference: `sources/smmu/cpp/src/smmu/smmu.cpp` implements
  `gatosTranslate()` as a GATOS/ATOS-style translation wrapper that returns a
  64-bit PAR with `ATTR`, `SH`, translated PA, and fault `FAULTCODE/REASON`.

## Implementation summary

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - Adds `ARCH_CTRL_GATOS_TRANSLATE` and `REG_ARCH_PAR_LO/HI` for a bounded
    compatibility-register GATOS_PAR command.
  - Reuses the existing architectural stream/context descriptor walker and STE
    output-attribute state to form success PAR `ATTR[63:56]`, `SH[9:8]`, and
    `PA[55:12]` fields.
  - Maps modeled walker faults to GATOS_PAR `FAULTCODE[11:4]`, stage-2
    `REASON[2:1]`, and `FADDR[55:12]` where the current QBox fault state has
    the required information.
  - Returns `FAULTCODE=0xfd` for disabled SMMU GATOS requests and
    `FAULTCODE=0xfe` for modeled invalid-stage bypass/disabled results.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Adds `GatosParReportsSteOutputAttributes`, proving that a successful
    stage-1 walk returns STE-derived `ATTR`/`SH` in GATOS_PAR.
  - Adds `GatosParFaultCodeForUnmappedPage`, proving that a translation fault
    returns `FAULT=1`, `FAULTCODE=0x10`, and `REASON=0`.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh`
  - Add static/lane gates for the GATOS_PAR command, registers, logs, and
    focused component vectors.

## Verification commands

| Command | Log |
| --- | --- |
| `cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j2` | `build/verification/smmu-gatos-par-output-attrs-build-20260511.log` |
| `sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests --gtest_filter='*GatosParReportsSteOutputAttributes*:*GatosParFaultCodeForUnmappedPage*'` | `build/verification/smmu-gatos-par-output-attrs-gtest-20260511.log` |
| `ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure` | `build/verification/smmu-gatos-par-output-attrs-ctest-20260511.log` |
| static checker replay | `build/verification/smmu-gatos-par-output-attrs-static-20260511.log` |
| lane checker | `build/verification/smmu-gatos-par-output-attrs-lane-20260511.log` |
| final closure replay | `build/verification/smmu-gatos-par-output-attrs-final-closure-check-20260511.log` |

## Result

- Build: PASS, `[100%] Built target apollo-smmu-tbu-tests` in
  `build/verification/smmu-gatos-par-output-attrs-build-20260511.log`.
- Focused gTest: PASS, `2 tests` passed in
  `build/verification/smmu-gatos-par-output-attrs-gtest-20260511.log`; the
  trace includes `architectural GATOS translation` and
  `architectural GATOS fault PAR`.
- Full component CTest: PASS, `100% tests passed, 0 tests failed out of 1` in
  `build/verification/smmu-gatos-par-output-attrs-ctest-20260511.log`.
- Static replay: PASS, `SUMMARY {"pass": 798}` with
  `full_smmuv3_compliance=not_claimed` in
  `build/verification/smmu-gatos-par-output-attrs-static-20260511.log`.
- Buildroot lane: PASS, lane conclusion recorded in
  `build/verification/smmu-gatos-par-output-attrs-lane-20260511.log`.

This slice covers a bounded QBox compatibility-register GATOS_PAR model. Full
architected ATOS/VATOS register parity, complete PCIe packet-level attribute
semantics, and upstream `arm-smmu-v3` lifecycle parity remain out of scope, so
full ARM SMMUv3 compliance remains not claimed.
