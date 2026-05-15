# QBox SMMUv3 Secure IDR0 MSI/stall/RES0 verification

- Date: 2026-05-11
- Scope: `SMMU-COMP-020/070 Secure IDR0 MSI/stall/RES0 slice`
- Target: `/build/qbox_dev`
- Ground truth: Arm SMMUv3 IHI0070G.b `SMMU_S_IDR0` field definition: bit 31
  `ECMDQ`, bits [25:24] `STALL_MODEL`, bit 13 `MSI`, and all other bits RES0.

## Implemented behavior

The Apollo TBU Secure register bank now exposes `SMMU_S_IDR0` as a Secure-only
ID register instead of mirroring Non-secure `SMMU_IDR0` capability bits:

- `ARCH_S_IDR0_MSI` advertises the already-modeled Secure EVENTQ/GERROR MSI
  bank behavior.
- `ARCH_S_IDR0_STALL_MODEL_TERMINATE_ONLY` keeps the Secure discovery surface
  aligned with the current terminate-only advertised model.
- `ARCH_S_IDR0_ECMDQ` remains clear, consistent with the existing Secure ECMDQ
  unsupported RES0/WI control-page policy.
- Secure reads of offset `SMMUV3_IDR0` return `ARCH_S_IDR0`; Non-secure reads
  still return the broader `ARCH_IDR0` stage/ATS/PRI/MSI discovery surface.
- `SecureRegisterBankConfiguresStrtabCmdqAndEventq` now verifies the Secure
  `SMMU_S_IDR0` MSI/stall/ECMDQ fields and that unrelated bits are RES0.

This is a Secure register-bank discovery correction.  It does not add ECMDQ or a
new stall model.

## Verification evidence

| Command | Log | Result |
| --- | --- | --- |
| `cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j4` | `build/verification/smmu-secure-idr0-msi-stall-res0-build-20260511.log` | `Built target apollo-smmu-tbu-tests` |
| `./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests --gtest_filter='*SecureRegisterBankConfiguresStrtabCmdqAndEventq:*SecureEventqMsiAndAbortUseSecureBank:*SecureGerrorMsiAndAbortUseSecureBank*'` | `build/verification/smmu-secure-idr0-msi-stall-res0-gtest-20260511.log` | `[  PASSED  ] 3 tests.` |
| `ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure` | `build/verification/smmu-secure-idr0-msi-stall-res0-ctest-20260511.log` | `100% tests passed` |
| `python3 scripts/check_qbox_smmuv3_compliance.py --json build/verification/smmu-secure-idr0-msi-stall-res0-static-20260511.json` | `build/verification/smmu-secure-idr0-msi-stall-res0-static-20260511.log` / `.json` | `SUMMARY {"pass": 1038}` and `tbu:secure-idr0-msi-stall-res0` passed; full compliance remains `not_claimed` |
| `./scripts/check_buildroot_arm64_lane.sh` | `build/verification/smmu-secure-idr0-msi-stall-res0-lane-20260511.log` | `Lane conclusion:` present and new Secure IDR0 greps passed |
| `bash -n scripts/*.sh` | `build/verification/smmu-secure-idr0-msi-stall-res0-bash-syntax-20260511.log` | exit 0, empty log |
| `python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py` | `build/verification/smmu-secure-idr0-msi-stall-res0-pycompile-20260511.log` | exit 0, empty log |
| `{ git diff --check; git -C sources/qbox diff --check; git -C sources/linux diff --check; }` | `build/verification/smmu-secure-idr0-msi-stall-res0-diff-check-20260511.log` | exit 0, empty log |

## No-overclaim boundary

Full ARM SMMUv3 compliance remains `not_claimed`.  This slice only corrects the
Secure IDR0 discovery surface; full Secure command lifecycle ordering, complete
ATS/PRI packet protocol, upstream Linux `arm-smmu-v3` parity, ECMDQ, DPT, and
RME/GPT/GPC remain open.
