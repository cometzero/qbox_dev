# QBox SMMUv3 command invalidation verification — 2026-05-10

## Scope

This report covers the SMMU-COMP-020/080 follow-up slice for command-driven
invalidation in the Apollo SMMUv3 TBU model. It does not claim full ARM SMMUv3
command queue compliance.

## Implemented slice

- Added `FEATURE_ARCH_CMD_INVALIDATION` to the Apollo TBU feature surface.
- Added command progress/status registers for local observability:
  `REG_ARCH_CMD_STATUS` and `REG_ARCH_CMD_DETAIL`.
- Implemented CMDQ side effects for:
  - `CFGI_STE`, `CFGI_CD`, `CFGI_CD_ALL`, `CFGI_ALL`
  - `TLBI_NH_ALL`, `TLBI_NH_ASID`, `TLBI_NH_VA`, `TLBI_NH_VAA`
  - `ATC_INV`
- Added ATS cache invalidation helpers for global, per-StreamID, per-page, and
  per-StreamID/per-page scopes.
- Added component test `CmdqInvalidationCommandsClearAtsBySidPageAndGlobal`.

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
  2>&1 | tee build/verification/apollo-smmuv3-cmd-invalidation-build-20260510.log
ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure \
  2>&1 | tee build/verification/apollo-smmuv3-cmd-invalidation-ctest-20260510.log
```

Result:

- `apollo_smmu_tbu` rebuilt successfully.
- `apollo-smmu-tbu-tests` rebuilt successfully.
- CTest result: `100% tests passed, 0 tests failed out of 1`.

## Claim boundary

This slice proves modeled command-driven invalidation behavior in component
coverage. Remaining work includes byte-exact command encodings, ASID/VMID/PASID
TLB tags, endpoint ATC completion ordering, command error states, Linux
arm-smmu-v3-driven invalidation, and full multi-master runtime coverage.

### Static/lane gate

Command:

```bash
rm -rf scripts/__pycache__
{
  bash -n scripts/*.sh
  python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py scripts/check_iree_cnn_pipeline_readiness.py scripts/qbox_pty_runner.py
  scripts/check_qbox_smmuv3_compliance.py --self-test-negative --json build/verification/qbox-smmuv3-compliance-cmd-invalidation-20260510.json
  ./scripts/check_buildroot_arm64_lane.sh
  git diff --check
  git -C sources/qbox diff --check
  git -C sources/linux diff --check
} 2>&1 | tee build/verification/smmu-command-invalidation-static-lane-20260510.log
rm -rf scripts/__pycache__
```

Result:

- Shell syntax and Python bytecode checks passed.
- SMMUv3 compliance checker passed with `SUMMARY {"pass": 109}`.
- New invariant passed: `tbu:cmdq-invalidation`.
- Buildroot ARM64 lane contract passed.
- Whitespace checks passed for the superproject, `sources/qbox`, and
  `sources/linux`.

### QBox platform rebuild

Command:

```bash
./scripts/build_qbox_buildroot_platform.sh \
  2>&1 | tee build/verification/qbox-platform-smmu-command-invalidation-20260510.log
```

Result:

- QBox Buildroot platform runtime rebuilt successfully in
  `/build/qbox_dev/sources/qbox/build`.

### Guest no-regression smoke

Command:

```bash
QBOX_HEXAGON_GUEST_SMOKE_STAMP=20260510-smmu-command-invalidation \
QBOX_BOOT_TIMEOUT=80 \
QBOX_IREE_LOGIN_DELAY=24 \
QBOX_IREE_AFTER_COMMAND_DELAY=25 \
./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh \
  2>&1 | tee build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-command-invalidation.driver.log
```

Result:

- Guest smoke passed: `PASS: QBox guest IREE Hexagon tiny-CNN output
  matched`.
- Expected output matched: `1x1x2x2xf32=[[[54 63][90 99]]]`.
- Runtime log preserved the upstream-style HAL registry marker:
  `IREE Apollo Hexagon HAL: upstream-style HAL registry`.
- Runtime log preserved existing SMMUv3 evidence markers for architected CMDQ
  processing, queue selftest, and page-table walker/ATS/PRI/fault readiness.

Evidence:

- `build/verification/apollo-smmuv3-cmd-invalidation-build-20260510.log`
- `build/verification/apollo-smmuv3-cmd-invalidation-ctest-20260510.log`
- `build/verification/smmu-command-invalidation-static-lane-20260510.log`
- `build/verification/qbox-smmuv3-compliance-cmd-invalidation-20260510.json`
- `build/verification/qbox-platform-smmu-command-invalidation-20260510.log`
- `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-command-invalidation.driver.log`
- `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-command-invalidation.log`
