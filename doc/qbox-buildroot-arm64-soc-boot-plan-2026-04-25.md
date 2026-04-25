# QBox Buildroot ARM64 SoC Boot Plan

Date: 2026-04-25
Workspace: `/build/qbox_dev`
QBox submodule: `/build/qbox_dev/qbox`
Goal: boot a minimal Buildroot Linux userspace on an ARM64 QBox platform first, then extend toward the requested heterogeneous SoC.

## 0. Current Repository Baseline

The current checkout already has an AArch64 Linux boot lane, but it is Ubuntu-oriented rather than Buildroot-oriented.

Evidence:

- `qbox/README.md:161-175` documents the current AArch64 quick start: build `platforms/ubuntu/fw/` artifacts, build QBox with `LIBQEMU_TARGETS=aarch64`, then run `platforms-vp` with `platforms/ubuntu/conf_aarch64.lua`.
- `qbox/docs/platforms/ubuntu.md:17-27` lists generated Linux artifacts: `Image.bin`, `image_ext4.img`, `image_ext4_initrd.img`, `ubuntu.dts`, and `ubuntu.dtb`.
- `qbox/platforms/ubuntu/conf_aarch64.lua:16-22` defines the boot load addresses.
- `qbox/platforms/ubuntu/conf_aarch64.lua:144-150` loads `Image.bin`, `ubuntu.dtb`, `image_ext4_initrd.img`, and the ARM64 bootloader stub.
- `qbox/platforms/ubuntu/conf_aarch64.lua:33,48,166-188` currently configures eight `cpu_arm_cortexA76` CPUs, not the requested four Cortex-A710 CPUs.
- `qbox/qemu-components/cpu_arm/CMakeLists.txt:1-11` includes `cpu_arm_cortex_a710`, `cpu_arm_cortex_r52`, and `cpu_arm_cortex_m55`, so the requested CPU model classes exist in the QBox component tree.
- `qbox/docs/networking.md:43-89` contains Buildroot SSH/root-login notes, but no Buildroot boot pipeline.

Conclusion: first reuse the proven Ubuntu AArch64 boot contract, but introduce a Buildroot-specific artifact pipeline and platform config instead of mutating the existing Ubuntu lane.

## 1. Target Architecture

### Requested final hardware shape

- Application cluster: 4 x Cortex-A710, arranged as 2 clusters x 2 cores.
- Realtime cores: 2 x Cortex-R52.
- MCU core: 1 x Cortex-M55.
- UARTs: 4 total.
  - A710/Linux: 1 UART.
  - R52/Zephyr: 2 UARTs.
  - M55/Zephyr: 1 UART.
- SRAM: 8 MiB total.
  - A710 SRAM: 1 MiB.
  - R52 SRAM: 2 MiB x 2.
  - M55 SRAM: 1 MiB.
  - Shared SRAM: 2 MiB.
- DRAM: 4 GiB.

### Milestone-1 subset

Do not model the full heterogeneous SoC on day one. Milestone 1 should boot Linux first with:

- 4 x `cpu_arm_cortexA710` only.
- GICv3.
- Generic timer wiring inherited from the current AArch64 platform.
- 1 x PL011 console UART.
- 4 GiB DRAM at the existing base, `0x80000000`.
- Buildroot-generated Linux artifacts loaded through the existing loader mechanism.
- R52/M55 represented only as reserved address-map/DT placeholders or omitted entirely until Linux boot is stable.

## 2. Proposed Memory Map

Use the existing QBox AArch64 map as the baseline and add explicit SRAM windows later.

| Region | Proposed base | Size | Owner | Milestone |
| --- | ---: | ---: | --- | --- |
| DRAM | `0x80000000` | 4 GiB | A710/Linux | M1 |
| A710 SRAM | `0x00400000` | 1 MiB | A710/Linux or firmware scratch | M2 |
| R52 SRAM 0 | `0x00500000` | 2 MiB | R52 #0 Zephyr | M3 |
| R52 SRAM 1 | `0x00700000` | 2 MiB | R52 #1 Zephyr | M3 |
| M55 SRAM | `0x00900000` | 1 MiB | M55 Zephyr | M4 |
| Shared SRAM | `0x00A00000` | 2 MiB | cross-core mailbox/shared memory | M4 |
| UART0 | `0x10000000` | 4 KiB | A710/Linux console | M1 |
| UART1 | TBD | 4 KiB | R52 #0 | M3 |
| UART2 | TBD | 4 KiB | R52 #1 | M3 |
| UART3 | TBD | 4 KiB | M55 | M4 |

Notes:

