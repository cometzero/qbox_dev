# QBox SMMUv3 SMMU-COMP-020 verification report

- Date: 2026-05-10
- Scope: `/build/qbox_dev`
- Story: first functional slice for architected SMMUv3 register and queue surfaces
- Source plan: `doc/analysis/qbox-smmuv3-compliance-gap-plan-2026-05-10.md`
- Checklist: `doc/spec/qbox-smmuv3-compliance-checklist.md`

## Result

SMMU-COMP-020 advanced from `missing` to `functional-slice`.

Implemented in `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`:

- Kept the existing Apollo compatibility/debug register ABI at offsets `0x00..0x8c`.
- Added a SMMUv3 architectural register/queue aperture at offset `0x1000`.
- Added readable ID/status registers and CR0/CR0ACK, IRQ_CTRL/IRQ_CTRLACK, GERROR/GERRORN side effects.
- Added STRTAB, CMDQ, EVENTQ, and PRIQ base/prod/cons state.
- Added memory-backed queue helpers with index/wrap/overflow handling.
- Added initial CMDQ fetch/consume handling for CMD_SYNC, PRI_RESP, RESUME, CFGI, TLBI, and ATC_INV opcodes.
- Added EVENTQ and PRIQ record-push helpers used by the existing fault/PRI paths when queues are configured.
- Added `FEATURE_ARCH_REG_QUEUE_SURFACE`, observed at runtime by feature marker `features=0x7ff`.
- Added `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc` to exercise the
  compatibility-preserving register socket, queue index/wrap helpers, memory-backed CMDQ consume,
  EVENTQ/PRIQ record writes, overflow, and GERROR acknowledge behavior under CTest.
- Enlarged the QBox Apollo TBU MMIO mapping in `sources/qbox/platforms/buildroot/conf_aarch64.lua`
  to `size=0x2000`, making the `0x1000` SMMUv3 aperture guest-visible.
- Added a Linux probe selftest in `sources/linux/drivers/soc/apollo/apollo-hexagon-test.c`
  that programs guest-visible CMDQ/EVENTQ/PRIQ rings in shared SRAM and verifies
  CMDQ consumption, PRIQ push, EVENTQ push, CR0/IRQ acknowledgements, and status bits.

This is not full ARM SMMUv3 compliance.  Full binary command/event/PRI formats,
stall retention, PRG lifecycle, MSI/GIC delivery, and full negative replay
coverage remain open.

## Verification evidence

### Static/checker

Command:

```sh
python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py scripts/check_iree_cnn_pipeline_readiness.py scripts/qbox_pty_runner.py
scripts/check_qbox_smmuv3_compliance.py --self-test-negative --json build/verification/qbox-smmuv3-compliance-guest-queue-selftest-20260510.json
scripts/check_iree_cnn_pipeline_readiness.py --json build/verification/iree-cnn-readiness-smmu-guest-queue-selftest-20260510.json
./scripts/check_buildroot_arm64_lane.sh
git diff --check
```

Evidence:

- `build/verification/smmu-comp-020-static-20260510.log`
- `build/verification/qbox-smmuv3-compliance-comp020-20260510.json`
- `build/verification/qbox-smmuv3-compliance-comp020-20260510.log`
- `build/verification/smmu-comp-020-guest-queue-static-20260510.log`
- `build/verification/qbox-smmuv3-compliance-guest-queue-selftest-20260510.json`
- `build/verification/iree-cnn-readiness-smmu-guest-queue-selftest-20260510.json`

Observed result:

- Compliance checker advanced from `SUMMARY {"pass": 50}` to `SUMMARY {"pass": 63}`.
- Classification includes `smmu_comp_020=functional-slice` with guest-visible register/queue selftest coverage
  and `full_smmuv3_compliance=not_claimed`.
- IREE readiness checker reached `SUMMARY {"missing": 5, "pass": 38}`; the five missing items are
  host-side `iree-*`, `onnx`, and `numpy` tools, not the QBox guest/runtime SMMUv3 lane.
- Buildroot ARM64 lane contract completed with the lane conclusion:
  `Buildroot owns rootfs/DTB generation only; Linux Image comes from sources/linux, and libqemu comes from sources/qemu.`

### Target and platform build

Commands:

```sh
./scripts/build_qbox_buildroot_platform.sh --config-only \
  2>&1 | tee build/verification/qbox-platform-config-apollo-smmu-tbu-tests-20260510.log
cmake --build sources/qbox/build --target apollo_smmu_tbu -j"$(nproc)" \
  2>&1 | tee build/verification/apollo-smmu-tbu-smmu-comp-020-final-build-20260510.log
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)" \
  2>&1 | tee build/verification/apollo-smmu-tbu-reg-queue-test-build-20260510.log
./scripts/build_qbox_buildroot_platform.sh \
  2>&1 | tee build/verification/qbox-platform-smmu-comp-020-reg-queue-tests-20260510.log
```

Evidence:

- `build/verification/qbox-platform-config-apollo-smmu-tbu-tests-20260510.log`
- `build/verification/apollo-smmu-tbu-smmu-comp-020-final-build-20260510.log`
- `build/verification/apollo-smmu-tbu-reg-queue-test-build-20260510.log`
- `build/verification/qbox-platform-smmu-comp-020-reg-queue-tests-20260510.log`
- `sources/qbox/build/apollo_smmu_tbu.so`
- `sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests`

Observed result:

- QBox configure regenerated the component test target.
- Target build reached `Built target apollo_smmu_tbu`.
- Test build reached `Built target apollo-smmu-tbu-tests`.
- Platform build completed with `QBox Buildroot platform runtime built in /build/qbox_dev/sources/qbox/build`.

### Component unit regression

Command:

