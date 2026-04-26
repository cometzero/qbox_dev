# Apollo Hexagon Firmware DMA Verification

Date: 2026-04-26
Workspace: `/build/qbox_dev`
Branch: `feature/qbox_dev`

## Scope

This report records the next bring-up step after the SMMUv3/Hexagon sidecar
plan: run real Hexagon firmware in QBox and prove firmware-triggered DMA traffic
while the A710 Linux/Buildroot lane still boots to login.

## Implemented Changes

- Added `apollo_hexagon_dma` SystemC/TLM dynamic module under
  `sources/qbox/systemc-components/apollo_hexagon_dma/`.
- Added Hexagon firmware smoke sources:
  - `sources/qbox/platforms/buildroot/fw/hexagon_dma_smoke.s`
  - `sources/qbox/platforms/buildroot/fw/hexagon_dma_smoke.ld`
- Added `scripts/build_qbox_hexagon_firmware.sh` and integrated it into QBox
  platform build/staging.
- Updated `sources/qbox/platforms/buildroot/conf_aarch64.lua` to:
  - build/run `qemu_cpu_hexagon` powered on,
  - load `apollo_hexagon_dma.bin` into Hexagon SRAM,
  - alias Hexagon local boot address `0x0` to SoC SRAM `0x00C00000`,
  - connect `apollo_hexagon_dma` MMIO at `0x1C220000`,
  - provide shared SRAM at `0x00A00000` for DMA destination.
- Updated Linux DTS and driver so `apollo-hexagon-test` checks the shared SRAM
  pattern produced by firmware DMA before reporting probe success.

## Firmware/DMA Contract

The smoke firmware writes an 8-word source pattern at `0x00C01000`, programs the
SystemC DMA registers at `0x1C220000`, polls `STATUS`, and writes a completion
magic to `FW_DONE`.

| Item | Value |
| --- | --- |
| Source | `0x00C01000` in Hexagon SRAM |
| Destination | `0x00A00000` in shared SRAM |
| Length | 32 bytes |
| First word | `0x48455831` |
| Done magic | `0x48455844` |

## Commands Run

```bash
./scripts/build_qbox_linux_arm64.sh \
  2>&1 | tee build/verification/linux-hexagon-fw-dma-2026-04-26-222759.log
./scripts/build_qbox_buildroot_arm64.sh \
  2>&1 | tee build/verification/buildroot-dtb-hexagon-fw-dma-2026-04-26-222627.log
./scripts/build_qbox_buildroot_platform.sh \
  2>&1 | tee build/verification/qbox-platform-hexagon-fw-dma-2026-04-26-222325.log
./scripts/stage_buildroot_artifacts.sh \
  2>&1 | tee build/verification/stage-hexagon-fw-dma-2026-04-26-222829.log

bash -n scripts/build_qbox_hexagon_firmware.sh \
  scripts/build_qbox_buildroot_platform.sh \
  scripts/run_qbox_buildroot_boot.sh \
  scripts/stage_buildroot_artifacts.sh \
  scripts/check_buildroot_arm64_lane.sh
./scripts/check_buildroot_arm64_lane.sh
git diff --check

QBOX_BOOT_TIMEOUT=60 \
QBOX_BOOT_LOG=build/verification/qbox-boot-hexagon-fw-dma-2026-04-26-222848.log \
  ./scripts/run_qbox_buildroot_boot.sh
```

## Build Evidence

- Hexagon firmware built and staged:
  - `sources/qbox/platforms/buildroot/fw/Artifacts/apollo_hexagon_dma.bin`
  - size: `180 bytes`
- Linux build completed with ccache and produced:
  - `build/linux-a710/arch/arm64/boot/Image`
- Buildroot regenerated rootfs/DTB and reported:
  - `Generated /build/qbox_dev/build/buildroot-a710/images/apollo_soc.dtb with initrd [0x8a800000, 0x8aba2200)`
- QBox platform build completed with local `sources/qemu`/libqemu and ccache,
  including `apollo_hexagon_dma`, `qemu_cpu_hexagon`, and the Buildroot runtime.

## Boot Evidence

Boot log:

- `build/verification/qbox-boot-hexagon-fw-dma-2026-04-26-222848.log`

Selected markers:

```text
APOLLO_HEXAGON_DMA: firmware requested DMA src=0xc01000 dst=0xa00000 len=0x20
APOLLO_HEXAGON_DMA: DMA copy complete src=0xc01000 dst=0xa00000 len=0x20 first=0x48455831
APOLLO_HEXAGON_DMA: firmware done magic=0x48455844
Booting Linux on physical CPU 0x0000000000 [0x412fd471]
Machine model: Apollo SoC on apollo-qbox
arm-smmu-v3 1c200000.iommu: oas 44-bit (features 0x01008305)
apollo-hexagon-test 1c220000.hexagon: iommu group attached
apollo-hexagon-test 1c220000.hexagon: firmware dma traffic ok dst=0x0000000000a00000 words=8 first=0x48455831
apollo-hexagon-test 1c220000.hexagon: dma selftest ok dma=0x0000fffffffff000 size=4096
apollo-hexagon-test 1c220000.hexagon: probe ok
apollo-qbox login:
```

The bounded verification run returned `BOOT_RC=124` because `QBOX_BOOT_TIMEOUT=60`
intentionally stopped the otherwise unlimited interactive simulation after the
login prompt was reached.

## Conclusion

The current Apollo QBox platform now executes Hexagon firmware and observes
firmware-triggered DMA traffic before Linux completes boot. The Linux driver
independently verifies the DMA destination pattern in shared SRAM and still
binds behind the SMMUv3-visible `hexagon@1c220000` device.

## Remaining Limitations

- The DMA copy is performed by the new SystemC `apollo_hexagon_dma` TLM engine
  after firmware MMIO programming; it is not yet a native Hexagon DMA
  controller model.
- The SystemC DMA path does not yet traverse SMMUv3 translation. Current SMMUv3
  proof is Linux probe/IOMMU group attach plus APSS coherent DMA allocation.
- Reset/power sequencing, mailbox/doorbell IRQs, production firmware ABI, and
  userspace driver interfaces remain future work.