- `qbox/platforms/ubuntu/conf_aarch64.lua:31` already uses `UART0 = 0x10000000`.
- `qbox/platforms/ubuntu/conf_aarch64.lua:62-66` already maps 4 GiB DRAM at `0x80000000`.
- Avoid changing the DRAM base in M1 because the bootloader, DTB, initrd, and current docs all assume that contract.

## 3. Buildroot Artifact Plan

Create a Buildroot lane outside the upstream `qbox/` submodule first, then wire QBox to consume its outputs.

Recommended workspace layout:

```text
buildroot/
  external/qbox_arm64/
    Config.in
    external.mk
    board/qbox/a710_soc/
      linux.config
      rootfs_overlay/
      post-build.sh
      post-image.sh
      genimage.cfg
      qbox_a710_soc.dts
      readme.txt
    configs/qbox_a710_soc_defconfig
build/
  buildroot-a710/
    images/
      Image
      qbox_a710_soc.dtb
      rootfs.cpio
      rootfs.ext4
```

Initial Buildroot choices:

- Architecture: `BR2_aarch64=y`.
- Toolchain: start with Buildroot internal toolchain for reproducibility.
- Kernel: latest mainline Linux, built by Buildroot, with `Image` output.
- Root filesystem: start with initramfs (`rootfs.cpio`) for the first boot proof; add ext4 block rootfs after console boot is stable.
- Userspace: BusyBox + init scripts + optional Dropbear/OpenSSH later.
- Console: `console=ttyAMA0` or the exact PL011 alias in the generated DTB.

Expected M1 output contract for QBox:

```text
qbox/platforms/buildroot/fw/Artifacts/Image.bin        # or symlink/copy from Buildroot Image
qbox/platforms/buildroot/fw/Artifacts/qbox_a710.dtb
qbox/platforms/buildroot/fw/Artifacts/rootfs.cpio      # M1 initramfs
qbox/platforms/buildroot/conf_aarch64.lua
```

Do not overwrite `qbox/platforms/ubuntu/fw/Artifacts/*` for Buildroot.

## 4. QBox Platform Plan

### Phase 1: clone the existing boot contract

Add a new platform lane rather than modifying Ubuntu directly:

```text
qbox/platforms/buildroot/
  conf_aarch64.lua
  fw/
    arm64_bootloader.lua      # initially copied/reused from ubuntu fw
    qbox_a710_soc.dts         # generated or copied from Buildroot output
    Artifacts/                # ignored/generated
```

Implementation steps:

1. Copy the current AArch64 Lua platform as a starting point.
2. Rename artifact references from Ubuntu names to Buildroot names:
   - `Image.bin` or `Image`.
   - `qbox_a710_soc.dtb`.
   - `rootfs.cpio` for initramfs first.
3. Change `ARM_NUM_CPUS` from 8 to 4.
4. Change CPU moduletype from `cpu_arm_cortexA76` to `cpu_arm_cortexA710`.
5. Keep the existing GICv3, timer PPI, PSCI, loader, PL011 UART, virtio-blk, and virtio-net wiring unless a boot failure proves a change is needed.
6. Keep `LIBQEMU_TARGETS=aarch64`.

### Phase 2: CMake integration

Add a separate target so Ubuntu remains untouched:

```bash
cmake -B qbox/build -S qbox -DLIBQEMU_TARGETS=aarch64
cmake --build qbox/build --parallel
cmake --build qbox/build --target buildroot-a710-boot
```

The new target should depend on:

- `platforms-vp`.
- Buildroot output artifacts, or a preflight check that tells the user how to generate them.

### Phase 3: direct run command

First run should be explicit and debuggable:

```bash
cd /build/qbox_dev/qbox
./build/platforms/platforms-vp -l platforms/buildroot/conf_aarch64.lua
```

Add `timeout`/log capture only after the command reaches a stable console or panic point.

## 5. Device Tree and Kernel Boot Contract

M1 DTB must describe only what Linux needs to boot:

- 4 Cortex-A710 CPUs with correct `enable-method = "psci"`.
- DRAM region at `0x80000000`, size 4 GiB.
- GICv3 distributor/redistributor matching QBox addresses.
- PL011 UART at `0x10000000` as console.
- PSCI node matching `smc` by default; switch to `hvc` only for KVM if used.
- initramfs bootargs for first boot.
- Optional virtio-mmio block/net nodes if enabled.

Kernel command line for initramfs first boot:

```text
console=ttyAMA0 earlycon=pl011,0x10000000 rdinit=/sbin/init loglevel=8
```

For ext4 rootfs later:

```text
console=ttyAMA0 earlycon=pl011,0x10000000 root=/dev/vda rw rootwait loglevel=8
```

## 6. Verification Gates

### Gate A: repository baseline

Already added and passing:

```bash
bash scripts/check_arm64_boot_lane.sh
```

