# QBox SMMUv3 Secure IDR3 SAMS/RES0 verification

- Date: 2026-05-11
- Scope: `SMMU-COMP-020/060 Secure IDR3 SAMS/RES0 slice`
- Target: `/build/qbox_dev`
- Ground truth: Arm SMMUv3 IHI0070G.b `SMMU_S_IDR3` field definition: bit 6 `SAMS`, all other bits RES0.

## Implemented behavior

The Apollo TBU Secure register bank now exposes `SMMU_S_IDR3` as a Secure-only
ID register instead of mirroring Non-secure `SMMU_IDR3`:

- `ARCH_S_IDR3_SAMS` names the architected Secure ATS Maintenance Support bit.
- `ARCH_S_IDR3 == 0`, meaning Secure `CMD_ATC_INV`/`CMD_PRI_RESP` are supported
  consistently with the modeled Secure command slices and `SAMS` is not set.
- Secure reads of offset `SMMUV3_IDR3` return `ARCH_S_IDR3`.
- Non-secure `SMMU_IDR3` still advertises the modeled MPAM/RIL bits.

This is a register-bank correction.  It does not expand the Secure command model
beyond the already-tested CFGI/TLBI/ATC/PRI response slices.

## Verification evidence

| Command | Log | Result |
| --- | --- | --- |
| `cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j4` | `build/verification/smmu-secure-idr3-sams-res0-build-20260511.log` | `Built target apollo-smmu-tbu-tests` |
| `./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests --gtest_filter='*SecureRegisterBankConfiguresStrtabCmdqAndEventq:*SecureCmdqSsecCfgiTargetsSelectedSecurityState:*SecureCmdqSsecTlbiAtcTargetsSelectedSecurityState*'` | `build/verification/smmu-secure-idr3-sams-res0-gtest-20260511.log` | `[  PASSED  ] 3 tests.` |
| `ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure` | `build/verification/smmu-secure-idr3-sams-res0-ctest-20260511.log` | `100% tests passed` |
| `python3 scripts/check_qbox_smmuv3_compliance.py --json build/verification/smmu-secure-idr3-sams-res0-static-20260511.json` | `build/verification/smmu-secure-idr3-sams-res0-static-20260511.log` / `.json` | `SUMMARY {"pass": 1028}` and `tbu:secure-idr3-sams-res0` passed; full compliance remains `not_claimed` |
| `./scripts/check_buildroot_arm64_lane.sh` | `build/verification/smmu-secure-idr3-sams-res0-lane-20260511.log` | `Lane conclusion:` present and new Secure IDR3 greps passed |
| `bash -n scripts/*.sh` | `build/verification/smmu-secure-idr3-sams-res0-bash-syntax-20260511.log` | exit 0, empty log |
| `python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py` | `build/verification/smmu-secure-idr3-sams-res0-pycompile-20260511.log` | exit 0, empty log |
| `{ git diff --check; git -C sources/qbox diff --check; git -C sources/linux diff --check; }` | `build/verification/smmu-secure-idr3-sams-res0-diff-check-20260511.log` | exit 0, empty log |

## No-overclaim boundary

Full ARM SMMUv3 compliance remains `not_claimed`.  This slice only corrects the
Secure IDR3 discovery surface; full Secure command lifecycle ordering, complete
ATS/PRI packet protocol, upstream Linux `arm-smmu-v3` parity, ECMDQ, DPT, and
RME/GPT/GPC remain open.
