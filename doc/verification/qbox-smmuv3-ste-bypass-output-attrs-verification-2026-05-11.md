# QBox SMMUv3 STE bypass output-attribute propagation

Date: 2026-05-11

## Scope

SMMU-COMP-030/080 STE bypass output-attribute propagation.

This is a focused reference-backed slice for `sources/smmu/bugs/newBugs24Mar2026_7pm.md`
BUG-QA-11. The pinned reference requires STE output attributes
`MTCFG/MemAttr`, `ALLOCCFG`, `SHCFG`, `NSCFG`, `PRIVCFG`, and `INSTCFG` to be
applied even when the stream takes a bypass result. QBox currently models the
bypass path through the S1DSS no-SSID context-descriptor bypass path rather than
claiming full STE.Config all-bypass parity.

## Implementation

- `sources/qbox/systemc-components/common/include/tlm-extensions/apollo-smmu-stream-id.h`
  - Added output-attribute fields to the SMMU TLM extension so translated/bypass
    payloads can carry modeled STE output attributes downstream.
- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - Added modeled STE output-attribute bit decoders for `MTCFG`, `MEMATTR`,
    `SHCFG`, `ALLOCCFG`, `PRIVCFG`, `INSTCFG`, and existing `NSCFG`.
  - Added `record_arch_ste_output_attrs()` and
    `populate_arch_output_attrs_extension()`.
  - Applied the modeled STE output attributes on the context-descriptor bypass
    path and propagated them on downstream TLM payloads.
  - Modeled the reference behavior that `MTCFG=1 && MemAttr==0` forces OSH
    shareability for device/nC memory.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Added `SteBypassOutputAttributesPropagateOnContextBypass`, validating
    `MTCFG/MemAttr`, `SHCFG`, `ALLOCCFG`, `INSTCFG`, `PRIVCFG`, `NSCFG`, and the
    `MTCFG=0 => memType=0` rule.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh`
  - Added static/lane gates for the output-attribute helpers, extension fields,
    and component test.

## Verification

| Command | Evidence |
| --- | --- |
| `cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j2` | `build/verification/smmu-ste-bypass-output-attrs-build-20260511.log` |
| `sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests --gtest_filter='*SteBypassOutputAttributesPropagateOnContextBypass*:*SteS2sRejectedWhenStallModelTerminateOnly*'` | `build/verification/smmu-ste-bypass-output-attrs-gtest-20260511.log` |
| `ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure` | `build/verification/smmu-ste-bypass-output-attrs-ctest-20260511.log` |
| static checker replay | `build/verification/smmu-ste-bypass-output-attrs-static-20260511.log` |
| lane checker | `build/verification/smmu-ste-bypass-output-attrs-lane-20260511.log` |
| final closure replay | `build/verification/smmu-ste-bypass-output-attrs-final-closure-check-20260511.log` |

## Results

- Targeted build: PASS, `Built target apollo-smmu-tbu-tests` in
  `build/verification/smmu-ste-bypass-output-attrs-build-20260511.log`.
- Focused gTest: PASS, `[  PASSED  ] 2 tests` in
  `build/verification/smmu-ste-bypass-output-attrs-gtest-20260511.log`; the
  trace shows `mem-type=0xf` for `MTCFG=1` and `mem-type=0x0` for `MTCFG=0`.
- Full component CTest: PASS, `100% tests passed, 0 tests failed out of 1` in
  `build/verification/smmu-ste-bypass-output-attrs-ctest-20260511.log`.
- Static replay: PASS, `SUMMARY {"pass": 769}` with
  `full_smmuv3_compliance=not_claimed` in
  `build/verification/smmu-ste-bypass-output-attrs-static-20260511.log`.
- Buildroot lane: PASS, lane conclusion recorded in
  `build/verification/smmu-ste-bypass-output-attrs-lane-20260511.log`.
- Final closure replay: PASS, `PASS: final STE bypass output-attribute closure
  checks completed` in
  `build/verification/smmu-ste-bypass-output-attrs-final-closure-check-20260511.log`.

## Remaining blockers

This report covers the original context-bypass slice. The direct STE.Config
all-bypass follow-up is recorded in
`doc/verification/qbox-smmuv3-ste-config-bypass-output-attrs-verification-2026-05-11.md`.
The ATS Translated follow-up is recorded in
`doc/verification/qbox-smmuv3-ats-translated-output-attrs-verification-2026-05-11.md`.
GATOS/ATOS return-path output attributes, packet-level PCIe attributes, and
upstream `arm-smmu-v3` lifecycle parity remain open.
