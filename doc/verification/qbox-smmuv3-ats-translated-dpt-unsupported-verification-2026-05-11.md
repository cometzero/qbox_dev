# QBox SMMUv3 ATS Translated DPT unsupported verification - 2026-05-11

SMMU-COMP-050/060 ATS Translated DPT unsupported functional slice.

## Scope

This slice verifies ATS Translated transaction handling when `CR0.ATSCHK==1`
and `STE.EATS==0b11` selects Device Permission Table behavior. QBox does not yet
model DPT lookup state, so it rejects the traffic deterministically:

- the access terminates with an address error,
- private status reports `ARCH_FAULT_TRANSL_FORBIDDEN`,
- one `F_TRANSL_FORBIDDEN` EVENTQ record is pushed,
- `m_arch_last_eats` preserves the decoded `ARCH_STE_EATS_DPT` value.

This does not claim real DPT table walks, `DPT_WALK_EN`, Secure/Realm DPT
variants, GPC ordering, or complete packet-level ATS protocol.

## Ground truth

- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md:2235`:
  `STE.EATS==0b11` DPT checks can report `F_TRANSL_FORBIDDEN` in the ATS
  Translated priority list.
- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md:2244`:
  Realm DPT behavior records `F_TRANSL_FORBIDDEN` for disabled or failed DPT
  lookup/check cases.
- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md:2265`:
  Non-secure DPT behavior records `F_TRANSL_FORBIDDEN` for disabled or failed
  DPT lookup/check cases.

## Implemented QBox behavior

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - Adds `arch_translated_dpt_supported()` and
    `arch_translated_eats_unsupported_by_dpt()` for the current no-DPT model.
  - Records `ARCH_FAULT_TRANSL_FORBIDDEN` and `F_TRANSL_FORBIDDEN` for
    `ATS translated DPT unsupported`.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Adds `AtsTranslatedDptUnsupportedRecordsForbidden`.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh`
  - Add durable static/lane guards for this slice.

## Verification commands and evidence

```sh
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)" \
  2>&1 | tee build/verification/apollo-smmu-tbu-ats-translated-dpt-unsupported-build-20260511.log
ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure \
  2>&1 | tee build/verification/apollo-smmu-tbu-ats-translated-dpt-unsupported-ctest-20260511.log
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
    --json build/verification/qbox-smmuv3-compliance-ats-translated-dpt-unsupported-final-20260511.json
  ./scripts/check_buildroot_arm64_lane.sh
  git diff --check
  git -C sources/qbox diff --check
  git -C sources/linux diff --check
} 2>&1 | tee build/verification/smmu-ats-translated-dpt-unsupported-static-final-20260511.log
rm -rf scripts/__pycache__
```

Observed result:

- `build/verification/apollo-smmu-tbu-ats-translated-dpt-unsupported-build-20260511.log`
  - `Built target apollo_smmu_tbu`
  - `Built target apollo-smmu-tbu-tests`
- `build/verification/apollo-smmu-tbu-ats-translated-dpt-unsupported-ctest-20260511.log`
  - `100% tests passed, 0 tests failed out of 1`
- `build/verification/smmu-ats-translated-dpt-unsupported-static-final-20260511.log`
  - `PASS  tbu:ats-translated-dpt-unsupported`
  - `PASS: QBox Apollo SMMU TBU ATS Translated DPT unsupported component test present`
  - `SUMMARY {"pass": 443}`
- `build/verification/qbox-smmuv3-compliance-ats-translated-dpt-unsupported-final-20260511.json`
  - `summary.pass = 443`
  - `classification.full_smmuv3_compliance = not_claimed`

## Current limitation

This is a narrow no-DPT-model rejection slice. Full compliance still requires
real DPT tables, DPT-disabled register reporting, Secure/Realm DPT variants,
GPC ordering, and upstream recovery parity.
