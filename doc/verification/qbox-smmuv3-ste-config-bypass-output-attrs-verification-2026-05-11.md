# QBox SMMUv3 STE.Config all-bypass output-attribute propagation

Date: 2026-05-11

## Scope

SMMU-COMP-030/080 STE.Config all-bypass output-attribute propagation.

This follow-up slice closes the BUG-QA-11 gap for QBox's modeled
`STE.Config==0b100` all-bypass path. The pinned `sources/smmu` reference requires
STE output attributes (`MTCFG/MemAttr`, `ALLOCCFG`, `SHCFG`, `NSCFG`, `PRIVCFG`,
and `INSTCFG`) to be applied when a stream returns a bypass result. The previous
slice covered S1DSS context-bypass; this slice adds the direct STE.Config
all-bypass identity path.

## Implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - Added `ARCH_STE_CFG_BYPASS` as the modeled all-bypass encoding while keeping
    the existing compatibility alias used by ATS Translated rejection tests.
  - Added `arch_ste_all_bypass()` and an `architectural STE.Config all-bypass`
    path in `arch_stream_context_walk()`.
  - The path returns identity PA, fills ATS cache state for the modeled page, and
    calls `record_arch_ste_output_attrs(..., "ste-config-bypass")` before
    downstream transport.
- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_arch_core.h`
  - Added the core `STE_CFG_BYPASS` name and uses it in supported-config and
    effective-EATS decisions.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Added `SteConfigBypassOutputAttributesPropagate`, validating identity
    access plus `MTCFG/MemAttr`, `SHCFG`, `ALLOCCFG`, `INSTCFG`, `PRIVCFG`, and
    `NSCFG` propagation. The test also checks the device/nC `MTCFG=1 &&
    MemAttr=0` shareability override to OSH.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh`
  - Added static/lane gates for the STE.Config all-bypass helper, log marker,
    and component test.

## Verification

| Command | Evidence |
| --- | --- |
| `cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j2` | `build/verification/smmu-ste-config-bypass-output-attrs-build-20260511.log` |
| `sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests --gtest_filter='*SteConfigBypassOutputAttributesPropagate*:*SteBypassOutputAttributesPropagateOnContextBypass*'` | `build/verification/smmu-ste-config-bypass-output-attrs-gtest-20260511.log` |
| `ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure` | `build/verification/smmu-ste-config-bypass-output-attrs-ctest-20260511.log` |
| static checker replay | `build/verification/smmu-ste-config-bypass-output-attrs-static-20260511.log` |
| lane checker | `build/verification/smmu-ste-config-bypass-output-attrs-lane-20260511.log` |
| final closure replay | `build/verification/smmu-ste-config-bypass-output-attrs-final-closure-check-20260511.log` |

## Results

- Targeted build: PASS, `Built target apollo-smmu-tbu-tests` in
  `build/verification/smmu-ste-config-bypass-output-attrs-build-20260511.log`.
- Focused gTest: PASS, `[  PASSED  ] 2 tests` in
  `build/verification/smmu-ste-config-bypass-output-attrs-gtest-20260511.log`;
  the trace includes `path=ste-config-bypass` and
  `architectural STE.Config all-bypass`.
- Full component CTest: PASS, `100% tests passed, 0 tests failed out of 1` in
  `build/verification/smmu-ste-config-bypass-output-attrs-ctest-20260511.log`.
- Static replay: PASS, `SUMMARY {"pass": 778}` with
  `full_smmuv3_compliance=not_claimed` in
  `build/verification/smmu-ste-config-bypass-output-attrs-static-20260511.log`.
- Buildroot lane: PASS, lane conclusion recorded in
  `build/verification/smmu-ste-config-bypass-output-attrs-lane-20260511.log`.
- Final closure replay: PASS, `PASS: final STE.Config bypass output-attribute
  closure checks completed` in
  `build/verification/smmu-ste-config-bypass-output-attrs-final-closure-check-20260511.log`.

## Remaining blockers

This closes modeled output attributes for QBox context-bypass and direct
STE.Config all-bypass transactions. The ATS Translated follow-up is tracked in
`doc/verification/qbox-smmuv3-ats-translated-output-attrs-verification-2026-05-11.md`.
GATOS/ATOS return-path output attributes, packet-level PCIe attributes, full
PCIe/RID topology, and upstream `arm-smmu-v3` lifecycle parity remain open.
