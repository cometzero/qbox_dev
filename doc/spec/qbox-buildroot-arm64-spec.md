# Specification: QBox Buildroot ARM64 SoC Boot Lane

## Scope

This specification defines the first Buildroot ARM64 Linux boot lane for the
QBox workspace. It converts the source plan into concrete functional and
technical requirements.

## Functional requirements

### FR-1: Buildroot artifact generation

The project must produce these artifacts for Milestone 1:

| Artifact | Required | Description |
| --- | --- | --- |
| `Image` or `Image.bin` | Yes | Uncompressed AArch64 Linux kernel image. |
| `qbox_a710_soc.dtb` | Yes | Device tree blob matching the QBox platform map. |
| `rootfs.cpio` | Yes | Initramfs root filesystem for first userspace proof. |
| `rootfs.ext4` | Later | Block rootfs for post-initramfs validation. |

Artifacts must be generated under a reproducible Buildroot output directory and
then staged, copied, or symlinked into the QBox platform artifact directory.

### FR-2: Separate QBox platform lane

The Buildroot platform must not overwrite Ubuntu artifacts. It must use a
separate QBox platform path such as:

```text
qbox/platforms/buildroot/
  conf_aarch64.lua
  fw/
    arm64_bootloader.lua
    Artifacts/
```

### FR-3: ARM64 Linux boot contract

The first Buildroot Linux boot must use:

- 4 x Cortex-A710 CPUs.
- 4 GiB DRAM at `0x80000000`.
- PL011 UART console at `0x10000000`.
- GICv3 interrupt controller.
- PSCI enable method.
- Existing QBox loader-based boot flow.

### FR-4: Verification

The implementation must provide repeatable verification for:

1. Repository baseline.
2. Buildroot artifact existence.
3. QBox build.
4. Linux boot to initramfs userspace.
5. Later ext4 rootfs boot.

### FR-5: Future expansion boundaries

The first implementation must leave space for:

- A710 SRAM: 1 MiB.
- R52 SRAM: 2 MiB x 2.
- M55 SRAM: 1 MiB.
- Shared SRAM: 2 MiB.
- UART1/2/3 for R52/M55.
- Future SystemC devices.

These regions may be reserved or documented in M1, but R52/M55 boot is not
required.

## Non-functional requirements

| Requirement | Specification |
| --- | --- |
| Reproducibility | Commands must use explicit output directories and record kernel/Buildroot versions. |
| Debuggability | First boot must produce a console log artifact. |
| Upstream safety | Ubuntu platform flow must stay unchanged unless intentionally refactored later. |
| Minimality | M1 must boot Linux before adding heterogeneous-core complexity. |
| Portability | Prefer standard Buildroot, CMake, QEMU, SystemC, and device tree workflows. |

## Memory map

| Region | Base | Size | Required in M1 | Notes |
| --- | ---: | ---: | --- | --- |
| DRAM | `0x80000000` | 4 GiB | Yes | Existing QBox AArch64 baseline. |
| UART0 | `0x10000000` | 4 KiB | Yes | Linux console. |
| A710 SRAM | `0x00400000` | 1 MiB | No | Reserve in M2. |
| R52 SRAM 0 | `0x00500000` | 2 MiB | No | Reserve in M2/M3. |
| R52 SRAM 1 | `0x00700000` | 2 MiB | No | Reserve in M2/M3. |
| M55 SRAM | `0x00900000` | 1 MiB | No | Reserve in M2/M4. |
| Shared SRAM | `0x00A00000` | 2 MiB | No | Shared mailbox/memory later. |

## Device tree requirements

The M1 DTB must include:

- `/cpus` with 4 Cortex-A710-compatible CPU nodes.
- PSCI node with `method = "smc"` by default.
- `/memory` at `0x80000000` with 4 GiB size.
- GICv3 node matching the QBox platform addresses.
- PL011 UART node at `0x10000000`.
- `/chosen` with bootargs for initramfs boot.

Initial bootargs:

```text
console=ttyAMA0 earlycon=pl011,0x10000000 rdinit=/sbin/init loglevel=8
```

Later ext4 bootargs:

```text
console=ttyAMA0 earlycon=pl011,0x10000000 root=/dev/vda rw rootwait loglevel=8
```

## Buildroot requirements

Recommended layout:

```text
buildroot/external/qbox_arm64/
  Config.in
  external.mk
  board/qbox/a710_soc/
    linux.config
    rootfs_overlay/
    post-build.sh
    post-image.sh
    genimage.cfg
    qbox_a710_soc.dts
  configs/qbox_a710_soc_defconfig
```

Minimum defconfig requirements:

- `BR2_aarch64=y`.
- Internal toolchain initially.
- Linux kernel enabled with AArch64 `Image` output.
- CPIO initramfs enabled for M1.
- BusyBox userspace.
- Optional SSH packages only after console boot works.

## QBox requirements

The Buildroot QBox platform config must:

- Load the Buildroot kernel image at the existing kernel load address.
- Load `qbox_a710_soc.dtb` at the existing DTB load address.
- Load `rootfs.cpio` at the existing initrd load address.
- Load the ARM64 bootloader stub at the existing DRAM base.
- Instantiate 4 x `cpu_arm_cortexA710`.
- Preserve GICv3, timer, PL011, and loader wiring unless boot evidence requires
  a change.

## Verification gates

| Gate | Command or proof | Pass criteria |
| --- | --- | --- |
| Baseline | `bash scripts/check_arm64_boot_lane.sh` | Existing Ubuntu AArch64 lane and Buildroot gap are confirmed. |
| Buildroot artifacts | `ls build/buildroot-a710/images/{Image,qbox_a710_soc.dtb,rootfs.cpio}` | Required files exist and are non-empty. |
| QBox build | `cmake --preset gcc -DLIBQEMU_TARGETS=aarch64 && cmake --build --preset gcc --parallel` | Build exits 0. |
| Linux initramfs boot | `platforms-vp -l platforms/buildroot/conf_aarch64.lua` | BusyBox init or shell reached. |
| Ext4 boot | virtio rootfs boot log | `/dev/vda` rootfs mounts and init completes. |

## Out of scope for M1

- Cortex-R52 boot.
- Cortex-M55 boot.
- Inter-core mailbox.
- Custom SystemC devices.
- Network login.
- Performance modeling or cycle accuracy claims.
