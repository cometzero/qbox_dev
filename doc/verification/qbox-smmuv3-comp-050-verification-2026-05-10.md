# QBox SMMUv3 SMMU-COMP-050 verification — 2026-05-10

## Scope

SMMU-COMP-050 is still a **functional slice**, not a byte-exact ARM SMMUv3
EVENTQ/stall replay implementation. This slice expands the previous invalid-STE
negative replay marker into component-visible fault replay state and records.

Implemented coverage:

- EVENTQ record word 3 now carries a compact syndrome detail word: reason,
  fault class, stage, attributes, and replay sequence.
- Fault classes cover STE, CD, and translation/page faults.
- Negative replay queues stall-pending state instead of only incrementing a log
  counter.
- CMD_RESUME handling distinguishes retry and terminate responses.
- EVENTQ overflow preserves stall-pending accounting and raises GERROR.
- Existing Linux/QBox invalid-STE negative replay compatibility marker remains
  present.
- The guest smoke marker was relaxed to `SMMUv3 architected queue` because
  APOLLO/SystemC UART output can interleave later words in the Linux log line;
  the final fixed smoke log still contains the full kernel marker.

Open blockers:

- EVENTQ byte layout is compatibility-oriented and not a complete architectural
  EVTQ record encoding.
- Substream/PASID, stage-2 IPA, privilege/security, access-flag, permission, and
  full syndrome fields remain incomplete.
- Retry-after-mapping-fix is modeled as component-visible state only; it does not
  re-drive a blocked endpoint transaction.
- Guest runtime validates compatibility invalid-STE replay and end-to-end IREE
  survival, while the full syndrome/stall matrix is covered by component tests.

## Changed files

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
- `scripts/check_qbox_smmuv3_compliance.py`
- `scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh`
- `doc/spec/qbox-smmuv3-compliance-checklist.md`
- `doc/analysis/qbox-smmuv3-compliance-gap-plan-2026-05-10.md`

## New component tests

- `FaultReplayRecordsSyndromeAndResumeState`
- `FaultReplayOverflowKeepsStallPending`

## Validation evidence

### Component build and CTest

```bash
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)" \
  2>&1 | tee build/verification/apollo-smmuv3-fault-replay-build-20260510.log
ctest --test-dir sources/qbox/build -R '^apollo-smmu-tbu-tests$' \
  --output-on-failure \
  2>&1 | tee build/verification/apollo-smmuv3-fault-replay-ctest-20260510.log
```

Result:

- `build/verification/apollo-smmuv3-fault-replay-build-20260510.log`: target
  `apollo-smmu-tbu-tests` built.
- `build/verification/apollo-smmuv3-fault-replay-ctest-20260510.log`:
  `100% tests passed, 0 tests failed out of 1`.

### Platform build

```bash
./scripts/build_qbox_buildroot_platform.sh \
  2>&1 | tee build/verification/qbox-platform-smmu-comp-050-fault-replay-20260510.log
```

Result:

- `build/verification/qbox-platform-smmu-comp-050-fault-replay-20260510.log`:
  `QBox Buildroot platform runtime built in /build/qbox_dev/sources/qbox/build`.

### Guest IREE smoke

```bash
QBOX_HEXAGON_GUEST_SMOKE_STAMP=20260510-smmu-comp-050-fault-replay-fixed \
QBOX_BOOT_TIMEOUT=80 \
QBOX_IREE_LOGIN_DELAY=24 \
QBOX_IREE_AFTER_COMMAND_DELAY=25 \
./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh \
  2>&1 | tee build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-comp-050-fault-replay-fixed.driver.log
```

Result:

- `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-comp-050-fault-replay-fixed.driver.log`:
  `PASS: QBox guest IREE Hexagon tiny-CNN output matched` and
  `1x1x2x2xf32=[[[54 63][90 99]]]`.
- `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-comp-050-fault-replay-fixed.log`:
  `SMMUv3 negative fault replay ok`,
  `SMMUv3 architected queue register selftest ok`, and
  `APOLLO_SMMU_TBU: architected fault replay queued ... detail=0x10210102`.
- `build/verification/qbox-iree-tiny-cnn-hexagon-guest-boot-20260510-smmu-comp-050-fault-replay-fixed.log`:
  same boot-time fault replay and architected queue markers.

### Static compliance gate

```bash
rm -rf scripts/__pycache__
{
  bash -n scripts/*.sh
  python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py \
    scripts/check_iree_cnn_pipeline_readiness.py scripts/qbox_pty_runner.py
  scripts/check_qbox_smmuv3_compliance.py --self-test-negative \
    --json build/verification/qbox-smmuv3-compliance-fault-replay-final-20260510.json
  git diff --check
  git -C sources/qbox diff --check
  git -C sources/linux diff --check
} 2>&1 | tee build/verification/smmu-comp-050-fault-replay-static-final-20260510.log
rm -rf scripts/__pycache__
```

Result:

- `build/verification/smmu-comp-050-fault-replay-static-final-20260510.log`:
  `SUMMARY {"pass": 92}`.
- `build/verification/qbox-smmuv3-compliance-fault-replay-final-20260510.json`:
  `tbu:fault-replay-matrix` pass and
  `full_smmuv3_compliance` remains `not_claimed`.
- `bash -n`, Python compile, and `git diff --check` for the superproject,
  `sources/qbox`, and `sources/linux` passed.

### Buildroot ARM64 lane

```bash
./scripts/check_buildroot_arm64_lane.sh \
  2>&1 | tee build/verification/check-buildroot-arm64-lane-smmu-comp-050-20260510.log
```

Result:

- `build/verification/check-buildroot-arm64-lane-smmu-comp-050-20260510.log`:
  all lane checks passed, including the SMMUv3 fault replay feature/log checks.

## Claim boundary

`full_smmuv3_compliance` remains `not_claimed`. This report only upgrades
SMMU-COMP-050 from invalid-STE counter/log replay to a component-tested
syndrome/stall replay functional slice.
## 2026-05-10 follow-up

A later SMMU-COMP-050 slice adds architected common EVENTQ event numbers,
StreamID/SubstreamID fields, and modeled `CMD_STALL_TERM` accounting. Evidence is
recorded in `doc/verification/qbox-smmuv3-event-record-layout-verification-2026-05-10.md`.
Full byte-exact event/stall replay and endpoint transaction re-drive remain open.
