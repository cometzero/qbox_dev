# QBox SMMUv3 HTTU AF/Dirty verification

- Date: 2026-05-11
- Scope: `SMMU-COMP-040/050/060 HTTU AF/Dirty leaf-update slice`
- Target: `/build/qbox_dev`
- Ground truth: Arm SMMUv3 IHI0070G.b defines `SMMU_IDR0.HTTU` as the
  implementation discovery field for hardware translation table updates.  When
  enabled by `CD.HA`/`CD.HD` for stage 1, or `STE.S2HA`/`STE.S2HD` for stage 2,
  a leaf descriptor with `AF==0` can be updated to set `AF`, and a write to a
  read-only DBM leaf can update the descriptor to writable instead of raising
  `F_ACCESS` or `F_PERMISSION`.

## Implemented behavior

- `ARCH_IDR0_HTTU_ACCESS_DIRTY` advertises the bounded AF/Dirty update model in
  the non-secure IDR0 surface and the Apollo Linux selftest expected IDR0 value
  is updated to `0x098db78b`.
- The TBU names descriptor `DBM`, context descriptor `CD.HA`/`CD.HD`, and
  stream-table `STE.S2HA`/`STE.S2HD` bits, and permits those fields in reserved
  encoding checks.
- The compatibility STE word-2 VMID helper masks `S2HA`/`S2HD` so enabling
  stage-2 HTTU does not perturb modeled VMID tags.
- `arch_apply_httu_leaf_update()` updates stage-1 and stage-2 leaf descriptors
  in memory before the architected walker evaluates `AF` and write permission.
- The model records `m_arch_last_httu_af_update`,
  `m_arch_last_httu_dirty_update`, and before/after descriptor state for focused
  component tests.

## Verification evidence

| Command | Log | Result |
| --- | --- | --- |
| `cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j4` | `build/verification/smmu-httu-af-dirty-build-20260511.log` | PASS: `[100%] Built target apollo-smmu-tbu-tests` |
| `./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests --gtest_filter='*HttuStage1AccessAndDirtyUpdatesLeaf:*HttuStage2AccessAndDirtyUpdatesLeaf:*ArchitectedWalkerGranuleBlockAndFaultMatrix:*ArchitectedRegisterMmioSurface*'` | `build/verification/smmu-httu-af-dirty-gtest-20260511.log` | PASS: `[  PASSED  ] 4 tests.` |
| `ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure` | `build/verification/smmu-httu-af-dirty-ctest-20260511.log` | PASS: `100% tests passed, 0 tests failed out of 1` |
| `python3 scripts/check_qbox_smmuv3_compliance.py --json build/verification/smmu-httu-af-dirty-static-20260511.json` | `build/verification/smmu-httu-af-dirty-static-20260511.log` / `.json` | PASS: `SUMMARY {"pass": 1053}`, `full_smmuv3_compliance=not_claimed` |
| `./scripts/check_buildroot_arm64_lane.sh` | `build/verification/smmu-httu-af-dirty-lane-20260511.log` | PASS: lane found IDR0.HTTU, CD.HA/HD, STE.S2HA/S2HD, DBM, and stage-1/stage-2 HTTU test contracts |
| `bash -n scripts/*.sh` | `build/verification/smmu-httu-af-dirty-bash-syntax-20260511.log` | PASS: command exited 0 with no diagnostics |
| `python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py` | `build/verification/smmu-httu-af-dirty-pycompile-20260511.log` | PASS: command exited 0 with no diagnostics |
| `{ git diff --check; git -C sources/qbox diff --check; git -C sources/linux diff --check; }` | `build/verification/smmu-httu-af-dirty-diff-check-20260511.log` | PASS: command exited 0 with no diagnostics |

## No-overclaim boundary

Full ARM SMMUv3 compliance remains `not_claimed`. This slice covers bounded
leaf-level AF and DBM dirty state updates for the modeled stage-1/stage-2
descriptor walkers. It does not claim table-descriptor AF/HAFT updates, full
atomic update ordering, complete cache/TLB coherency side effects, DPT, ECMDQ,
RME/GPT/GPC, or upstream Linux `arm-smmu-v3` lifecycle parity.
