# Read-only QBox Buildroot ARM64 boot planning lane report

Date: 2026-04-25

## Scope

I inspected the QBox repository at `/build/qbox_dev/sources/qbox` for the ARM64 boot
path that is available in this workspace and checked whether a repo-native
Buildroot lane already exists.

## Findings

### 1) The implemented ARM64 lane is Ubuntu-based

- `platforms/CMakeLists.txt` selects `platforms/ubuntu/conf_${UBUNTU_ARCH}.lua`
  when the Ubuntu-specific `configs/fw/8775/bsp/lnx/ubuntu/conf.lua` fallback
  is not present.
- This checkout does not contain `configs/fw/8775/bsp/lnx/ubuntu/conf.lua`, so
  the active ARM64 platform config is `platforms/ubuntu/conf_aarch64.lua`.
- `platforms/ubuntu/fw/build_linux_dist_image.sh` is the rootfs/image
  generator used by that lane.
- The repo docs advertise one quick-start command per architecture:
  AArch64 in `README.md` and RISC-V 64 in `docs/platforms/ubuntu.md`.

### 2) The AArch64 boot contract is explicit

`platforms/ubuntu/conf_aarch64.lua` loads:

- kernel image at `INITIAL_DDR_SPACE + 0x01200000`
- DTB at `INITIAL_DDR_SPACE + 0x07600000`
- initrd at `INITIAL_DDR_SPACE + 0x0A800000`
- the AArch64 bootloader stub at `INITIAL_DDR_SPACE`

This makes the boot path deterministic and easy to validate.

### 3) Buildroot support is documentation-only in this checkout

The only Buildroot-specific material I found is the networking example in
`docs/networking.md`, which shows Buildroot package and SSH configuration
snippets. I did not find a dedicated Buildroot image pipeline or platform
config in this repository.

## Lane finding

**Current lane:** Ubuntu AArch64 virtual platform boot flow.

**Not present in-repo:** a dedicated Buildroot ARM64 SoC boot lane.

## Verification artifact

I added `scripts/check_arm64_boot_lane.sh` as a repeatable repository check for
the above observations. It points at `/build/qbox_dev/sources/qbox` by default and
verifies:

- the Ubuntu AArch64 platform config exists
- the AArch64 bootloader/load-address contract exists
- the Buildroot-related documentation snippet exists
- the Ubuntu fallback config path is absent in this checkout

## Suggested next step

If the Buildroot lane is still desired, the next implementation step should be
to decide whether to:

1. reuse `platforms/ubuntu/conf_aarch64.lua` and swap in a Buildroot image
   pipeline, or
2. add a new ARM64 platform config and image generator specific to Buildroot.

## Verification snapshot

The repeatable check script in `scripts/check_arm64_boot_lane.sh` passed against
`/build/qbox_dev/sources/qbox` on 2026-04-25, confirming the AArch64 Ubuntu lane and
the absence of a repo-native Buildroot ARM64 boot lane in this checkout.
This was a static planning pass; I did not run the full QBox simulator or a
Buildroot image build because the task only asked for lane discovery and
reporting.
