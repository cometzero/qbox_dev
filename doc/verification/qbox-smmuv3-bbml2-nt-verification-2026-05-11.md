# QBox SMMUv3 BBML level-2 nT verification

- Date: 2026-05-11
- Scope: `SMMU-COMP-040/050 BBML level-2 nT block descriptor slice`
- Target: `/build/qbox_dev`
- Ground truth: Arm SMMUv3 IHI0070G.b section 3.21.1.3 states that when
  `SMMU_IDR3.BBML == 2`, the implementation ignores the Block descriptor `nT`
  bit and automatically resolves TLB multi-hit scenarios, so `F_TLB_CONFLICT`
  is never reported for this BBML level.

## Implemented behavior

- `ARCH_DESC_NT`/`WALKER_DESC_NT` explicitly name descriptor bit 16 for Block
  descriptors.
- The architected core tags block-leaf descriptor steps with `block_nt` without
  treating `nT` as output-address bits.
- The Apollo TBU records `m_arch_last_bbml2_nt_ignored` and logs
  `IDR3.BBML level-2 ignores block descriptor nT` when the advertised BBML
  level-2 surface sees a Block descriptor with `nT==1`.
- The behavior remains intentionally scoped: it proves the advertised BBML
  level-2 `nT` ignore/no-conflict rule for the modeled walker, not a complete
  BBM reference-vector suite.

## Verification evidence

| Command | Log | Result |
| --- | --- | --- |
| `cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j4` | `build/verification/smmu-bbml2-nt-build-20260511.log` | PASS: `[100%] Built target apollo-smmu-tbu-tests` |
| `./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests --gtest_filter='*Idr3Bbml2IgnoresBlockNt:*ArchitectedRegisterMmioSurface*'` | `build/verification/smmu-bbml2-nt-gtest-20260511.log` | PASS: `[  PASSED  ] 2 tests.` |
| `ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure` | `build/verification/smmu-bbml2-nt-ctest-20260511.log` | PASS: `100% tests passed, 0 tests failed out of 1` |
| `python3 scripts/check_qbox_smmuv3_compliance.py --json build/verification/smmu-bbml2-nt-static-20260511.json` | `build/verification/smmu-bbml2-nt-static-20260511.log` / `.json` | PASS: `SUMMARY {"pass": 1052}`, `full_smmuv3_compliance=not_claimed` |
| `./scripts/check_buildroot_arm64_lane.sh` | `build/verification/smmu-bbml2-nt-lane-20260511.log` | PASS: lane found BBML level-2 nT source and component-test contracts |
| `bash -n scripts/*.sh` | `build/verification/smmu-bbml2-nt-bash-syntax-20260511.log` | PASS: command exited 0 with no diagnostics |
| `python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py` | `build/verification/smmu-bbml2-nt-pycompile-20260511.log` | PASS: command exited 0 with no diagnostics |
| `{ git diff --check; git -C sources/qbox diff --check; git -C sources/linux diff --check; }` | `build/verification/smmu-bbml2-nt-diff-check-20260511.log` | PASS: command exited 0 with no diagnostics |

## No-overclaim boundary

Full ARM SMMUv3 compliance remains `not_claimed`. This slice covers the bounded
BBML level-2 `nT` rule for Block descriptors and does not implement complete
BBM transition/reference-vector parity, full TLB multi-hit detection geometry,
HTTU, DPT, ECMDQ, RME/GPT/GPC, or upstream Linux `arm-smmu-v3` lifecycle parity.
