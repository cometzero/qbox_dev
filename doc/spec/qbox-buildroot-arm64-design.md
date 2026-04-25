# Design: QBox Buildroot ARM64 SoC Boot Lane

## Design principles

1. Reuse the proven AArch64 boot contract.
2. Keep Buildroot artifacts separate from Ubuntu artifacts.
3. Boot Linux before modeling the full heterogeneous SoC.
4. Prefer explicit generated artifacts over implicit script side effects.
5. Leave future SystemC and RTOS integration points visible but inactive.

## High-level architecture

```text
+------------------------+        +-------------------------------+
| sources/linux          |        | QBox platform/buildroot       |
| git submodule          |        |                               |
|  + linux.config        | -----> |  fw/Artifacts/Image.bin       |
+------------------------+        |                               |
                                  |  conf_aarch64.lua             |
+------------------------+        |  fw/Artifacts/qbox_a710.dtb   |
| Buildroot external     | -----> |  fw/Artifacts/rootfs.cpio     |
| rootfs/DTB only        |        |                               |
|  qbox_a710_defconfig   |        |                               |
|  qbox_a710_soc.dts     |        |                               |
|  rootfs overlay        |        |                               |
+------------------------+        +---------------+---------------+
                                                |
                                                v
                              +-----------------+-----------------+
                              | QBox platforms-vp                 |
                              | 4 x Cortex-A710 + GICv3 + UART0  |
                              | DRAM 4 GiB + loader              |
                              +-----------------+-----------------+
                                                |
                                                v
                              +-----------------+-----------------+
                              | Linux kernel + Buildroot initramfs|
                              | PL011 console / BusyBox proof     |
                              +-----------------------------------+
```

## Component responsibilities

| Component | Responsibility |
| --- | --- |
| `sources/linux` submodule | Build the AArch64 Linux `Image` outside Buildroot. |
| Buildroot external tree | Build rootfs/DTB artifacts and later ext4 rootfs; it must not build the kernel. |
| QBox Buildroot platform | Consume the staged Linux + Buildroot artifacts and model the M1 hardware subset. |
| QBox loader | Place kernel, DTB, initramfs, and bootloader at fixed addresses. |
| PL011 UART | Provide first boot console. |
| GICv3/timer | Provide Linux interrupt and timer services. |
| `router` / `gs_memory` | Carry current and future TLM memory/device mappings. |

## Boot sequence

1. Buildroot produces `qbox_a710_soc.dtb` and `rootfs.cpio` only.
2. The standalone Linux script builds `Image` from `sources/linux`.
3. A staging step copies or symlinks those artifacts into
   `qbox/platforms/buildroot/fw/Artifacts/`.
4. `platforms-vp` loads `platforms/buildroot/conf_aarch64.lua`.
5. The QBox loader writes:
   - kernel to `_KERNEL64_LOAD_ADDR`.
   - DTB to `_DTB_LOAD_ADDR`.
   - initramfs to `_INITRD_LOAD_ADDR`.
   - bootloader to `INITIAL_DDR_SPACE`.
6. CPU0 starts at the bootloader entry.
7. PSCI brings up secondary A710 cores if the kernel and DTB agree.
8. Linux prints logs to PL011 UART0.
9. Linux mounts initramfs and starts BusyBox init.

## QBox platform design

The first Buildroot platform should be a copy-derived sibling of the Ubuntu
AArch64 platform:

```text
qbox/platforms/buildroot/conf_aarch64.lua
```

Initial edits from the Ubuntu baseline:

| Existing Ubuntu field | Buildroot M1 value |
| --- | --- |
| `ARM_NUM_CPUS = 8` | `ARM_NUM_CPUS = 4` |
| `cpu_arm_cortexA76` | `cpu_arm_cortexA710` |
| `fw/Artifacts/ubuntu.dtb` | `fw/Artifacts/qbox_a710_soc.dtb` |
| `fw/Artifacts/image_ext4_initrd.img` | `fw/Artifacts/rootfs.cpio` |
| Ubuntu doc/script assumptions | Buildroot-specific staging script or target |

Keep initially:

- `INITIAL_DDR_SPACE = 0x80000000`.
- Existing kernel/DTB/initrd load offsets.
- PL011 UART0 at `0x10000000`.
- GICv3 and timer interrupt wiring.
- `LIBQEMU_TARGETS=aarch64`.

## Buildroot and Linux source design

Use `BR2_EXTERNAL` so the Buildroot board support remains project-controlled
without vendoring all Buildroot source into QBox. Buildroot owns the rootfs and
DTB post-image step only; Linux owns kernel image generation from the separate
`sources/linux` submodule.

Recommended build command shape:

```bash
scripts/build_qbox_buildroot_arm64.sh
scripts/build_qbox_linux_arm64.sh
```

Equivalent ownership:

```text
build/buildroot-a710/images/rootfs.cpio        # Buildroot
build/buildroot-a710/images/qbox_a710_soc.dtb # Buildroot post-image hook
build/linux-a710/arch/arm64/boot/Image        # sources/linux submodule
```

Artifact staging should be explicit:

```bash
install -D build/linux-a710/arch/arm64/boot/Image \
  qbox/platforms/buildroot/fw/Artifacts/Image.bin
install -D build/buildroot-a710/images/qbox_a710_soc.dtb \
  qbox/platforms/buildroot/fw/Artifacts/qbox_a710_soc.dtb
install -D build/buildroot-a710/images/rootfs.cpio \
  qbox/platforms/buildroot/fw/Artifacts/rootfs.cpio
```

## Heterogeneous SoC design path

### M2: reserved memory topology

Add reserved memory and comments before booting RTOS cores. This makes the
memory contract visible to Linux and future developers.

### M3: Cortex-R52 domain

Start with standalone Zephyr boot on R52 before Linux integration.

Design questions to resolve in M3:

- Separate QEMU instance vs shared QEMU instance.
- SRAM-only boot image layout.
- UART addresses and interrupt lines.
- Shared SRAM mailbox ownership.

### M4: Cortex-M55 domain

Use the existing Cortex-M55 component family and the prior Cortex-M55 remote
platform experience. Boot standalone Zephyr first.

### M5: SystemC devices

Use existing router and memory patterns:

- `router` for address decode.
- `gs_memory` for SRAM/shared RAM.
- `reg_router` or a dedicated component for register banks.
- `pass` or explicit TLM sockets for bridge/pass-through cases.

## Failure-mode design

| Failure | Debug path |
| --- | --- |
| No UART output | Verify PL011 address, DTB `stdout-path`, and bootloader entry. |
| Kernel decompresses then hangs | Check GIC/timer DTB nodes and PSCI method. |
| Secondary CPUs fail | Check CPU nodes, `enable-method`, PSCI conduit, and `mp_affinity`. |
| Initramfs not mounted | Check initrd load address, size, and bootargs. |
| Virtio block missing | Keep ext4 out of M1; add after initramfs proof. |

## Design decision record

| Decision | Rationale |
| --- | --- |
| New Buildroot platform lane | Prevents Buildroot work from breaking the existing Ubuntu lane. |
| Initramfs first | Removes block-device variables from first boot debug. |
| 4 x A710 in M1 | Matches user target while staying inside Linux application-cluster scope. |
| R52/M55 deferred | Avoids mixing RTOS and heterogeneous-core modeling with initial Linux bring-up. |
| Artifact staging explicit | Makes generated files auditable and reproducible. |
| Linux as source submodule | Keeps kernel source/version control independent from Buildroot rootfs generation. |
