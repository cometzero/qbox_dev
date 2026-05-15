# QBox SMMUv3 ATS Translated F_TRANSL_FORBIDDEN verification

- Date: 2026-05-11
- Scope: SMMU-COMP-050/060 ATS Translated F_TRANSL_FORBIDDEN functional slice
- Repository: `/build/qbox_dev`

## Result

PASS for this functional slice. The final checker report stays conservative:
`full_smmuv3_compliance=not_claimed`.

## Ground truth

- `sources/smmu/TASKS_CPP_OPERATION.md` §3.9.1.3 records that an ATS
  Translated transaction with `SMMU_CR0.ATSCHK==1` and forbidden state, including
  effective `STE.EATS==0b00`, aborts and records `F_TRANSL_FORBIDDEN`.
- `sources/smmu/wiki/synthesis/smmu-pcie-ats-integration.md` describes AT=0b10
  Translated transactions and the `STE.EATS`/`ATSCHK` dispatch model.

## Implemented scope

- `ApolloSmmuStreamIdExtension` now carries a default-off `translated` sideband
  for modeled endpoint ATS Translated transactions.
- `apollo_smmu_tbu` checks that sideband when `CR0.ATSCHK` is enabled, reads the
  modeled STE, rejects effective `STE.EATS==DISABLED`, and records
  `ARCH_EVENT_F_TRANSL_FORBIDDEN` through `ARCH_FAULT_TRANSL_FORBIDDEN`.
- `AtsTranslatedTransactionForbiddenRecordsEvent` verifies rejection and event
  recording, then verifies `EATS=FULL` permits the translated endpoint access to
  continue through the existing dynamic map path.

## Validation commands and evidence

```bash
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)" \
  2>&1 | tee build/verification/apollo-smmu-tbu-ats-translated-forbidden-build-20260511.log
ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure \
  2>&1 | tee build/verification/apollo-smmu-tbu-ats-translated-forbidden-ctest-20260511.log
{
  bash -n scripts/*.sh
  python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py \
    scripts/check_iree_cnn_pipeline_readiness.py scripts/qbox_pty_runner.py
  scripts/check_qbox_smmuv3_compliance.py --self-test-negative \
    --json build/verification/qbox-smmuv3-compliance-ats-translated-forbidden-final-20260511.json
  ./scripts/check_buildroot_arm64_lane.sh
  git diff --check
  git -C sources/qbox diff --check
  git -C sources/linux diff --check
} 2>&1 | tee build/verification/smmu-ats-translated-forbidden-static-final-20260511.log
```

Evidence:

- `build/verification/apollo-smmu-tbu-ats-translated-forbidden-build-20260511.log`
  - `Built target apollo_smmu_tbu`
  - `Built target apollo-smmu-tbu-tests`
- `build/verification/apollo-smmu-tbu-ats-translated-forbidden-ctest-20260511.log`
  - `100% tests passed, 0 tests failed out of 1`
- `build/verification/smmu-ats-translated-forbidden-static-final-20260511.log`
  - `PASS  tbu:ats-translated-forbidden-event`
  - `SUMMARY {"pass": 394}`
  - `Lane conclusion: Buildroot owns rootfs/DTB generation only; Linux Image comes from sources/linux, and libqemu comes from sources/qemu.`
- `build/verification/qbox-smmuv3-compliance-ats-translated-forbidden-final-20260511.json`
  - `summary = {"pass": 394}`
  - `classification.full_smmuv3_compliance = not_claimed`

## Remaining blockers

This is not full ATS Translated transaction compliance. It does not yet model
Secure-state routing, split-stage EATS=0b10 IPA-to-PA behavior, DPT/GPC
interactions, PASIDTT priority details, F_UUT no-event behavior, all translated
transaction priority ordering, CXL attributes, or upstream Linux recovery parity.
