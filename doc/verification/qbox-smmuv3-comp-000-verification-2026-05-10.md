# QBox SMMUv3 SMMU-COMP-000 verification report

- Date: 2026-05-10
- Scope: `/build/qbox_dev`
- Ultragoal story: `G001-implement-the-reviewed-smmuv3-compli`
- Source plan: `doc/analysis/qbox-smmuv3-compliance-gap-plan-2026-05-10.md`
- Checklist: `doc/spec/qbox-smmuv3-compliance-checklist.md`
- Checker: `scripts/check_qbox_smmuv3_compliance.py`

## Result

SMMU-COMP-000 is implemented and verified.  This means the repository now has a
machine-readable compliance inventory, conservative status taxonomy, and a
no-overclaiming gate.  It does **not** mean full ARM SMMUv3 compliance is done.
The current QBox runtime remains a functional/compliance-oriented slice until the
remaining SMMU-COMP gates are implemented and independently verified.

## Current checklist status

| ID | Status | Meaning |
| --- | --- | --- |
| SMMU-COMP-000 | implemented | Checklist/checker/no-overclaiming gate exists and passes. |
| SMMU-COMP-010 | functional-slice | Compatibility TBU ownership is documented; architected split remains future work. |
| SMMU-COMP-020 | functional-slice | Initial Apollo TBU SMMUv3 register/queue aperture exists; full CMDQ/EVENTQ/PRIQ semantics remain open. |
| SMMU-COMP-030 | functional-slice | One-StreamID STE/CD probe path exists; full format matrix remains open. |
| SMMU-COMP-040 | functional-slice | 4KB/4-level happy path exists; full translation matrix remains open. |
| SMMU-COMP-050 | functional-slice | Invalid-STE negative replay is observable; full fault matrix remains open. |
| SMMU-COMP-060 | functional-slice | ATS/PRI behavior is observable as a compatibility slice; protocol matrix remains open. |
| SMMU-COMP-070 | missing | TBU IRQ/MSI/event ordering is not implemented. |
| SMMU-COMP-080 | missing | Multi-master and multi-StreamID isolation are not implemented. |
| SMMU-COMP-090 | functional-slice | Repo-local IREE HAL plugin slice works; upstream registry integration remains open. |
| SMMU-REF-000 | reference-only | Pinned `sources/smmu` reference corpus exists with one known C++ test failure. |

## Commands and evidence

### Static/checker verification

Command:

```sh
bash -n scripts/*.sh configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/post-build.sh
python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py scripts/check_iree_cnn_pipeline_readiness.py scripts/qbox_pty_runner.py
scripts/check_qbox_smmuv3_compliance.py --self-test-negative --json build/verification/qbox-smmuv3-compliance-20260510.json
./scripts/check_buildroot_arm64_lane.sh
./scripts/check_iree_cnn_pipeline_readiness.py --json build/verification/iree-cnn-readiness-smmu-comp-000-20260510.json
git diff --check
```

Evidence:

- `build/verification/smmu-comp-000-static-20260510.log`
- `build/verification/qbox-smmuv3-compliance-20260510.json`
- `build/verification/iree-cnn-readiness-smmu-comp-000-20260510.json`

Observed results:

- SMMUv3 compliance checker: `SUMMARY {"pass": 47}`.
- Checker classification: `smmu_comp_000=implemented`, `full_smmuv3_compliance=not_claimed`.
- Buildroot ARM64 lane check: passed.
- IREE CNN readiness: `38` pass, `5` missing host-tool checks.

Known host-tool gaps from readiness check:

- `iree-import-onnx`
- `iree-compile`
- `iree-run-module`
- Python `onnx`
- Python `numpy`

These gaps do not invalidate the QBox runtime smoke below, which uses already
staged guest artifacts, but they do block fresh host-side IREE artifact rebuilds
from a clean environment.

### QBox platform build

Command:

```sh
./scripts/build_qbox_buildroot_platform.sh \
  2>&1 | tee build/verification/qbox-platform-smmu-comp-000-20260510.log
```

Evidence:

- `build/verification/qbox-platform-smmu-comp-000-20260510.log`
- `sources/qbox/build/arm_smmuv3.so`
- `sources/qbox/build/apollo_smmu_tbu.so`
- `sources/qbox/build/apollo_hexagon_dma.so`
- `sources/qbox/build/_deps/libqemu-build/qemu-prefix/lib/libqemu-system-aarch64.so`
- `sources/qbox/build/_deps/libqemu-build/qemu-prefix/lib/libqemu-system-hexagon.so`

Observed result:

- Build completed with `QBox Buildroot platform runtime built in /build/qbox_dev/sources/qbox/build`.

### QBox guest Hexagon/IREE smoke

Command:

```sh
QBOX_HEXAGON_GUEST_SMOKE_STAMP=20260510-smmu-comp-000 \
QBOX_BOOT_TIMEOUT=180 \
QBOX_IREE_LOGIN_DELAY=24 \
QBOX_IREE_AFTER_COMMAND_DELAY=25 \
./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh \
  2>&1 | tee build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-comp-000.driver.log
```

Evidence:

- `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-comp-000.driver.log`
- `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-comp-000.log`
- `build/verification/qbox-iree-tiny-cnn-hexagon-guest-boot-20260510-smmu-comp-000.log`

Observed result:

- PASS: `QBox guest IREE Hexagon tiny-CNN output matched`.
- Expected and observed output: `1x1x2x2xf32=[[[54 63][90 99]]]`.
- Boot marker present: `Run /sbin/init as init process`.
- Guest login marker present: `apollo-qbox login:`.
- Runtime markers present for:
  - SMMUv3 stream/context descriptor probe
  - SMMUv3 negative fault replay
  - SMMUv3 page-table walker/ATS/PRI/fault queue readiness
  - 128 KiB SG DMA stress over 8 segments
  - dynamic C HAL plugin load
  - two command queues with async interrupt/fence polling
  - async fence signaling for queue 0 and queue 1

## Stop condition / blocker classification

The build and smoke verification for SMMU-COMP-000 passed.  The aggregate
ultragoal is **not** complete because the reviewed plan includes full ARM SMMUv3
compliance work that is still explicitly missing or only a functional slice:

- Missing: SMMU-COMP-070, SMMU-COMP-080.
- Functional-slice only: SMMU-COMP-010, SMMU-COMP-020, SMMU-COMP-030,
  SMMU-COMP-040, SMMU-COMP-050, SMMU-COMP-060, SMMU-COMP-090.
- Reference-only: SMMU-REF-000.

Next implementation should continue deepening SMMU-COMP-020 command/event/PRI
semantics, then move to SMMU-COMP-070 IRQ/MSI delivery and SMMU-COMP-080
multi-master isolation.
