# QBox SMMUv3 IIDR/AIDR register-slot verification

- Date: 2026-05-11
- Scope: `SMMU-COMP-020 IIDR/AIDR register-slot correction slice`
- Target: `/build/qbox_dev`
- Ground truth: Arm SMMUv3 IHI0070G.b register formats for `SMMU_IIDR` at offset `0x0018` and `SMMU_AIDR` at offset `0x001C`.

## Implemented behavior

The Apollo TBU register aperture now exposes the implementation ID and
architecture ID at their architected Page 0 slots:

- `SMMU_IIDR` is assigned to offset `0x0018` and returns the model's
  implementation-defined `ARCH_IIDR` value.
- `SMMU_AIDR` is assigned to offset `0x001C` and returns `ARCH_AIDR`.
- The existing `ArchitectedRegisterMmioSurface` component test now verifies that
  the `0x0018` IIDR slot no longer aliases the AIDR value.

This is a register-map correction only.  It does not claim a new SMMUv3 revision
or implement additional architecture-version features beyond those already
advertised elsewhere.

## Verification evidence

| Command | Log | Result |
| --- | --- | --- |
| `cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j4` | `build/verification/smmu-iidr-aidr-register-slots-build-20260511.log` | `Built target apollo-smmu-tbu-tests` |
| `./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests --gtest_filter='*ArchitectedRegisterMmioSurface*'` | `build/verification/smmu-iidr-aidr-register-slots-gtest-20260511.log` | `[  PASSED  ] 1 test.` |
| `ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure` | `build/verification/smmu-iidr-aidr-register-slots-ctest-20260511.log` | `100% tests passed` |

| `python3 scripts/check_qbox_smmuv3_compliance.py --json build/verification/smmu-iidr-aidr-register-slots-static-20260511.json` | `build/verification/smmu-iidr-aidr-register-slots-static-20260511.log` / `.json` | `SUMMARY {"pass": 998}` and `tbu:iidr-aidr-register-slots` passed; full compliance remains `not_claimed` |
| `./scripts/check_buildroot_arm64_lane.sh` | `build/verification/smmu-iidr-aidr-register-slots-lane-20260511.log` | `Lane conclusion:` present and new IIDR/AIDR greps passed |
| `bash -n scripts/*.sh` | `build/verification/smmu-iidr-aidr-register-slots-bash-syntax-20260511.log` | exit 0, empty log |
| `python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py` | `build/verification/smmu-iidr-aidr-register-slots-pycompile-20260511.log` | exit 0, empty log |
| `{ git diff --check; git -C sources/qbox diff --check; }` | `build/verification/smmu-iidr-aidr-register-slots-diff-check-20260511.log` | exit 0, empty log |

## No-overclaim boundary

Full ARM SMMUv3 compliance remains `not_claimed`.  Correct IIDR/AIDR placement
only fixes the architected discovery aperture; it does not close remaining
stream/context descriptor parity, packet-level ATS/PRI/ECMDQ protocol, DPT,
RME/GPT/GPC, or upstream driver lifecycle gaps.
