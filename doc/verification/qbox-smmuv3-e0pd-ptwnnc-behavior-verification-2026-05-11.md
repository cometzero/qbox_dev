# QBox SMMUv3 E0PD/PTWNNC behavior verification

- Date: 2026-05-11
- Scope: `SMMU-COMP-040/050/060 E0PD/PTWNNC behavior slice`
- Target: `/build/qbox_dev`
- Ground truth: Arm SMMUv3 IHI0070G.b requires SMMUv3.3 implementations that
  advertise `SMMU_IDR3.E0PD` and `SMMU_IDR3.PTWNNC` to block unprivileged
  `CD.E0PD{0,1}` stage-1 accesses with an `F_TRANSLATION` fault and to treat
  stage-1 CD/translation-table fetches mapped as Device by stage 2 as Normal
  Non-cacheable when `PTWNNC` is set and `STE.S2PTW` is clear.

## Implemented behavior

- `ARCH_CD_E0PD0` and `ARCH_CD_E0PD1` are decoded from CD word 1/2 and accepted
  by the reserved-bit validator now that `IDR3.E0PD` is advertised.
- Unprivileged stage-1 accesses through the selected TTB half are rejected before
  the stage-1 descriptor walk when the matching `CD.E0PDx` bit is set. The model
  records a stage-1 translation fault and preserves privileged-access success.
- Nested stage-1 descriptor fetches that are stage-2-translated through
  Device-mapped stage-2 descriptors are detected and marked as `PTWNNC`
  Normal-Non-cacheable normalization instead of being rejected.

## Verification evidence

| Command | Log | Result |
| --- | --- | --- |
| `cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j4` | `build/verification/smmu-e0pd-ptwnnc-behavior-build-20260511.log` | PASS: `[100%] Built target apollo-smmu-tbu-tests` |
| `./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests --gtest_filter='*CdE0pdBlocksUnprivilegedTtb0Access:*PtwnncNormalizesNestedStage1FetchDeviceMemory*'` | `build/verification/smmu-e0pd-ptwnnc-behavior-gtest-20260511.log` | PASS: `[  PASSED  ] 2 tests.` |
| `ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure` | `build/verification/smmu-e0pd-ptwnnc-behavior-ctest-20260511.log` | PASS: `100% tests passed, 0 tests failed out of 1` |
| `python3 scripts/check_qbox_smmuv3_compliance.py --json build/verification/smmu-e0pd-ptwnnc-behavior-static-20260511.json` | `build/verification/smmu-e0pd-ptwnnc-behavior-static-20260511.log` / `.json` | PASS: `tbu:e0pd-ptwnnc-behavior` and `SUMMARY {"pass": 1050}`; `full_smmuv3_compliance=not_claimed` |
| `./scripts/check_buildroot_arm64_lane.sh` | `build/verification/smmu-e0pd-ptwnnc-behavior-lane-20260511.log` | PASS: lane contract plus E0PD/PTWNNC greps passed |
| `bash -n scripts/*.sh` | `build/verification/smmu-e0pd-ptwnnc-behavior-bash-syntax-20260511.log` | PASS: exit 0, no diagnostics |
| `python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py` | `build/verification/smmu-e0pd-ptwnnc-behavior-pycompile-20260511.log` | PASS: exit 0, no diagnostics |
| `{ git diff --check; git -C sources/qbox diff --check; git -C sources/linux diff --check; }` | `build/verification/smmu-e0pd-ptwnnc-behavior-diff-check-20260511.log` | PASS: exit 0, no whitespace diagnostics |

## No-overclaim boundary

Full ARM SMMUv3 compliance remains `not_claimed`. This slice covers bounded
E0PD and PTWNNC behavior for the existing CD/stage-1/nested walker model. It does
not implement complete TTB1 translation-table selection, `STE.S2PTW` permission
fault behavior, DPT, ECMDQ, RME/GPT/GPC, or upstream Linux `arm-smmu-v3` lifecycle
parity.
