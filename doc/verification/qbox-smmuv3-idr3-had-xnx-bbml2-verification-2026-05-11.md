# QBox SMMUv3 IDR3 HAD/XNX/BBML2 verification

- Date: 2026-05-11
- Scope: `SMMU-COMP-020/040/050/060 IDR3 HAD/XNX/BBML2 behavior slice`
- Target: `/build/qbox_dev`
- Ground truth: Arm SMMUv3 IHI0070G.b defines `SMMU_IDR3.HAD` as mandatory
  from SMMUv3.1 when stage 1 is supported, `SMMU_IDR3.XNX` as mandatory from
  SMMUv3.1 when stage 2 is supported, and BBML level 2 as the Secure EL2
  requirement used by this QBox SMMUv3.3 discovery surface.

## Implemented behavior

- `ARCH_IDR3` now reports mandatory `HAD`, `XNX`, and `BBML==Level 2` while
  retaining the previously modeled `MPAM`, `FWB`, `STT`, `RIL`, `E0PD`, and
  `PTWNNC` bits and keeping `DPT` clear.
- `CD.HAD0` and `CD.HAD1` are decoded from CD word 1/2 and accepted by the
  reserved-bit validator.  For the modeled stage-1 walker, `CD.HAD0` disables
  hierarchical table-descriptor APTable/UXNTable/PXNTable enforcement on the
  TTB0 path.
- The stage-2 walker now checks the modeled XNX execute-never bits for
  instruction transactions: unprivileged execute requests fault on `UXN`, and
  privileged execute requests fault on `PXN`.
- The Apollo Linux probe's expected IDR3 value is updated to `0x00007794` so
  guest-visible discovery matches the SystemC model.

## Verification evidence

| Command | Log | Result |
| --- | --- | --- |
| `cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j4` | `build/verification/smmu-idr3-had-xnx-bbml2-build-20260511.log` | PASS: `[100%] Built target apollo-smmu-tbu-tests` |
| `./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests --gtest_filter='*CdHadDisablesHierarchicalStage1Attrs:*Idr3XnxBlocksUnprivilegedStage2Execute:*ArchitectedRegisterMmioSurface:*MpamDiscoveryAdvertisesVmsPrerequisites*'` | `build/verification/smmu-idr3-had-xnx-bbml2-gtest-20260511.log` | PASS: `[  PASSED  ] 4 tests.` |
| `ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure` | `build/verification/smmu-idr3-had-xnx-bbml2-ctest-20260511.log` | PASS: `100% tests passed, 0 tests failed out of 1` |
| `python3 scripts/check_qbox_smmuv3_compliance.py --json build/verification/smmu-idr3-had-xnx-bbml2-static-20260511.json` | `build/verification/smmu-idr3-had-xnx-bbml2-static-20260511.log` / `.json` | PASS: `SUMMARY {"pass": 1051}`, `full_smmuv3_compliance=not_claimed` |
| `./scripts/check_buildroot_arm64_lane.sh` | `build/verification/smmu-idr3-had-xnx-bbml2-lane-20260511.log` | PASS: lane concluded Buildroot rootfs/DTB ownership and SMMUv3 HAD/XNX/BBML2 contracts present |
| `bash -n scripts/*.sh` | `build/verification/smmu-idr3-had-xnx-bbml2-bash-syntax-20260511.log` | PASS: command exited 0 with no diagnostics |
| `python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py` | `build/verification/smmu-idr3-had-xnx-bbml2-pycompile-20260511.log` | PASS: command exited 0 with no diagnostics |
| `{ git diff --check; git -C sources/qbox diff --check; git -C sources/linux diff --check; }` | `build/verification/smmu-idr3-had-xnx-bbml2-diff-check-20260511.log` | PASS: command exited 0 with no diagnostics |

## No-overclaim boundary

Full ARM SMMUv3 compliance remains `not_claimed`.  This slice covers discovery
coherence and bounded HAD/XNX behavior in the existing QBox walker.  It does not
implement complete table-descriptor hierarchical attribute parity across all
translation regimes, full HTTU, complete BBML reference-vector parity, DPT,
ECMDQ, RME/GPT/GPC, or upstream Linux `arm-smmu-v3` lifecycle parity.
