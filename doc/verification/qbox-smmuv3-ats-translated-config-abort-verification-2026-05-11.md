# QBox SMMUv3 ATS Translated STE.Config abort verification - 2026-05-11

SMMU-COMP-050/060 ATS Translated STE.Config abort functional slice.

## Scope

This slice verifies ATS Translated transaction handling for a valid STE using
`STE.Config==0b100` while `CR0.ATSCHK==1`. QBox models the architected behavior
as a direct Translated-transaction rejection:

- the access terminates with an address error,
- private status reports `ARCH_FAULT_TRANSL_FORBIDDEN`,
- one `F_TRANSL_FORBIDDEN` EVENTQ record is pushed,
- the STE is not treated as a generic reserved/illegal `C_BAD_STE` case.

This does not claim the full ATS Translated priority matrix, Secure/Realm
variants, DPT/GPC behavior, or upstream Linux recovery parity.

## Ground truth

- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md:2181`:
  `STE.Config==0b000` is aborted when `ATSCHK==1`.
- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md:2182`:
  `STE.Config==0b100` is aborted with `F_TRANSL_FORBIDDEN` when `ATSCHK==1`.
- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md:2211`:
  ATS Translated events have an explicit priority order while `SMMUEN==1` and
  `ATSCHK==1`.

## Implemented QBox behavior

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - Adds `ARCH_STE_CFG_ABORT` for `STE.Config==0b100`.
  - Keeps the encoding modeled so ATS Translated handling can distinguish it
    from illegal/reserved STE encodings.
  - Records `ARCH_FAULT_TRANSL_FORBIDDEN` and `F_TRANSL_FORBIDDEN` for
    `ATS translated STE.Config abort`.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Adds `AtsTranslatedConfigAbortRecordsForbidden`.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh`
  - Add durable static/lane guards for this slice.

## Verification commands and evidence

```sh
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)" \
  2>&1 | tee build/verification/apollo-smmu-tbu-ats-translated-config-abort-build-20260511.log
ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure \
  2>&1 | tee build/verification/apollo-smmu-tbu-ats-translated-config-abort-ctest-20260511.log
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
    --json build/verification/qbox-smmuv3-compliance-ats-translated-config-abort-final-20260511.json
  ./scripts/check_buildroot_arm64_lane.sh
  git diff --check
  git -C sources/qbox diff --check
  git -C sources/linux diff --check
} 2>&1 | tee build/verification/smmu-ats-translated-config-abort-static-final-20260511.log
rm -rf scripts/__pycache__
```

Observed result:

- `build/verification/apollo-smmu-tbu-ats-translated-config-abort-build-20260511.log`
  - `Built target apollo_smmu_tbu`
  - `Built target apollo-smmu-tbu-tests`
- `build/verification/apollo-smmu-tbu-ats-translated-config-abort-ctest-20260511.log`
  - `100% tests passed, 0 tests failed out of 1`
- `build/verification/smmu-ats-translated-config-abort-static-final-20260511.log`
  - `PASS  tbu:ats-translated-config-abort-forbidden`
  - `PASS: QBox Apollo SMMU TBU ATS Translated STE.Config abort component test present`
  - `SUMMARY {"pass": 440}`
- `build/verification/qbox-smmuv3-compliance-ats-translated-config-abort-final-20260511.json`
  - `summary.pass = 440`
  - `classification.full_smmuv3_compliance = not_claimed`

## Current limitation

This is a narrow ATS Translated `STE.Config==0b100` event slice. Full compliance
still requires complete priority ordering, Secure/Realm variants, DPT/GPC
checks, and upstream recovery parity.
