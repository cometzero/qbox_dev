# QBox SMMUv3 IDR4 implementation-defined zero verification

- Date: 2026-05-11
- Scope: `SMMU-COMP-020 IDR4 implementation-defined zero slice`
- Target: `/build/qbox_dev`
- Ground truth: Arm SMMUv3 IHI0070G.b register map exposes `SMMU_IDR4` at
  offset `0x0010`; `SMMU_IDR4` and `SMMU_S_IDR4` are implementation-defined
  read-only discovery registers.

## Implemented behavior

The Apollo TBU now exposes IDR4 explicitly in both Non-secure and Secure
register banks instead of leaving the Page 0 slot implicit:

- `SMMUV3_IDR4 == 0x010`, preserving the architected Page 0 sequence
  `IDR0..IDR5`, `IIDR`, and `AIDR`.
- `ARCH_IDR4 == 0` documents the QBox implementation-defined Non-secure policy.
- `ARCH_S_IDR4 == 0` documents the QBox implementation-defined Secure policy.
- Non-secure reads of `SMMU_IDR4` return `ARCH_IDR4`; Secure reads of the same
  Secure-page offset return `ARCH_S_IDR4`.
- Component tests cover both banks through the existing architected register
  surface and Secure register-bank tests.

This is a register-map/discovery correction only.  It intentionally does not
advertise implementation-defined capabilities through IDR4.

## Verification evidence

| Command | Log | Result |
| --- | --- | --- |
| `cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j4` | `build/verification/smmu-idr4-implementation-defined-zero-build-20260511.log` | `Built target apollo-smmu-tbu-tests` |
| `./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests --gtest_filter='*ArchitectedRegisterMmioSurface:*SecureRegisterBankConfiguresStrtabCmdqAndEventq*'` | `build/verification/smmu-idr4-implementation-defined-zero-gtest-20260511.log` | `[  PASSED  ] 2 tests.` |
| `ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure` | `build/verification/smmu-idr4-implementation-defined-zero-ctest-20260511.log` | `100% tests passed` |
| `python3 scripts/check_qbox_smmuv3_compliance.py --json build/verification/smmu-idr4-implementation-defined-zero-static-20260511.json` | `build/verification/smmu-idr4-implementation-defined-zero-static-20260511.log` / `.json` | `SUMMARY {"pass": 1033}` and `tbu:idr4-implementation-defined-zero` passed; full compliance remains `not_claimed` |
| `./scripts/check_buildroot_arm64_lane.sh` | `build/verification/smmu-idr4-implementation-defined-zero-lane-20260511.log` | `Lane conclusion:` present and new IDR4 greps passed |
| `bash -n scripts/*.sh` | `build/verification/smmu-idr4-implementation-defined-zero-bash-syntax-20260511.log` | exit 0, empty log |
| `python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py` | `build/verification/smmu-idr4-implementation-defined-zero-pycompile-20260511.log` | exit 0, empty log |
| `{ git diff --check; git -C sources/qbox diff --check; git -C sources/linux diff --check; }` | `build/verification/smmu-idr4-implementation-defined-zero-diff-check-20260511.log` | exit 0, empty log |

## No-overclaim boundary

Full ARM SMMUv3 compliance remains `not_claimed`.  This slice only makes the
implementation-defined IDR4 slots explicit and testable; full upstream Linux
`arm-smmu-v3` lifecycle parity, ECMDQ, DPT, complete ATS/PRI packet protocol,
and complete RME/GPT/GPC remain open.
