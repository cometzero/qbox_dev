# QBox SMMUv3 AGBPA unsupported-RES0 verification (2026-05-11)

## Scope

`SMMU-COMP-020/030/080 AGBPA unsupported-RES0 slice`.

This slice grounds QBox behavior for the SMMUv3 alternate global bypass
attribute registers:

- `SMMU_AGBPA` at Page 0 offset `0x0048`.
- `SMMU_S_AGBPA` at Secure Page 0 offset `0x8048`.

The Arm SMMUv3 reference permits `SMMU_(S_)AGBPA` to be RES0 when the
implementation-defined alternate bypass attribute/tag field is unsupported.  QBox
now models that policy explicitly instead of leaving the architected register
slot ambiguous.

## Implementation evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - Adds `SMMUV3_AGBPA = 0x048`.
  - Adds `ARCH_AGBPA_UNSUPPORTED_RES0`.
  - Reads `SMMU_AGBPA` and `SMMU_S_AGBPA` as zero.
  - Ignores writes to both AGBPA registers.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Adds `AgbpaUnsupportedRegistersAreRes0`, covering Non-secure and Secure
    AGBPA write-ignore/read-zero behavior while proving adjacent GBPA remains
    writable.
- `scripts/check_qbox_smmuv3_compliance.py`
  - Adds `tbu:agbpa-unsupported-res0`.
- `scripts/check_buildroot_arm64_lane.sh`
  - Adds greps for the AGBPA register slot, RES0 policy, and component test.

## Verification commands

```sh
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j4
./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests \
  --gtest_filter='*AgbpaUnsupportedRegistersAreRes0:*GlobalBypassUsesGbpaOutputAttributes:*GlobalBypassGbpaAbortSuppressesEvent'
ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure
python3 scripts/check_qbox_smmuv3_compliance.py \
  --json build/verification/smmu-agbpa-res0-static-20260511.json
./scripts/check_buildroot_arm64_lane.sh
bash -n scripts/*.sh
python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py
git diff --check && git -C sources/qbox diff --check
```

## Expected no-overclaim boundary

This slice only claims explicit unsupported-RES0 behavior for the
implementation-defined AGBPA register fields.  It does not implement a vendor
alternate bypass tag, packet-level PCIe ATS/PRI ordering, DPT, upstream Linux
`arm-smmu-v3` lifecycle parity, or complete Realm/RME/GPT/GPC policy.

## Observed results

- `build/verification/smmu-agbpa-res0-build-20260511.log`
  - `[100%] Built target apollo-smmu-tbu-tests`
- `build/verification/smmu-agbpa-res0-gtest-20260511.log`
  - `[  PASSED  ] 3 tests.`
- `build/verification/smmu-agbpa-res0-ctest-20260511.log`
  - `100% tests passed, 0 tests failed out of 1`
- `build/verification/smmu-agbpa-res0-static-20260511.json`
  - `SUMMARY {"pass": 977}`
  - `tbu:agbpa-unsupported-res0` is `pass`
  - `full_smmuv3_compliance` remains `not_claimed`
- `build/verification/smmu-agbpa-res0-lane-20260511.log`
  - Buildroot ARM64 lane passed, including the AGBPA register/policy/test greps.
- `build/verification/smmu-agbpa-res0-bash-syntax-20260511.log`
  - `bash -n scripts/*.sh` passed.
- `build/verification/smmu-agbpa-res0-pycompile-20260511.log`
  - `python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py` passed.
- `build/verification/smmu-agbpa-res0-diff-check-20260511.log`
  - `git diff --check` and `git -C sources/qbox diff --check` passed.