This proves the current checkout has the Ubuntu AArch64 lane and lacks a native Buildroot boot lane.

### Gate B: Buildroot artifact generation

Expected commands after Buildroot scaffold exists:

```bash
make -C buildroot O=/build/qbox_dev/build/buildroot-a710 \
  BR2_EXTERNAL=/build/qbox_dev/buildroot/external/qbox_arm64 \
  qbox_a710_soc_defconfig
make -C buildroot O=/build/qbox_dev/build/buildroot-a710 -j"$(nproc)"
ls -l build/buildroot-a710/images/Image \
      build/buildroot-a710/images/qbox_a710_soc.dtb \
      build/buildroot-a710/images/rootfs.cpio
```

### Gate C: QBox build

```bash
cd /build/qbox_dev/qbox
cmake --preset gcc -DLIBQEMU_TARGETS=aarch64
cmake --build --preset gcc --parallel
```

### Gate D: first Linux boot smoke

```bash
cd /build/qbox_dev/qbox
timeout --signal=SIGQUIT 120s \
  ./build/platforms/platforms-vp -l platforms/buildroot/conf_aarch64.lua \
  2>&1 | tee /build/qbox_dev/build/qbox-a710-buildroot-boot.log
```

Pass criteria:

- Kernel prints early boot on PL011 console.
- Kernel detects 4 CPUs or at least boots CPU0 with PSCI-visible secondaries.
- Kernel mounts initramfs and reaches BusyBox init or shell.
- No immediate GIC/timer/DTB fatal error.

### Gate E: ext4/virtio boot

After initramfs boot works, switch to ext4 rootfs via virtio block and verify:

- `/dev/vda` appears.
- rootfs mounts read-write.
- login or init script completes.
- optional network interface appears if virtio-net is enabled.

## 7. Future R52/M55/Zephyr Plan

Do not block Linux M1 on R52/M55. Add them in later milestones:

### M2: reserve topology

- Add reserved SRAM regions to DTB or QBox platform comments.
- Add shared SRAM `gs_memory` component at the proposed shared address.
- Keep R52/M55 reset-held or absent from Linux-visible topology.

### M3: Cortex-R52 Zephyr

- Instantiate 2 x `cpu_arm_cortexR52` in a separate QEMU instance or clearly isolated QBox CPU group if shared QEMU instance semantics are unsuitable.
- Add two UARTs and two 2 MiB SRAM windows.
- Boot Zephyr hello/shell images from SRAM.
- Add mailbox/shared SRAM test with Linux only after standalone R52 boot works.

### M4: Cortex-M55 Zephyr

- Instantiate `cpu_arm_cortexM55` using the existing Cortex-M55 component family.
- Reuse lessons from `qbox/platforms/cortex-m55-remote/`.
- Add M55 SRAM and UART.
- Validate Zephyr console first, then shared memory.

### M5: SystemC device expansion

- Use `router`/`gs_memory`/`reg_router`/`pass` patterns for new MMIO devices.
- Add one SystemC device at a time with a Linux register-access smoke test.
- Keep device models independent from the Buildroot image pipeline.

## 8. Risk Register

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Cortex-A710 component exists but current platform uses A76 | Linux SMP/DT mismatch | Change only after baseline A76/Ubuntu contract is understood; verify `cpu_arm_cortexA710` module loads. |
| Buildroot mainline latest kernel changes frequently | Reproducibility loss | Pin kernel tarball/commit in Buildroot defconfig despite “latest” intent; document update command separately. |
| DTB/GIC/PSCI mismatch | early boot hang | Start from existing `conf_aarch64.lua` addresses and bootloader, then adjust DTB incrementally. |
| Heterogeneous A/R/M cores in one QEMU instance may be unrealistic | integration complexity | Defer R52/M55 to separate milestones and consider separate QEMU instances plus TLM/shared-memory bridge. |
| Rootfs/ext4 adds block-device variables too early | boot debug noise | First boot with initramfs, then add virtio-blk ext4. |
| New SystemC devices before Linux boot | scope explosion | Freeze M1 to CPU/GIC/UART/DRAM/initramfs only. |

## 9. Recommended Execution Order

1. Commit/keep this plan and baseline check script.
2. Add Buildroot external tree and `qbox_a710_soc_defconfig`.
3. Generate `Image`, `qbox_a710_soc.dtb`, and `rootfs.cpio`.
4. Add `qbox/platforms/buildroot/conf_aarch64.lua` by cloning the Ubuntu AArch64 config.
5. Change CPU count/model to 4 x Cortex-A710.
6. Boot initramfs to BusyBox shell.
7. Add ext4/virtio rootfs boot.
8. Add persistent boot smoke script and dated verification report.
9. Only then start R52/M55 Zephyr and SystemC device milestones.
