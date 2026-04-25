# PRD: QBox Buildroot ARM64 SoC Linux Boot

## Summary

Create a reproducible QBox platform lane that boots a minimal Buildroot Linux
userspace on an ARM64 Cortex-A710 application cluster. This is the first step
toward a heterogeneous SoC virtual platform that later adds Cortex-R52,
Cortex-M55, Zephyr RTOS, shared SRAM, and SystemC device models.

## Problem

The current QBox checkout has a working AArch64 Linux boot lane, but it is tied
to the Ubuntu platform flow. The project needs a Buildroot-focused lane with a
clear artifact contract, platform configuration, and verification flow. Without
that lane, future heterogeneous SoC work will mix rootfs generation, platform
wiring, and device modeling concerns too early.

## Goals

1. Boot Linux on QBox using a Buildroot-generated minimal userspace.
2. Keep the existing Ubuntu AArch64 platform intact.
3. Create a separate Buildroot ARM64 platform lane with clear artifact names and
   reproducible build outputs.
4. Model the first milestone with 4 x Cortex-A710 cores, GICv3, PL011 console,
   4 GiB DRAM, and initramfs-based rootfs.
5. Keep Linux kernel source/build ownership in a separate git submodule while
   Buildroot owns userspace/rootfs generation.
5. Define the future expansion path for R52, M55, Zephyr, shared SRAM, and
   SystemC devices without blocking the first Linux boot.

## Non-goals

- Do not bring up Cortex-R52 Zephyr in Milestone 1.
- Do not bring up Cortex-M55 Zephyr in Milestone 1.
- Do not add custom SystemC devices before Linux reaches userspace.
- Do not replace or mutate the existing Ubuntu platform as the first step.
- Do not rely on undocumented generated artifacts.

## Users and stakeholders

| Stakeholder | Need |
| --- | --- |
| Platform developer | A repeatable way to boot ARM64 Linux in QBox with Buildroot artifacts. |
| SystemC device developer | A stable Linux platform to attach and test future MMIO/TLM devices. |
| RTOS developer | Reserved topology for later R52/M55 Zephyr integration. |
| Build/integration engineer | Deterministic commands, output paths, and pass/fail checks. |

## Current baseline

The source plan identifies these facts:

- Existing boot path: `sources/qbox/platforms/ubuntu/conf_aarch64.lua`.
- Existing artifact names: `Image.bin`, `ubuntu.dtb`, and
  `image_ext4_initrd.img`.
- Existing DRAM base: `0x80000000`.
- Existing UART0 base: `0x10000000`.
- Existing CPU model in the Ubuntu lane: 8 x Cortex-A76.
- Available QBox CPU components include Cortex-A710, Cortex-R52, and Cortex-M55.
- Buildroot is currently only mentioned in networking configuration notes.

## Milestones

### M1: Buildroot Linux initramfs boot

Scope:

- 4 x Cortex-A710.
- GICv3 and generic timer wiring inherited from the current AArch64 lane.
- PL011 UART console at `0x10000000`.
- 4 GiB DRAM at `0x80000000`.
- Linux `Image` built from the `sources/linux` git submodule.
- Buildroot-generated DTB and initramfs.

Success criteria:

- Buildroot generates DTB and initramfs artifacts without `BR2_LINUX_KERNEL`.
- Standalone Linux submodule build generates the kernel `Image`.
- QBox builds with `LIBQEMU_TARGETS=aarch64`.
- QBox starts the Buildroot platform config.
- Linux prints early boot logs on the PL011 console.
- Linux reaches BusyBox init or shell.
- R52/M55 are not required for this milestone.

### M2: Rootfs and topology hardening

Scope:

- Add ext4 or block-backed rootfs boot after initramfs works.
- Reserve SRAM windows for A710, R52, M55, and shared memory.
- Document memory map and device tree reservations.

Success criteria:

- Linux sees the expected DRAM and reserved-memory regions.
- Optional virtio block rootfs mounts reliably.
- Boot logs and artifacts are captured in `build/` or `doc/` reports.

### M3: Cortex-R52 Zephyr bring-up

Scope:

- 2 x Cortex-R52.
- 2 x R52 UARTs.
- 2 x 2 MiB R52 SRAM windows.
- Standalone Zephyr console boot before Linux interaction.

Success criteria:

- Each R52 instance boots a Zephyr hello/shell image from SRAM.
- UART output is independently observable.

### M4: Cortex-M55 Zephyr bring-up

Scope:

- 1 x Cortex-M55.
- 1 x M55 UART.
- 1 MiB M55 SRAM.
- Reuse lessons from `sources/qbox/platforms/cortex-m55-remote/`.

Success criteria:

- M55 boots Zephyr standalone.
- Console proof is captured.

### M5: SystemC device expansion

Scope:

- Add custom SystemC devices through router, memory, register router, or pass
  patterns.
- Validate one MMIO device at a time from Linux.

Success criteria:

- Linux can read/write a test register device.
- Device integration does not alter the Buildroot image pipeline.

## Acceptance criteria

- A dedicated Buildroot ARM64 lane exists and does not overwrite Ubuntu
  artifacts.
- The Buildroot lane documents exact generated artifacts and where QBox consumes
  them.
- The first boot path uses initramfs before ext4 rootfs.
- Boot verification includes a captured log and explicit pass/fail criteria.
- Future R52/M55/SystemC work is documented but does not block M1.

## Open decisions

| Decision | Default recommendation |
| --- | --- |
| Buildroot source location | Use a workspace-managed Buildroot tree plus `BR2_EXTERNAL`. |
| Kernel version policy | Use latest mainline at implementation time as a separate Linux submodule, and record the exact tag or commit in the report. |
| DTB ownership | Generate or stage the M1 DTB in the Buildroot board directory, then copy/symlink it to QBox artifacts. |
| Kernel build ownership | Build Linux outside Buildroot from `sources/linux`; Buildroot remains rootfs-only. |
| Initramfs vs ext4 first | Initramfs first, ext4 later. |
| R52/M55 modeling | Defer to separate milestones and consider isolated QEMU instances if needed. |
