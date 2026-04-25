# QBox mainline Linux and ccache verification

Date: 2026-04-25
Workspace: `/build/qbox_dev`

## Scope

This verification records the update from the Linux `v7.0` tag to the latest
mainline `master` commit available from `torvalds/linux.git` during this run,
full-history submodule refresh, and ccache enablement for Buildroot, standalone
Linux, and QBox platform builds.

## Source revisions

| Component | Path | Revision / history state |
| --- | --- | --- |
| QBox | `sources/qbox/` | `7ece7381b08715372f8984a6b38980df6fd2b821`, full history |
| Buildroot | `sources/buildroot/` | `2026.02.1` / `0141ca3fa5302c0c3c583cb898bd3f8792bced69`, full history |
| Linux | `sources/linux/` | mainline `master` / `27d128c1cff64c3b8012cc56dd5a1391bb4f1821`, full history |

Linux kernel release string after config:

```text
7.0.0-13891-g27d128c1cff6
```

## ccache policy

| Build lane | Mechanism | Default cache path |
| --- | --- | --- |
| Buildroot rootfs/DTB | `BR2_CCACHE=y` plus `BR2_CCACHE_DIR` exported by script | `build/ccache/buildroot` |
| Standalone Linux Image | `CROSS_COMPILE="/usr/bin/ccache <toolchain-prefix>"` | `build/ccache/linux` |
| QBox CMake platform | `CMAKE_C_COMPILER_LAUNCHER=/usr/bin/ccache`, `CMAKE_CXX_COMPILER_LAUNCHER=/usr/bin/ccache` | `build/ccache/qbox` |

## Verification commands

```bash
bash -n scripts/build_qbox_buildroot_arm64.sh \
  scripts/build_qbox_linux_arm64.sh \
  scripts/build_qbox_buildroot_platform.sh \
  scripts/check_buildroot_arm64_lane.sh

scripts/check_buildroot_arm64_lane.sh
scripts/build_qbox_buildroot_arm64.sh --config-only
scripts/build_qbox_linux_arm64.sh --config-only
scripts/build_qbox_buildroot_platform.sh --config-only
make -s -C sources/linux O=/build/qbox_dev/build/linux-a710 \
  kernelrelease ARCH=arm64 \
  CROSS_COMPILE="/usr/bin/ccache /build/qbox_dev/build/buildroot-a710/host/bin/aarch64-buildroot-linux-gnu-"
rg -n 'CMAKE_(C|CXX)_COMPILER_LAUNCHER' sources/qbox/build/CMakeCache.txt
```

## Results

| Check | Result | Evidence |
| --- | --- | --- |
| Submodule full history | PASS | `sources/linux` and `sources/buildroot` both report `false` from `git rev-parse --is-shallow-repository` |
| Linux latest mainline tree | PASS | `sources/linux` HEAD is `27d128c1cff64c3b8012cc56dd5a1391bb4f1821`, matching `refs/heads/master` from `torvalds/linux.git` during this run |
| Buildroot ccache config | PASS | `build/buildroot-a710/.config` contains `BR2_CCACHE=y`; build script exports `BR2_CCACHE_DIR=/build/qbox_dev/build/ccache/buildroot` |
| Linux ccache config | PASS | `scripts/build_qbox_linux_arm64.sh --config-only` reports `/usr/bin/ccache` and `build/ccache/linux` |
| QBox ccache config | PASS | `sources/qbox/build/CMakeCache.txt` contains both C and CXX compiler launcher entries set to `/usr/bin/ccache` |
| Kernel build ownership | PASS | `scripts/check_buildroot_arm64_lane.sh` still verifies `BR2_LINUX_KERNEL` is disabled and Linux Image is built from `sources/linux` |

## Notes

- Buildroot 2026.02.1 still exposes Linux headers options up to 6.19 in its
  Kconfig. The rootfs/toolchain header selection was not changed here; the
  runtime kernel source moved independently to latest mainline `master` through
  the standalone `sources/linux` submodule.
- The follow-up move/rebuild pass reran the full QBox runtime build and boot
  smoke after relocating QBox to `sources/qbox/`; see
  `doc/verification/qbox-sources-move-rebuild-2026-04-25.md`.
