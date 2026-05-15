# QBox SMMUv3 SMMU-COMP-070 verification report

- Date: 2026-05-10
- Scope: `/build/qbox_dev`
- Story: signal-level Apollo TBU SMMUv3 interrupt functional slice
- Source plan: `doc/analysis/qbox-smmuv3-compliance-gap-plan-2026-05-10.md`
- Checklist: `doc/spec/qbox-smmuv3-compliance-checklist.md`

## Result

SMMU-COMP-070 advanced from `missing` to `functional-slice`.

Implemented in `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`:

- Added `irq_out[0..3]` signal outputs for EVENTQ, PRIQ, CMDQ_SYNC, and GERROR.
- Added IRQ output updates gated by architected `IRQ_CTRL` and status bits.
- Asserted signal-level IRQs when EVENTQ/PRIQ records are pushed, CMD_SYNC is consumed, or GERROR is raised.
- Deasserted EVENTQ/PRIQ/GERROR outputs when guest-visible cons/ack registers clear the corresponding status.
- Kept outputs safe when unbound, so existing platform runs are not forced into duplicate GIC ownership.

This is not full ARM SMMUv3 IRQ/MSI compliance. Full MSI doorbells, GIC routing ownership,
architected interrupt ordering, Linux `arm-smmu-v3` interrupt handling integration, and negative
IRQ ordering tests remain open.

## Verification evidence

### Component unit regression

Command:

```sh
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)"
ctest --test-dir sources/qbox/build -R '^apollo-smmu-tbu-tests$' --output-on-failure
```

Evidence:

- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
- `build/verification/apollo-smmu-tbu-irq-output-test-20260510.log`

Observed result:

- Target build reached `Built target apollo-smmu-tbu-tests`.
- CTest reached `100% tests passed, 0 tests failed out of 1`.
- New test `ArchitectedIrqOutputsFollowQueueStatus` covers:
  - EVENTQ output assertion and deassertion through `EVENTQ_CONS`.
  - PRIQ output assertion and deassertion through `PRIQ_CONS`.
  - CMDQ_SYNC output assertion after memory-backed `CMD_SYNC` consumption.
  - GERROR output assertion on queue overflow and deassertion through `GERRORN` ack.

### Platform build regression

Command:

```sh
./scripts/build_qbox_buildroot_platform.sh
```

Evidence:

- `build/verification/qbox-platform-smmu-comp-070-irq-output-20260510.log`

Observed result:

- Build reached `QBox Buildroot platform runtime built in /build/qbox_dev/sources/qbox/build`.
- Runtime artifacts were produced using `sources/qemu` as the libqemu dependency.

### Guest IREE smoke regression

Command:

```sh
QBOX_HEXAGON_GUEST_SMOKE_STAMP=20260510-smmu-comp-070-irq-output \
QBOX_BOOT_TIMEOUT=180 \
QBOX_IREE_LOGIN_DELAY=24 \
QBOX_IREE_AFTER_COMMAND_DELAY=25 \
./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh
```

Evidence:

- `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-comp-070-irq-output.driver.log`
- `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-comp-070-irq-output.log`
- `build/verification/qbox-iree-tiny-cnn-hexagon-guest-boot-20260510-smmu-comp-070-irq-output.log`

Observed result:

- Driver reached `PASS: QBox guest IREE Hexagon tiny-CNN output matched`.
- Expected tensor matched: `1x1x2x2xf32=[[[54 63][90 99]]]`.
- Boot/runtime log includes `APOLLO_SMMU_TBU: architected IRQ update` for EVENTQ/PRIQ/CMDQ_SYNC/GERROR status changes.
- Existing async fence and multi-queue IREE markers still passed:
  - `IREE Apollo Hexagon HAL: async fence signaled queue=0 fence=1 status=0x53474f4b`
  - `IREE Apollo Hexagon HAL: offload complete queue=1 status=0x434e4e4f`
  - `IREE Apollo Hexagon HAL: async fence signaled queue=1 fence=2 status=0x434e4e4f`

### Buildroot ARM64 lane contract

Command:

```sh
./scripts/check_buildroot_arm64_lane.sh
```

Evidence:

- `build/verification/check-buildroot-arm64-lane-smmu-comp-070-20260510.log`

Observed result:

- Lane checker completed with only `PASS` records and the conclusion:
  `Buildroot owns rootfs/DTB generation only; Linux Image comes from sources/linux, and libqemu comes from sources/qemu.`

### Static/checker gate

Command:

```sh
python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py scripts/check_iree_cnn_pipeline_readiness.py scripts/qbox_pty_runner.py
scripts/check_qbox_smmuv3_compliance.py --self-test-negative --json build/verification/qbox-smmuv3-compliance-irq-output-20260510.json
git diff --check
git -C sources/qbox diff --check
git -C sources/linux diff --check
```

Evidence:

- `build/verification/smmu-comp-070-irq-output-static-20260510.log`
- `build/verification/qbox-smmuv3-compliance-irq-output-20260510.json`

Observed result:

- Compliance checker reached `SUMMARY {"pass": 67}`.
- Compliance checker classified `smmu_comp_070` as `functional-slice` only.
- Compliance checker classified `full_smmuv3_compliance` as `not_claimed`.

## Remaining blockers

- Full IRQ/MSI/GIC delivery is not complete. The Apollo TBU signal outputs are not yet the canonical
  Linux SMMUv3 interrupt owner.
- Event ordering and interrupt coalescing are not modeled.
- MSI table/doorbell semantics are not implemented.
- Guest negative IRQ replay tests are still missing.
- SMMU-COMP-080 multi-master isolation remains missing.
