# Read-only QBox Buildroot ARM64 lane findings

Date: 2026-04-25
Workspace root: `/build/qbox_dev`
Repo root: `/build/qbox_dev/qbox`
Task: read-only QBox Buildroot ARM64 SoC boot planning

## Executive summary

This checkout already contains a working AArch64 Linux boot path, but it is
centered on the Ubuntu platform flow rather than a Buildroot board tree. I did
not find a Buildroot-specific external tree, defconfig, or image pipeline to
extend directly, so the correct next step is to treat Buildroot support as a
new lane rather than a small patch on an existing Buildroot implementation.

## What exists today

### AArch64 boot path is already modeled

- `qbox/platforms/ubuntu/conf_aarch64.lua` wires the AArch64 platform:
  - `cpu_arm_cortexA76`
  - `arm_gicv3`
  - `psci_conduit = "smc"` with `hvc` for KVM
  - kernel, DTB, and initrd load addresses
  - virtio block and network plumbing
- `qbox/platforms/ubuntu/fw/arm64_bootloader.lua` provides the AArch64
  bootloader stub.
- `qbox/platforms/ubuntu/fw/ubuntu-dts-arm64.template` provides the device
  tree template with PSCI and CPU enable-method wiring.

### Artifact generation already exists for Linux images

- `qbox/platforms/ubuntu/fw/build_linux_dist_image.sh` builds:
  - kernel `Image.bin`
  - ext4 rootfs `image_ext4.img`
  - initramfs `image_ext4_initrd.img`
  - generated DTB/ DTS artifacts
- `qbox/docs/platforms/ubuntu.md` documents the same flow and shows the
  `aarch64` and `riscv64` runtime entry points.

### Build-system hooks already expose the AArch64 path

- `qbox/platforms/CMakeLists.txt` selects `LIBQEMU_TARGETS=aarch64` by default
  for the Ubuntu path and defines the `ubuntu` custom target.
- `qbox/CMakePresets.json` includes `aarch64` in the default
  `LIBQEMU_TARGETS` list.
- `qbox/README.md` includes an AArch64 Ubuntu quick-start that matches the
  platform wiring above.

## What is missing for Buildroot ARM64

I did not find any of the following in this checkout:

- a `buildroot/` tree or `BR2_EXTERNAL` integration
- an ARM64 Buildroot defconfig
- Buildroot-specific post-build/post-image scripts
- Buildroot boot docs for QBox
- a Buildroot boot smoke test or CI hook

The only Buildroot reference in the repo is a generic networking doc section
(`qbox/docs/networking.md`) that lists SSH and root password settings. That is a
configuration hint, not a platform implementation.

## Lane findings

### Lane 1: Buildroot image pipeline

**Goal:** define how Buildroot will produce the guest kernel, rootfs, DTB, and
any initrd or disk image that the QBox platform consumes.

**Current state:** no Buildroot artifact pipeline exists in the repo.

**Implication:** this lane needs a new Buildroot external tree or a new board
package, not just a CMake tweak.

### Lane 2: Boot ABI / handoff contract

**Goal:** lock down the boot contract between firmware, kernel, and platform
model.

**Current state:** the Ubuntu AArch64 path already uses a clear contract:

- RAM base: `0x80000000`
- kernel load: `0x81200000`
- DTB load: `0x87600000`
- initrd load: `0x8A800000`
- PSCI conduit: `smc` or `hvc` depending on acceleration mode

**Implication:** a Buildroot ARM64 plan can reuse this contract as the initial
baseline, but the Buildroot image format and kernel/rootfs generation must be
validated against it.

### Lane 3: Platform wiring

**Goal:** decide whether Buildroot support should reuse the Ubuntu platform
definition or land as a separate platform configuration.

**Current state:** the only AArch64 platform entry point is
`qbox/platforms/ubuntu/conf_aarch64.lua`.

**Implication:** the safest path is a new Buildroot-specific platform config or
an explicitly named overlay so the Ubuntu flow stays intact.

### Lane 4: Verification

**Goal:** define a reproducible boot smoke test.

**Current state:** the repo documents Ubuntu boot, but not Buildroot boot.

**Implication:** the first verification artifact should be a boot-to-console
smoke test that proves the Buildroot guest reaches userspace with the expected
console and storage/network devices.

## Recommended next feasible task

If this work continues, the next best step is to create a Buildroot-specific
boot planning artifact that answers these questions:

1. Which Buildroot board or external tree owns ARM64 image generation?
2. Which kernel, DTB, rootfs, and optional initrd artifacts are consumed by the
   QBox runtime?
3. Does the Buildroot flow reuse the current AArch64 addresses and PSCI setup,
   or does it need a different boot stub?
4. What is the minimum boot smoke test for console/login proof?

## Notes

- I kept the scope read-only with respect to the QBox submodule.
- No source files were modified in `qbox/`; this report lives in the workspace
  `doc/` area.
