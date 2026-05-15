# QBox SMMUv3 SMMU-COMP-040 verification — 2026-05-10

## Scope

SMMU-COMP-040 remains a **functional slice**, not complete Arm SMMUv3
page-table walker parity. This slice expands the previous 4KB/4-level
happy-path probe into component-tested walker vectors for selected granules,
leaf descriptors, access faults, and stage composition.

Implemented coverage:

- Generic component walker helpers for 4K, 16K, and 64K granule-sized tables.
- Start-level selection for the staged component vectors.
- Table, block, and page descriptor handling.
- Access-flag and write-permission fault checks.
- Stage-2-only STE mode and nested S1+S2 walk mode for selected vectors.
- Stage-aware fault detail encoding uses S1/S2 in EVENTQ-compatible fault
  detail words.
- Existing Linux guest 4KB/4-level descriptor probe remains the runtime
  compatibility proof; guest smoke markers now match the new stage/granule
  walker log format.

Open blockers:

- The walker is still a compact compatibility model, not a byte-exact Arm
  descriptor decoder.
- Full TCR/VTCR field decode, output/address-size limits, shareability/cache
  attributes, DBM, UXN/PXN, privilege/security, S1DSS/S1CDMax PASID indexing,
  and full Arm reserved-matrix parity remain incomplete; modeled STE/CD reserved/illegal checks are covered by the SMMU-COMP-030 follow-up report.
- Stage-2 and nested support is component-visible only; Linux still exercises
  the original stage-1 compatibility marker.
- Reference-vector parity against `sources/smmu` is not complete.

## Changed files

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
- `scripts/check_qbox_smmuv3_compliance.py`
- `scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh`
- `doc/spec/qbox-smmuv3-compliance-checklist.md`
- `doc/analysis/qbox-smmuv3-compliance-gap-plan-2026-05-10.md`

## New component tests

- `ArchitectedWalkerGranuleBlockAndFaultMatrix`
- `ArchitectedWalkerStage2AndNestedMatrix`

## Validation evidence

### Component build and CTest

```bash
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)" \
  2>&1 | tee build/verification/apollo-smmuv3-walker-matrix-build-20260510.log
ctest --test-dir sources/qbox/build -R '^apollo-smmu-tbu-tests$' \
  --output-on-failure \
  2>&1 | tee build/verification/apollo-smmuv3-walker-matrix-ctest-20260510.log
```

Result:

- `build/verification/apollo-smmuv3-walker-matrix-build-20260510.log`:
  `Built target apollo-smmu-tbu-tests`.
- `build/verification/apollo-smmuv3-walker-matrix-ctest-20260510.log`:
  `100% tests passed, 0 tests failed out of 1`.

### QBox platform build

```bash
./scripts/build_qbox_buildroot_platform.sh \
  2>&1 | tee build/verification/qbox-platform-smmu-comp-040-walker-matrix-20260510.log
```

Result:

- `build/verification/qbox-platform-smmu-comp-040-walker-matrix-20260510.log`:
  `QBox Buildroot platform runtime built in /build/qbox_dev/sources/qbox/build`.

### Guest IREE Hexagon smoke

```bash
QBOX_HEXAGON_GUEST_SMOKE_STAMP=20260510-smmu-comp-040-walker-matrix-fixed \
QBOX_BOOT_TIMEOUT=80 \
QBOX_IREE_LOGIN_DELAY=24 \
QBOX_IREE_AFTER_COMMAND_DELAY=25 \
./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh \
  2>&1 | tee build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-comp-040-walker-matrix-fixed.driver.log
```

Result:

- `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-comp-040-walker-matrix-fixed.driver.log`:
  `PASS: QBox guest IREE Hexagon tiny-CNN output matched`.
- Runtime output matched `1x1x2x2xf32=[[[54 63][90 99]]]`.
- Combined runtime log:
  `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-comp-040-walker-matrix-fixed.log`.
- Boot log:
  `build/verification/qbox-iree-tiny-cnn-hexagon-guest-boot-20260510-smmu-comp-040-walker-matrix-fixed.log`.

### Static checker and diff hygiene

```bash
rm -rf scripts/__pycache__
{
  bash -n scripts/*.sh
  python3 -m py_compile \
    scripts/check_qbox_smmuv3_compliance.py \
    scripts/check_iree_cnn_pipeline_readiness.py \
    scripts/qbox_pty_runner.py
  scripts/check_qbox_smmuv3_compliance.py \
    --self-test-negative \
    --json build/verification/qbox-smmuv3-compliance-walker-matrix-final-20260510.json
  git diff --check
  git -C sources/qbox diff --check
  git -C sources/linux diff --check
} 2>&1 | tee build/verification/smmu-comp-040-walker-matrix-static-final-20260510.log
rm -rf scripts/__pycache__
```

Result:

- `build/verification/smmu-comp-040-walker-matrix-static-final-20260510.log`:
  `SUMMARY {"pass": 97}`.
- `build/verification/qbox-smmuv3-compliance-walker-matrix-final-20260510.json`:
  includes `tbu:walker-granule-stage-matrix` with `status: pass`.
- `git diff --check`, `git -C sources/qbox diff --check`, and
  `git -C sources/linux diff --check` completed without whitespace errors.

### Buildroot ARM64 lane contract

```bash
./scripts/check_buildroot_arm64_lane.sh \
  2>&1 | tee build/verification/check-buildroot-arm64-lane-smmu-comp-040-20260510.log
```

Result:

- `build/verification/check-buildroot-arm64-lane-smmu-comp-040-20260510.log`:
  passed all lane contract checks and preserved the lane conclusion that
  Buildroot owns rootfs/DTB generation while Linux Image and libqemu come from
  their source submodules.

## Claim boundary

`full_smmuv3_compliance` remains `not_claimed`. This report only upgrades
SMMU-COMP-040 from a single 4KB/4-level happy-path probe to a component-tested
walker matrix functional slice covering selected 4K/16K/64K, block/page,
AF/permission, stage-2-only, and nested S1+S2 vectors.
