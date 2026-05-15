# QBox SMMUv3 tagged invalidation verification — 2026-05-10

## Scope

This report covers a SMMU-COMP-020/080 follow-up slice for modeled
ASID/VMID/SSID-aware invalidation in the Apollo SMMUv3 TBU model. It does not
claim full ARM SMMUv3 command queue, PASID, endpoint ATC completion, or Linux
`arm-smmu-v3` invalidation-path compliance.

## Implemented slice

- Added `FEATURE_ARCH_TAGGED_INVALIDATION` to the Apollo TBU feature surface.
- Added ASID/VMID/SSID tags to modeled ATS cache entries.
- Added CMDQ tag-field decode helpers aligned with the Linux SMMUv3 command
  fields:
  - TLBI VMID bits `[47:32]`
  - TLBI ASID bits `[63:48]`
  - ATC_INV SSV/SSID bits `[11]` and `[31:12]`
- Updated TLBI handling:
  - `TLBI_NH_ASID`: invalidate matching ASID+VMID entries.
  - `TLBI_NH_VA`: invalidate matching page+ASID+VMID entries.
  - `TLBI_NH_VAA`: invalidate matching page+VMID entries across ASIDs.
  - `TLBI_NH_ALL`: invalidate matching VMID entries.
- Updated ATC_INV handling so SSID-valid commands invalidate only matching
  StreamID+page+SSID entries.
- Added component test `CmdqTaggedInvalidationHonorsAsidVmidAndSsid`.

## Changed files

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
- `scripts/check_qbox_smmuv3_compliance.py`
- `scripts/check_buildroot_arm64_lane.sh`
- `doc/spec/qbox-smmuv3-compliance-checklist.md`
- `doc/analysis/qbox-smmuv3-compliance-gap-plan-2026-05-10.md`

## Verification

### Component build and CTest

Command:

```bash
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests apollo_smmu_tbu -j"$(nproc)" \
  2>&1 | tee build/verification/apollo-smmuv3-tagged-invalidation-build-20260510.log
ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure \
  2>&1 | tee build/verification/apollo-smmuv3-tagged-invalidation-ctest-20260510.log
```

Result:

- `apollo_smmu_tbu` rebuilt successfully.
- `apollo-smmu-tbu-tests` rebuilt successfully.
- CTest result: `100% tests passed, 0 tests failed out of 1`.

## Claim boundary

This slice proves component-level modeled tag-aware invalidation. Remaining work
includes PASID/SSID CD-table indexing, endpoint ATC invalidate completion and
ordering, Linux `arm-smmu-v3` generated invalidation command coverage, byte-exact
CMDQ error states, and full platform multi-master runtime coverage.

### Static/lane gate

Command:

```bash
rm -rf scripts/__pycache__
{
  bash -n scripts/*.sh
  python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py scripts/check_iree_cnn_pipeline_readiness.py scripts/qbox_pty_runner.py
  scripts/check_qbox_smmuv3_compliance.py --self-test-negative --json build/verification/qbox-smmuv3-compliance-tagged-invalidation-20260510.json
  ./scripts/check_buildroot_arm64_lane.sh
  git diff --check
  git -C sources/qbox diff --check
  git -C sources/linux diff --check
} 2>&1 | tee build/verification/smmu-tagged-invalidation-static-lane-20260510.log
rm -rf scripts/__pycache__
```

Result:

- Shell syntax and Python bytecode checks passed.
- SMMUv3 compliance checker passed with `SUMMARY {"pass": 117}`.
- New invariant passed: `tbu:tagged-invalidation`.
- Buildroot ARM64 lane contract passed, including the tagged invalidation
  feature and component-test markers.
- Whitespace checks passed for the superproject, `sources/qbox`, and
  `sources/linux`.

### QBox platform rebuild

Command:

```bash
./scripts/build_qbox_buildroot_platform.sh \
  2>&1 | tee build/verification/qbox-platform-smmu-tagged-invalidation-20260510.log
```

Result:

- QBox Buildroot platform runtime rebuilt successfully in
  `/build/qbox_dev/sources/qbox/build`.

### Guest no-regression smoke

Command:

```bash
QBOX_HEXAGON_GUEST_SMOKE_STAMP=20260510-smmu-tagged-invalidation \
QBOX_BOOT_TIMEOUT=80 \
QBOX_IREE_LOGIN_DELAY=24 \
QBOX_IREE_AFTER_COMMAND_DELAY=25 \
./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh \
  2>&1 | tee build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-tagged-invalidation.driver.log
```

Result:

- Guest smoke passed: `PASS: QBox guest IREE Hexagon tiny-CNN output
  matched`.
- Expected output matched: `1x1x2x2xf32=[[[54 63][90 99]]]`.
- Runtime readiness marker reflected the new feature bit:
  `features=0x3fff`.
- Runtime log preserved the upstream-style HAL registry marker and existing
  SMMUv3 queue/walker/ATS/PRI/fault readiness markers.

Evidence:

- `build/verification/apollo-smmuv3-tagged-invalidation-build-20260510.log`
- `build/verification/apollo-smmuv3-tagged-invalidation-ctest-20260510.log`
- `build/verification/smmu-tagged-invalidation-static-lane-20260510.log`
- `build/verification/qbox-smmuv3-compliance-tagged-invalidation-20260510.json`
- `build/verification/qbox-platform-smmu-tagged-invalidation-20260510.log`
- `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-tagged-invalidation.driver.log`
- `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-tagged-invalidation.log`

### Final hygiene rerun

After appending this report, the same static/lane gate was rerun and passed:

- `build/verification/smmu-tagged-invalidation-static-final-20260510.log`
- `build/verification/qbox-smmuv3-compliance-tagged-invalidation-final-20260510.json`
- Result: `SUMMARY {"pass": 117}` and Buildroot ARM64 lane PASS.
