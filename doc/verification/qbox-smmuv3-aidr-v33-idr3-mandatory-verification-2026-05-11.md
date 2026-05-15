# QBox SMMUv3 AIDR v3.3 and IDR3 mandatory discovery verification

- Date: 2026-05-11
- Scope: `SMMU-COMP-020/040/060 AIDR v3.3 and IDR3 mandatory discovery slice`
- Target: `/build/qbox_dev`
- Ground truth: Arm SMMUv3 IHI0070G.b version/discovery rules: `SMMU_AIDR[7:0]`
  encodes the SMMUv3 minor revision; SMMUv3.2 introduces mandatory/required
  `IDR3.RIL`, `IDR3.FWB`, and `IDR3.BBML` discovery behavior plus Secure EL2
  optional discovery through `SMMU_S_IDR1.SEL2`; SMMUv3.3 introduces mandatory
  `IDR3.E0PD` and `IDR3.PTWNNC` when stage 2 is present, and optional
  `IDR0.ATSRECERR`.

## Implemented behavior

The Apollo TBU now reports an architecture revision that matches the bounded
feature surface already exposed by the model:

- `ARCH_AIDR == 0x00000003`, identifying SMMUv3.3 instead of SMMUv3.1.
- `ARCH_IDR3.FWB`, `STT`, `RIL`, and `BBML==Level 1` are advertised for the
  modeled SMMUv3.2 Secure EL2/RIL/MPAM/VMS-oriented slices.
- `ARCH_IDR3.E0PD` and `PTWNNC` are advertised to align the SMMUv3.3 AIDR value
  with mandatory v3.3 discovery when stage 2 is present.
- `ARCH_IDR3.DPT` remains clear; DPT registers and DPTI commands continue to use
  the existing unsupported RES0/CERROR policy.
- The Apollo Linux selftest constants now expect `IDR3=0x00004f80` and
  `AIDR=0x00000003`.

This is a discovery-alignment slice.  It does not claim complete E0PD, PTWNNC,
or all SMMUv3.3 behavioral parity beyond the already-modeled slices.

## Verification evidence

| Command | Log | Result |
| --- | --- | --- |
| `cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j4` | `build/verification/smmu-aidr-v33-idr3-mandatory-build-20260511.log` | PASS: `[100%] Built target apollo-smmu-tbu-tests` |
| `./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests --gtest_filter='*ArchitectedRegisterMmioSurface:*MpamDiscoveryAdvertisesVmsPrerequisites*'` | `build/verification/smmu-aidr-v33-idr3-mandatory-gtest-20260511.log` | PASS: `[  PASSED  ] 2 tests.` |
| `ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure` | `build/verification/smmu-aidr-v33-idr3-mandatory-ctest-20260511.log` | PASS: `100% tests passed, 0 tests failed out of 1` |
| `python3 scripts/check_qbox_smmuv3_compliance.py --json build/verification/smmu-aidr-v33-idr3-mandatory-static-20260511.json` | `build/verification/smmu-aidr-v33-idr3-mandatory-static-20260511.log` / `.json` | PASS: `SUMMARY {"pass": 1043}` and `tbu:aidr-v33-idr3-mandatory-discovery` passed; `full_smmuv3_compliance=not_claimed` |
| `./scripts/check_buildroot_arm64_lane.sh` | `build/verification/smmu-aidr-v33-idr3-mandatory-lane-20260511.log` | PASS: lane conclusion present and AIDR/IDR3 v3.3 greps passed |
| `bash -n scripts/*.sh` | `build/verification/smmu-aidr-v33-idr3-mandatory-bash-syntax-20260511.log` | PASS: exit 0, empty log |
| `python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py` | `build/verification/smmu-aidr-v33-idr3-mandatory-pycompile-20260511.log` | PASS: exit 0, empty log |
| `{ git diff --check; git -C sources/qbox diff --check; git -C sources/linux diff --check; }` | `build/verification/smmu-aidr-v33-idr3-mandatory-diff-check-20260511.log` | PASS: exit 0, empty log |

## No-overclaim boundary

Full ARM SMMUv3 compliance remains `not_claimed`.  This slice aligns the
reported architecture revision and mandatory discovery fields with already
advertised v3.2/v3.3 features; complete SMMUv3.3 E0PD/PTWNNC behavior, upstream
Linux `arm-smmu-v3` lifecycle parity, ECMDQ, DPT, complete ATS/PRI packet
protocol, and RME/GPT/GPC remain open.
