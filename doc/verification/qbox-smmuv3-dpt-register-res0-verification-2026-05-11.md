# QBox SMMUv3 DPT unsupported-register RES0 verification (2026-05-11)

## Scope

`SMMU-COMP-020/050/060 DPT unsupported-register RES0 slice`.

QBox currently advertises `SMMU_IDR3.DPT == 0`, so Device Permission Table
walking is not implemented.  The pinned SMMUv3 reference makes
`SMMU_DPT_BASE`, `SMMU_DPT_BASE_CFG`, and `SMMU_DPT_CFG_FAR` conditional on DPT
support.  This slice makes the unsupported register policy explicit by exposing
those DPT registers as RES0/write-ignored in the Apollo TBU register model.

## Implementation evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - Adds `SMMUV3_DPT_BASE_LO/HI`, `SMMUV3_DPT_BASE_CFG`, and
    `SMMUV3_DPT_CFG_FAR_LO/HI` register offsets.
  - Adds `ARCH_DPT_UNSUPPORTED_RES0`.
  - Reads DPT registers as zero and ignores writes while `ARCH_IDR3_DPT` is not
    included in `ARCH_IDR3`.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Adds `DptUnsupportedRegistersAreRes0`, covering DPT discovery clear plus
    Non-secure and Secure register write-ignore/read-zero behavior.
- `scripts/check_qbox_smmuv3_compliance.py`
  - Adds `tbu:dpt-unsupported-registers-res0`.
- `scripts/check_buildroot_arm64_lane.sh`
  - Adds lane greps for DPT register slots, RES0 policy, and component test.

## Verification commands

```sh
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j4
./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests \
  --gtest_filter='*DptUnsupportedRegistersAreRes0:*DptiCommandsSetGerrorWhenDptUnsupported:*AtsTranslatedDptUnsupportedRecordsForbidden'
ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure
python3 scripts/check_qbox_smmuv3_compliance.py \
  --json build/verification/smmu-dpt-register-res0-static-20260511.json
./scripts/check_buildroot_arm64_lane.sh
bash -n scripts/*.sh
python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py
git diff --check && git -C sources/qbox diff --check
```

## Expected no-overclaim boundary

This slice only claims architecturally consistent behavior for unsupported DPT
registers while DPT is not advertised.  It does not implement a DPT descriptor
walker, DPT cache, DPT lookup faults, packet-level ATS/PRI ordering, upstream
Linux `arm-smmu-v3` lifecycle parity, or complete Realm/RME/GPT/GPC policy.

## Observed results

- `build/verification/smmu-dpt-register-res0-build-20260511.log`
  - `[100%] Built target apollo-smmu-tbu-tests`
- `build/verification/smmu-dpt-register-res0-gtest-20260511.log`
  - `[  PASSED  ] 3 tests.`
- `build/verification/smmu-dpt-register-res0-ctest-20260511.log`
  - `100% tests passed, 0 tests failed out of 1`
- `build/verification/smmu-dpt-register-res0-static-20260511.json`
  - `SUMMARY {"pass": 980}`
  - `tbu:dpt-unsupported-registers-res0` is `pass`
  - `full_smmuv3_compliance` remains `not_claimed`
- `build/verification/smmu-dpt-register-res0-lane-20260511.log`
  - Buildroot ARM64 lane passed, including the DPT register/policy/test greps.
- `build/verification/smmu-dpt-register-res0-bash-syntax-20260511.log`
  - `bash -n scripts/*.sh` passed.
- `build/verification/smmu-dpt-register-res0-pycompile-20260511.log`
  - `python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py` passed.
- `build/verification/smmu-dpt-register-res0-diff-check-20260511.log`
  - `git diff --check` and `git -C sources/qbox diff --check` passed.
