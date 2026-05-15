# QBox SMMUv3 IDR0 ASID16/VMID16 discovery verification

- Date: 2026-05-11
- Scope: `SMMU-COMP-020/040/060 IDR0 ASID16/VMID16 discovery slice`
- Target: `/build/qbox_dev`
- Ground truth: Arm SMMUv3 IHI0070G.b `SMMU_IDR0.ASID16` and `SMMU_IDR0.VMID16` field definitions.

## Implemented behavior

The Apollo TBU now advertises ASID16 and VMID16 because the modeled descriptor,
TLBI, and ATS-cache tag paths already carry 16-bit values:

- `SMMU_IDR0.ASID16` is set; `ARCH_CD_ASID_MASK` and command decoding keep the
  16-bit ASID field.
- `SMMU_IDR0.VMID16` is set; `ARCH_STE_S2VMID_MASK` and command decoding keep
  the 16-bit VMID field.
- `CmdqTaggedInvalidationHonorsAsidVmidAndSsid` now uses high-bit ASID/VMID
  values to prove the upper byte participates in matching and invalidation.
- The Apollo Linux selftest constant now expects `APOLLO_SMMUV3_ARCH_IDR0 ==
  0x098db70b`.

This is a discovery and regression-strengthening slice.  It does not add a new
TLBI model; it advertises the 16-bit tag width already represented by the model.

## Verification evidence

| Command | Log | Result |
| --- | --- | --- |
| `cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j4` | `build/verification/smmu-idr0-asid16-vmid16-build-20260511.log` | `Built target apollo-smmu-tbu-tests` |
| `./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests --gtest_filter='*ArchitectedRegisterMmioSurface:*CmdqTaggedInvalidationHonorsAsidVmidAndSsid*'` | `build/verification/smmu-idr0-asid16-vmid16-gtest-20260511.log` | `[  PASSED  ] 2 tests.` |
| `ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure` | `build/verification/smmu-idr0-asid16-vmid16-ctest-20260511.log` | `100% tests passed` |
| `python3 scripts/check_qbox_smmuv3_compliance.py --json build/verification/smmu-idr0-asid16-vmid16-static-20260511.json` | `build/verification/smmu-idr0-asid16-vmid16-static-20260511.log` / `.json` | `SUMMARY {"pass": 1023}` and `tbu:idr0-asid16-vmid16-discovery` passed; full compliance remains `not_claimed` |
| `./scripts/check_buildroot_arm64_lane.sh` | `build/verification/smmu-idr0-asid16-vmid16-lane-20260511.log` | `Lane conclusion:` present and new ASID16/VMID16 greps passed |
| `bash -n scripts/*.sh` | `build/verification/smmu-idr0-asid16-vmid16-bash-syntax-20260511.log` | exit 0, empty log |
| `python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py` | `build/verification/smmu-idr0-asid16-vmid16-pycompile-20260511.log` | exit 0, empty log |
| `{ git diff --check; git -C sources/qbox diff --check; git -C sources/linux diff --check; }` | `build/verification/smmu-idr0-asid16-vmid16-diff-check-20260511.log` | exit 0, empty log |

## No-overclaim boundary

Full ARM SMMUv3 compliance remains `not_claimed`.  This slice only advertises
and tests the 16-bit ASID/VMID tags already modeled; exhaustive TLBI regime and
security-state parity, full upstream Linux lifecycle parity, ECMDQ, DPT, and
complete ATS/PRI packet protocol remain open.
