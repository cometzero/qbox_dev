# Read-only QBox Buildroot ARM64 boot-planning lane report

Date: 2026-04-25
Workspace root: `/build/qbox_dev`
Repo: `/build/qbox_dev/qbox`
Repo commit: `27adc6d59f0782bcbbb29b388de6d6971f1f1f7c`
Task: `Read-only QBox Buildroot ARM64 SoC boot planning`

## Executive summary

I reviewed the current ARM64 boot lane and documented what already exists
versus what is still missing for a Buildroot-oriented SoC boot plan.

Current state:
- QBox already has a documented Ubuntu AArch64 boot lane.
- The AArch64 platform boots a prebuilt Linux image, DTB, and initrd with a
  generated ARM64 bootloader shim.
- Buildroot support is only mentioned indirectly in networking/SSH setup notes;
  there is no dedicated Buildroot boot-lane guide or image-generation flow.

## Sources reviewed

- `README.md`
- `docs/platforms/ubuntu.md`
- `docs/networking.md`
- `platforms/ubuntu/conf_aarch64.lua`
- `platforms/ubuntu/fw/arm64_bootloader.lua`
- `platforms/ubuntu/fw/build_linux_dist_image.sh`

## Lane findings

### 1) The documented boot path is Ubuntu-centric, not Buildroot-centric

The top-level README and Ubuntu platform guide both describe the same
AArch64 boot flow:

- build a Linux rootfs image with
  `platforms/ubuntu/fw/build_linux_dist_image.sh`
- build QBox with `LIBQEMU_TARGETS=aarch64`
- run `build/platforms/platforms-vp` with
  `platforms/ubuntu/conf_aarch64.lua`

Relevant evidence:
- `README.md:161-175`
- `docs/platforms/ubuntu.md:6-86`

That means the current first-class lane is “Ubuntu on AArch64”, not
“Buildroot on ARM64”.

### 2) The AArch64 platform loads fixed boot artifacts at fixed addresses

The AArch64 Lua configuration hardcodes the boot memory map:

- RAM base: `0x80000000`
- kernel load: `0x81200000`
- DTB load: `0x87600000`
- initrd load: `0x8A800000`

It then loads:

- `fw/Artifacts/Image.bin`
- `fw/Artifacts/ubuntu.dtb`
- `fw/Artifacts/image_ext4_initrd.img`
- the generated `arm64_bootloader.lua` blob

Relevant evidence:
- `platforms/ubuntu/conf_aarch64.lua:16-22`
- `platforms/ubuntu/conf_aarch64.lua:144-156`
- `platforms/ubuntu/fw/arm64_bootloader.lua:1-27`

This is a clean, explicit boot chain, but it is still tied to the Ubuntu
artifact names and layout.

### 3) Buildroot exists only as a generic networking/SSH note

The networking guide includes Buildroot SSH and root-login settings:

- `BR2_PACKAGE_OPENSSH`
- `BR2_TARGET_GENERIC_ROOT_PASSWD`
- `PermitRootLogin yes`
- static `eth0` setup

Relevant evidence:
- `docs/networking.md:43-89`

That content is useful for a Buildroot guest, but it is disconnected from
the platform boot docs. There is no matching Buildroot boot guide, no
Buildroot image recipe, and no integration note that says where those
settings belong in the boot lane.

### 4) The image-generation script is Ubuntu/Fedora-oriented

`build_linux_dist_image.sh` is explicitly scoped to Ubuntu and Fedora
distributions and generates Ubuntu-named artifacts:

- `image.ext4`
- `image.ext4.initrd`
- `ubuntu.dts`
- `ubuntu.dtb`

Relevant evidence:
- `platforms/ubuntu/fw/build_linux_dist_image.sh:16-50`
- `platforms/ubuntu/fw/build_linux_dist_image.sh:143-166`

That script is a good host-side entry point for the current lane, but it is
not a Buildroot pipeline and should not be presented as one.

## Code-quality notes

These are not blockers, but they matter for future boot-lane work:

1. `platforms/ubuntu/conf_aarch64.lua` uses hardcoded address and topology
   values. That keeps the lane explicit, but any future ARM64 boot variant
   will need the same constants documented carefully.
2. `platforms/ubuntu/fw/build_linux_dist_image.sh` mixes dependency setup,
   distro selection, artifact generation, and DT creation in one script.
   That is workable for the Ubuntu lane, but it becomes a documentation risk
   if a Buildroot lane is added later and people assume this script covers it.
3. The repo currently has a clear Ubuntu AArch64 quick-start path, but no
   peer page that says “this is how to boot a Buildroot ARM64 guest”.

## Recommendations

If the next boot-planning step is to add a Buildroot lane, the lowest-risk
documentation work is:

1. add a dedicated `docs/platforms/buildroot-arm64.md` page or equivalent
2. document the guest image artifact names expected by the ARM64 platform
3. cross-link the SSH/networking setup notes from the new Buildroot page
4. keep the Ubuntu docs unchanged except for optional cross-references

## Status

Documentation updated with this lane report.
No source code changes were required for this review task.
