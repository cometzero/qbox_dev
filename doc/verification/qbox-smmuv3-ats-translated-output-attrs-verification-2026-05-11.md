# QBox SMMUv3 ATS Translated output-attribute verification

- Date: 2026-05-11
- Scope: SMMU-COMP-030/080 ATS Translated STE output-attribute propagation
- Reference: `sources/smmu/cpp/src/stream_context/stream_context.cpp` applies STE
  output attributes to normal, bypass, and cached translation results through its
  `applyOutputAttrs` path.

## Implementation summary

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - Preserves output-attribute state across the ATS Translated configuration
    check and the downstream translated payload routing path.
  - Records STE output attributes on successful ATS Translated checks with the
    `ats-translated` path marker.
  - Records STE output attributes on successful stage-1, stage-2, and nested
    translation results before downstream TLM transport.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Adds `AtsTranslatedSteOutputAttributesPropagateWhenAtschkEnabled`, which
    validates `MTCFG/MemAttr`, `SHCFG`, `ALLOCCFG`, `INSTCFG`, `PRIVCFG`, and
    `NSCFG` on the downstream TLM extension for an ATS Translated payload.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh`
  - Add static/lane gates for the ATS Translated output-attribute path and test.

## Verification commands

| Command | Log |
| --- | --- |
| `cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j2` | `build/verification/smmu-ats-translated-output-attrs-build-20260511.log` |
| `sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests --gtest_filter='*AtsTranslatedSteOutputAttributesPropagateWhenAtschkEnabled*:*SteConfigBypassOutputAttributesPropagate*'` | `build/verification/smmu-ats-translated-output-attrs-gtest-20260511.log` |
| `ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure` | `build/verification/smmu-ats-translated-output-attrs-ctest-20260511.log` |
| static checker replay | `build/verification/smmu-ats-translated-output-attrs-static-20260511.log` |
| lane checker | `build/verification/smmu-ats-translated-output-attrs-lane-20260511.log` |
| final closure replay | `build/verification/smmu-ats-translated-output-attrs-final-closure-check-20260511.log` |

## Result

- Build: PASS, `[100%] Built target apollo-smmu-tbu-tests` in
  `build/verification/smmu-ats-translated-output-attrs-build-20260511.log`.
- Focused gTest: PASS, `2 tests` passed in
  `build/verification/smmu-ats-translated-output-attrs-gtest-20260511.log`;
  the trace includes `path=ats-translated` and `STE output attributes`.
- Full component CTest: PASS, `100% tests passed, 0 tests failed out of 1` in
  `build/verification/smmu-ats-translated-output-attrs-ctest-20260511.log`.
- Static replay: PASS, `SUMMARY {"pass": 785}` with
  `full_smmuv3_compliance=not_claimed` in
  `build/verification/smmu-ats-translated-output-attrs-static-20260511.log`.
- Buildroot lane: PASS, lane conclusion recorded in
  `build/verification/smmu-ats-translated-output-attrs-lane-20260511.log`.

This slice covers the modeled ATS Translated TLM payload path plus ordinary
stage-1/stage-2/nested translation result propagation in QBox. GATOS/ATOS
register return-path modeling and packet-level PCIe attribute parity remain out
of scope for this slice, so full ARM SMMUv3 compliance remains not claimed.
