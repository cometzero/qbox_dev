# QBox SMMUv3 ATS Translated priority verification - 2026-05-11

SMMU-COMP-050/060 ATS Translated priority functional slice.

## Scope

This slice verifies a narrow, component-tested subset of the ATS Translated
transaction priority ordering for `CR0.SMMUEN==1` and `CR0.ATSCHK==1`:

- `C_BAD_STREAMID` is reported before an effective-EATS forbidden result.
- `C_BAD_STE` is reported before `F_TRANSL_FORBIDDEN`.
- `F_TRANSL_FORBIDDEN` is reported only after a valid STE is found and its
  effective `STE.EATS` disables the Translated transaction.

It does **not** claim the complete SMMUv3 priority list, Secure/Realm priority
cases, `F_VMS_FETCH`, TLB/config conflict priority, GPC ordering, split-stage
DPT ordering, or event merging behavior.

## Ground truth

- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md:2211`:
  ATS Translated events with `SMMUEN==1` and `ATSCHK==1` have architected
  reporting priority.
- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md:2190`:
  configuration errors are checked for Translated transactions only when
  `ATSCHK==1`.

## Implemented QBox behavior

- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Adds `AtsTranslatedPriorityChecksConfigBeforeForbidden`.
  - Verifies `C_BAD_STREAMID`, `C_BAD_STE`, and `F_TRANSL_FORBIDDEN` are emitted
    in the expected order for three focused Translated transaction vectors.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh`
  - Add durable static/lane guards for this priority slice.

## Verification commands and evidence

```sh
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)" \
  2>&1 | tee build/verification/apollo-smmu-tbu-ats-translated-priority-build-20260511.log
ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure \
  2>&1 | tee build/verification/apollo-smmu-tbu-ats-translated-priority-ctest-20260511.log
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
    --json build/verification/qbox-smmuv3-compliance-ats-translated-priority-final-20260511.json
  ./scripts/check_buildroot_arm64_lane.sh
  git diff --check
  git -C sources/qbox diff --check
  git -C sources/linux diff --check
} 2>&1 | tee build/verification/smmu-ats-translated-priority-static-final-20260511.log
rm -rf scripts/__pycache__
```

Observed result:

- Build log: `build/verification/apollo-smmu-tbu-ats-translated-priority-build-20260511.log`
  - `Built target apollo_smmu_tbu`
  - `Built target apollo-smmu-tbu-tests`
- CTest log: `build/verification/apollo-smmu-tbu-ats-translated-priority-ctest-20260511.log`
  - `100% tests passed, 0 tests failed out of 1`
- Static/lane log: `build/verification/smmu-ats-translated-priority-static-final-20260511.log`
  - `PASS  tbu:ats-translated-priority-config-before-forbidden`
  - `PASS: QBox Apollo SMMU TBU ATS Translated priority component test present`
  - `SUMMARY {"pass": 431}`
- JSON checker output:
  `build/verification/qbox-smmuv3-compliance-ats-translated-priority-final-20260511.json`
  - `summary.pass = 431`
  - `classification.full_smmuv3_compliance = not_claimed`

## Current limitation

This is a partial priority test only. Full ATS Translated priority compliance
still requires the full event matrix, Secure/Realm routing, DPT and GPC cases,
conflict detection, and upstream recovery-order parity.
