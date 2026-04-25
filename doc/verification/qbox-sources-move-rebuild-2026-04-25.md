# QBox sources/ move rebuild verification - 2026-04-25

Workspace: `/build/qbox_dev`

## Result

PASS. The QBox submodule was moved from repository root `qbox/` to
`sources/qbox/`, `.gitmodules` now points at the new path, and the Buildroot,
standalone Linux, and QBox platform lanes were rebuilt. The bounded run smoke
booted Linux through `/sbin/init` and reached the Buildroot login prompt on
`ttyAMA0`.

`QBOX_BOOT_TIMEOUT=8 scripts/run_qbox_buildroot_boot.sh` returns exit code `124`
because `timeout(1)` stops the otherwise interactive simulation after the login
prompt is already visible. That timeout exit is expected for bounded smoke runs.
Default script execution remains unlimited/interactive when `QBOX_BOOT_TIMEOUT`
is unset or `0`.

## Submodule layout

| Component | Path | Revision |
| --- | --- | --- |
| QBox | `sources/qbox` | `7ece7381b08715372f8984a6b38980df6fd2b821` |
| Buildroot | `sources/buildroot` | `0141ca3fa5302c0c3c583cb898bd3f8792bced69` (`2026.02.1`) |
| Linux | `sources/linux` | `27d128c1cff64c3b8012cc56dd5a1391bb4f1821` (`v7.0-13891-g27d128c1cff6`) |

`.gitmodules` now uses:

```ini
[submodule "qbox"]
	path = sources/qbox
	url = https://github.com/quic/qbox.git
```

The moved submodule gitfile uses `gitdir: ../../.git/modules/qbox`, preserving
the existing local submodule metadata.

## Rebuild commands and evidence

```bash
scripts/check_buildroot_arm64_lane.sh
rm -rf sources/qbox/build
scripts/build_qbox_buildroot_arm64.sh
scripts/build_qbox_linux_arm64.sh
scripts/stage_buildroot_artifacts.sh
scripts/build_qbox_buildroot_platform.sh
set +e; QBOX_BOOT_TIMEOUT=8 scripts/run_qbox_buildroot_boot.sh; rc=$?; set -e
rg -n 'Linux version|Run /sbin/init as init process|qbox-a710 login|Simulation Time' \
  build/verification/qbox-a710-buildroot-boot.log
```

| Check | Result | Evidence |
| --- | --- | --- |
| Buildroot rootfs/DTB rebuild | PASS | `rootfs.cpio` timestamp `2026-04-25 20:42:32 +0900`, size `3809280` bytes; DTB size `2841` bytes |
| Standalone Linux rebuild | PASS | `build/linux-a710/arch/arm64/boot/Image` timestamp `2026-04-25 20:53:55 +0900`, size `42920448` bytes |
| Artifact staging to moved QBox tree | PASS | `sources/qbox/platforms/buildroot/fw/Artifacts/Image.bin`, `rootfs.cpio`, and `qbox_a710_soc.dtb` refreshed |
| QBox clean rebuild | PASS | `sources/qbox/build/platforms-vp` rebuilt and executable; required runtime modules rebuilt under `sources/qbox/build/` |
| QBox boot smoke | PASS | log reaches `Run /sbin/init as init process` and `qbox-a710 login:` |

## ccache verification

| Lane | Evidence |
| --- | --- |
| Buildroot | `scripts/build_qbox_buildroot_arm64.sh` exports `BR2_CCACHE_DIR=/build/qbox_dev/build/ccache/buildroot`; generated config has `BR2_CCACHE=y` |
| Linux | `scripts/build_qbox_linux_arm64.sh` reports `Linux ccache launcher: /usr/bin/ccache` and `Linux ccache dir: /build/qbox_dev/build/ccache/linux` |
| QBox | `sources/qbox/build/CMakeCache.txt` contains `CMAKE_C_COMPILER_LAUNCHER=/usr/bin/ccache` and `CMAKE_CXX_COMPILER_LAUNCHER=/usr/bin/ccache` |

QBox configure output also used ccache wrapper compilers (`/usr/lib/ccache/cc`
and `/usr/lib/ccache/c++`).

## Boot-log proof

Boot log: `build/verification/qbox-a710-buildroot-boot.log`

```text
Linux version 7.0.0-13891-g27d128c1cff6
Run /sbin/init as init process
QBox A710 Buildroot
qbox-a710 login:
Simulation Time: 7.75863SC_SEC
```

The runner now uses a pseudo-TTY by default, including non-interactive Codex/CI
runs, because QBox's stdio-backed UART can observe stdin EOF and stop early
without a PTY. Set `QBOX_BOOT_PTY=0` only when the plain line-buffered path is
explicitly needed.

## Known gaps

- The smoke test stops at the login prompt; it does not perform a manual root
  shell session.
- R52, M55, Zephyr, and future SystemC device integration remain outside this
  verification scope.
