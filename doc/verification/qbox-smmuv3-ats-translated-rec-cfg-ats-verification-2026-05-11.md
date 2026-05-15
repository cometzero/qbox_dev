# QBox SMMUv3 ATS Translated REC_CFG_ATS verification - 2026-05-11

SMMU-COMP-050/060 ATS Translated REC_CFG_ATS functional slice.

## Scope

SMMU-COMP-050/060 ATS Translated configuration-fault reporting functional
slice.

This slice covers modeled ATS Translated transactions when `CR0.ATSCHK` is set
and the transaction encounters an SMMUv3 configuration fault before it can be
accepted. It verifies that configuration events are suppressed while
`CR2.REC_CFG_ATS` is clear and recorded when `CR2.REC_CFG_ATS` is set. It also
checks that ATS Translated `C_BAD_STREAMID` recording is not gated by
`CR2.RECINVSID`.

It does **not** claim full ATS/PRI compliance, Secure/Realm routing,
split-stage protocol-specific restrictions, DPT behavior, address-size checks
above the implemented PA size, or upstream Linux recovery parity.

## Ground truth

- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md:2171`:
  ATS Translated transactions generally pass through the SMMU unless one of the
  listed ATSCHK/configuration checks applies.
- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md:2190`:
  configuration errors observed for ATS Translated transactions are recorded
  only when `ATSCHK==1` and `SMMU_CR2.REC_CFG_ATS==1`; otherwise no event is
  recorded. The same note states that `C_BAD_STREAMID` reporting is not affected
  by `RECINVSID` for this path.
- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md:2208`:
  PASID/SSV ATS Translated configuration-structure errors are also controlled
  by `REC_CFG_ATS`.

## Implemented QBox behavior

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - Adds `arch_record_translated_config_fault()`.
  - Adds `record_or_suppress_arch_translated_config_fault()`.
  - Checks invalid STE contents before the ATS Translated EATS acceptance path.
  - Suppresses or records translated configuration faults according to
    `CR2.REC_CFG_ATS`.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Adds `AtsTranslatedConfigFaultsHonorCr2RecCfgAts`.
  - Verifies invalid STE suppression with `CR2.REC_CFG_ATS==0`.
  - Verifies invalid STE `C_BAD_STE` recording with `CR2.REC_CFG_ATS==1`.
  - Verifies invalid StreamID `C_BAD_STREAMID` recording with `REC_CFG_ATS==1`
    even when `RECINVSID==0`.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh`
  - Add durable static/lane guards for the ATS Translated `REC_CFG_ATS` slice.

## Verification commands and evidence

```sh
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)" \
  2>&1 | tee build/verification/apollo-smmu-tbu-ats-translated-rec-cfg-ats-build-20260511.log
ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure \
  2>&1 | tee build/verification/apollo-smmu-tbu-ats-translated-rec-cfg-ats-ctest-20260511.log
```

Final static/lane verification will be recorded in
`build/verification/smmu-ats-translated-rec-cfg-ats-static-final-20260511.log`
and the JSON checker output will be recorded in
`build/verification/qbox-smmuv3-compliance-ats-translated-rec-cfg-ats-final-20260511.json`.

Observed results:

- Build log:
  `build/verification/apollo-smmu-tbu-ats-translated-rec-cfg-ats-build-20260511.log`
  reports `Built target apollo_smmu_tbu` and
  `Built target apollo-smmu-tbu-tests`.
- CTest log:
  `build/verification/apollo-smmu-tbu-ats-translated-rec-cfg-ats-ctest-20260511.log`
  reports `100% tests passed, 0 tests failed out of 1`.
- Static checker JSON summary:
  `{"pass": 423}`.
- Static checker target:
  `tbu:ats-translated-rec-cfg-ats-gate` is `pass`.
- Lane guard:
  `build/verification/smmu-ats-translated-rec-cfg-ats-static-final-20260511.log`
  reports both ATS Translated `REC_CFG_ATS` guards as `PASS`.

## Current limitation

The aggregate compliance checker is expected to continue reporting
`full_smmuv3_compliance` as `not_claimed`; this slice narrows ATS Translated
configuration-fault reporting only.
