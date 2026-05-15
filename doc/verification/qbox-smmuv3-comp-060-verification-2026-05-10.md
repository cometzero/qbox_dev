# QBox SMMUv3 SMMU-COMP-060 verification — 2026-05-10

## Scope

SMMU-COMP-060 is still a **functional slice**, not full ARM SMMUv3 ATS/PRI
packet compliance. This slice adds component-visible protocol state so the
Apollo TBU no longer represents ATS/PRI only as undifferentiated counters/logs.

Implemented coverage:

- ATS response outcome accounting for success, Unsupported Request (UR), and
  Completer Abort (CA).
- PRG-tagged PRI pending request tracking.
- Memory-backed PRIQ records that preserve the existing guest selftest ABI while
  exposing ATS status and PRG fields in later record words.
- CMD_PRI_RESP handling for accept/clear, reject, and unknown PRG responses.
- Compatibility markers used by the existing Linux/QBox guest smoke remain
  present.

Open blockers:

- Full ATSCHK/EATS/secure-stream gating is not modeled.
- PRI queue record bit layout is compatibility-oriented and not a complete
  architected byte-for-byte implementation.
- Stall/PRG lifecycle, PRI_RESP ordering, and endpoint ATC invalidation remain
  later SMMU-COMP-050/SMMU-COMP-060 work.
- Full IRQ/MSI/GIC delivery and ordering remain outside this slice.

## Changed files

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
- `scripts/check_qbox_smmuv3_compliance.py`
- `scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh`
- `doc/spec/qbox-smmuv3-compliance-checklist.md`
- `doc/analysis/qbox-smmuv3-compliance-gap-plan-2026-05-10.md`

## New component tests

- `ArchitectedAtsPriProtocolMatrixAndPriResp`
- `CmdPriRespUnknownPrgIsAccounted`

## Validation evidence

### Component build and CTest

```bash
{
  cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)"
  ctest --test-dir sources/qbox/build -R '^apollo-smmu-tbu-tests$' --output-on-failure
} 2>&1 | tee build/verification/apollo-smmuv3-ats-pri-ctest-20260510.log
```

Result:

- `100% tests passed, 0 tests failed out of 1`

### QBox platform build

```bash
./scripts/build_qbox_buildroot_platform.sh \
  2>&1 | tee build/verification/qbox-platform-smmu-comp-060-ats-pri-20260510.log
```

Result:

- `QBox Buildroot platform runtime built in /build/qbox_dev/sources/qbox/build`

### Guest IREE Hexagon smoke

The initial SMMU-COMP-060 guest smoke produced the correct tiny-CNN output but
hit a false negative because APOLLO TBU logs interleaved into the long kernel
selftest marker. The smoke script now matches the stable selftest prefix and the
rerun passed.

```bash
QBOX_HEXAGON_GUEST_SMOKE_STAMP=20260510-smmu-comp-060-ats-pri-fixed \
QBOX_BOOT_TIMEOUT=80 \
QBOX_IREE_LOGIN_DELAY=24 \
QBOX_IREE_AFTER_COMMAND_DELAY=25 \
./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh \
  2>&1 | tee \
  build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-comp-060-ats-pri-fixed.driver.log
```

Result:

- `PASS: QBox guest IREE Hexagon tiny-CNN output matched`
- Output contract: `1x1x2x2xf32=[[[54 63][90 99]]]`
- Combined log:
  `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-comp-060-ats-pri-fixed.log`
- Boot log:
  `build/verification/qbox-iree-tiny-cnn-hexagon-guest-boot-20260510-smmu-comp-060-ats-pri-fixed.log`

### Static checker, syntax, and diff hygiene

```bash
{
  bash -n scripts/*.sh
  python3 -m py_compile \
    scripts/check_qbox_smmuv3_compliance.py \
    scripts/check_iree_cnn_pipeline_readiness.py \
    scripts/qbox_pty_runner.py
  scripts/check_qbox_smmuv3_compliance.py \
    --self-test-negative \
    --json build/verification/qbox-smmuv3-compliance-ats-pri-final-3-20260510.json
  git diff --check
  git -C sources/qbox diff --check
  git -C sources/linux diff --check
} 2>&1 | tee build/verification/smmu-comp-060-ats-pri-static-final-3-20260510.log
```

Result:

- `SUMMARY {"pass": 88}`
- `"full_smmuv3_compliance": "not_claimed: current QBox remains a functional/compliance-oriented slice until later SMMU-COMP gates pass"`

### Buildroot ARM64 lane contract

```bash
./scripts/check_buildroot_arm64_lane.sh \
  2>&1 | tee build/verification/check-buildroot-arm64-lane-smmu-comp-060-20260510.log
```

Result:

- Lane conclusion: Buildroot owns rootfs/DTB generation only; Linux Image comes
  from `sources/linux`, and libqemu comes from `sources/qemu`.

## Claim boundary

`full_smmuv3_compliance` remains `not_claimed`. This report only upgrades
SMMU-COMP-060 from counter/log-only behavior to a component-tested ATS/PRI
functional slice.