```sh
ctest --test-dir sources/qbox/build -R '^apollo-smmu-tbu-tests$' --output-on-failure \
  2>&1 | tee build/verification/apollo-smmu-tbu-reg-queue-ctest-20260510.log
```

Evidence:

- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
- `build/verification/apollo-smmu-tbu-reg-queue-ctest-20260510.log`

Observed result:

- `100% tests passed, 0 tests failed out of 1`.
- The test covers:
  - ID/status/CR0ACK/IRQ_CTRLACK register reads and writes through the TBU register socket.
  - Architected queue base decode, producer index wrap, and queue index helpers.
  - EVENTQ and PRIQ memory-backed record writes and interrupt status bits.
  - CMDQ producer write fetching CMD_SYNC and PRI_RESP entries from guest memory.
  - EVENTQ overflow setting `GERROR` and `GERRORN` acknowledgement clearing the error.

### Guest-visible architected queue selftest

Commands:

```sh
./scripts/build_qbox_linux_arm64.sh \
  2>&1 | tee build/verification/qbox-linux-smmu-guest-queue-selftest-20260510.log
./scripts/build_qbox_buildroot_platform.sh \
  2>&1 | tee build/verification/qbox-platform-smmu-guest-queue-selftest-20260510.log
./scripts/stage_buildroot_artifacts.sh \
  2>&1 | tee build/verification/stage-artifacts-smmu-guest-queue-selftest-20260510.log
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)" \
  2>&1 | tee build/verification/apollo-smmu-tbu-reg-queue-test-build-guest-selftest-20260510.log
ctest --test-dir sources/qbox/build -R '^apollo-smmu-tbu-tests$' --output-on-failure \
  2>&1 | tee build/verification/apollo-smmu-tbu-reg-queue-ctest-guest-selftest-20260510.log
```

Evidence:

- `sources/qbox/platforms/buildroot/conf_aarch64.lua`
- `sources/linux/drivers/soc/apollo/apollo-hexagon-test.c`
- `build/verification/qbox-linux-smmu-guest-queue-selftest-20260510.log`
- `build/verification/qbox-platform-smmu-guest-queue-selftest-20260510.log`
- `build/verification/stage-artifacts-smmu-guest-queue-selftest-20260510.log`
- `build/verification/apollo-smmu-tbu-reg-queue-ctest-guest-selftest-20260510.log`

Observed result:

- Linux build reached `Linux Image: /build/qbox_dev/build/linux-a710/arch/arm64/boot/Image`.
- QBox platform build reached `QBox Buildroot platform runtime built in /build/qbox_dev/sources/qbox/build`.
- Artifact staging reached `Staged Linux + Buildroot artifacts into /build/qbox_dev/sources/qbox/platforms/buildroot/fw/Artifacts`.
- CTest reached `100% tests passed, 0 tests failed out of 1`.
- Guest-visible probe marker expected in boot logs:
  `SMMUv3 architected queue register selftest ok idr0=0x1008305 cmdq-cons=2 eventq-prod=1 priq-prod=1 statusr=0x4`.

### Runtime smoke/regression

Command:

```sh
QBOX_HEXAGON_GUEST_SMOKE_STAMP=20260510-smmu-comp-020-final \
QBOX_BOOT_TIMEOUT=180 \
QBOX_IREE_LOGIN_DELAY=24 \
QBOX_IREE_AFTER_COMMAND_DELAY=25 \
./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh \
  2>&1 | tee build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-comp-020-final.driver.log

QBOX_HEXAGON_GUEST_SMOKE_STAMP=20260510-smmu-guest-queue-selftest-final \
QBOX_BOOT_TIMEOUT=180 \
QBOX_IREE_LOGIN_DELAY=24 \
QBOX_IREE_AFTER_COMMAND_DELAY=25 \
./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh \
  2>&1 | tee build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-guest-queue-selftest-final.driver.log
```

Evidence:

- `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-comp-020-final.driver.log`
- `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-comp-020-final.log`
- `build/verification/qbox-iree-tiny-cnn-hexagon-guest-boot-20260510-smmu-comp-020-final.log`
- `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-guest-queue-selftest-final.driver.log`
- `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-guest-queue-selftest-final.log`
- `build/verification/qbox-iree-tiny-cnn-hexagon-guest-boot-20260510-smmu-guest-queue-selftest-final.log`

Observed result:

- PASS: `QBox guest IREE Hexagon tiny-CNN output matched`.
- Expected and observed output: `1x1x2x2xf32=[[[54 63][90 99]]]`.
- Runtime feature marker updated to `SMMUv3 page-table walker/ATS/PRI/fault queue ready features=0x7ff`.
- Guest queue marker added:
  `SMMUv3 architected queue register selftest ok idr0=0x1008305 cmdq-cons=2 eventq-prod=1 priq-prod=1 statusr=0x4`.
- Stream/context descriptor walk, negative fault replay, 128 KiB SG DMA, dynamic C HAL plugin, two command queues,
  and async IRQ/fence markers remained present.  The smoke script now avoids brittle exact matching on
  UART-interleaved IREE fence lines and relies on stable DMA/kernel async markers plus the final output contract.

## Remaining blockers

- SMMU-COMP-020 is still a functional slice: it now has component-level register/queue unit coverage
  and a guest-visible CMDQ/EVENTQ/PRIQ selftest, but still needs reference-derived binary record
  tests, stall-pending retention, PRG lifecycle coverage, and the full negative replay matrix.
- SMMU-COMP-070 remains missing: Apollo TBU still has no IRQ output sockets or MSI/GIC delivery model.
- SMMU-COMP-080 remains missing: current topology still proves only one StreamID/master isolation path.
- Full SMMUv3 compliance remains explicitly not claimed.
