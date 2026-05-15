# QBox SMMUv3 ATS Translated SMMUEN/ATSCHK verification - 2026-05-11

SMMU-COMP-050/060 ATS Translated SMMUEN/ATSCHK functional slice.

## Scope

This slice verifies two architected ATS Translated transaction gates from the
local SMMUv3 reference corpus:

- `CR0.SMMUEN==0`: Translated traffic is aborted and reported as
  `F_TRANSL_FORBIDDEN` when Event queue recording is enabled.
- `CR0.SMMUEN==1` and `CR0.ATSCHK==0`: Translated traffic is accepted without
  checking Stream table/configuration structures, so an otherwise invalid
  StreamID does not produce `C_BAD_STREAMID`.

The QBox model still uses its simulation memory map to route the accepted access
into the test memory target; this report does not claim packet-level PCIe ATS
bypass, implemented-PA-size checks, split-stage `EATS==0b10`, DPT, or
Secure/Realm behavior.

## Ground truth

- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md:2081`:
  `ATSCHK` controls whether Translated traffic bypasses further checks or is
  checked against `STE.EATS`.
- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md:2179`:
  `SMMUEN==0` leads to `F_TRANSL_FORBIDDEN` and abort for Translated traffic.
- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md:2190`:
  with `ATSCHK==0`, the SMMU does not check configuration for Translated
  transactions and therefore does not detect those configuration errors.

## Implemented QBox behavior

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - Calls `allow_arch_translated_transaction()` for every Translated access.
  - Records `F_TRANSL_FORBIDDEN` for SMMU-disabled Translated traffic with
    `EVENTQEN` set.
  - Bypasses configuration lookup while `ATSCHK` is disabled.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Adds `AtsTranslatedTransactionsHonorSmmuenAndAtschk` to verify both paths.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh`
  - Add durable static/lane guards for this functional slice.

## Verification commands and evidence

```sh
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)" \
  2>&1 | tee build/verification/apollo-smmu-tbu-ats-translated-smmuen-atschk-build-20260511.log
ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure \
  2>&1 | tee build/verification/apollo-smmu-tbu-ats-translated-smmuen-atschk-ctest-20260511.log
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
    --json build/verification/qbox-smmuv3-compliance-ats-translated-smmuen-atschk-final-20260511.json
  ./scripts/check_buildroot_arm64_lane.sh
  git diff --check
  git -C sources/qbox diff --check
  git -C sources/linux diff --check
} 2>&1 | tee build/verification/smmu-ats-translated-smmuen-atschk-static-final-20260511.log
rm -rf scripts/__pycache__
```

Observed result:

- Build log: `build/verification/apollo-smmu-tbu-ats-translated-smmuen-atschk-build-20260511.log`
  - `Built target apollo_smmu_tbu`
  - `Built target apollo-smmu-tbu-tests`
- CTest log: `build/verification/apollo-smmu-tbu-ats-translated-smmuen-atschk-ctest-20260511.log`
  - `100% tests passed, 0 tests failed out of 1`
- Static/lane log: `build/verification/smmu-ats-translated-smmuen-atschk-static-final-20260511.log`
  - `PASS  tbu:ats-translated-smmuen-atschk-gates`
  - `PASS: QBox Apollo SMMU TBU ATS Translated SMMUEN/ATSCHK component test present`
  - `SUMMARY {"pass": 428}`
- JSON checker output:
  `build/verification/qbox-smmuv3-compliance-ats-translated-smmuen-atschk-final-20260511.json`
  - `summary.pass = 428`
  - `classification.full_smmuv3_compliance = not_claimed`

## Current limitation

This is an ATS Translated gate slice only. Full compliance still requires the
remaining event-priority matrix, address-size behavior above the implemented PA
size, split-stage/DPT behavior, Secure/Realm routing, and upstream recovery
parity.
