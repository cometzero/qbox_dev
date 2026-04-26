# QBox libqemu Submodule Verification - 2026-04-26

## Result

PASS. The workspace now tracks libqemu/QEMU as the independent git submodule
`sources/qemu`, pinned to the same QBox package-lock tag that the previous CPM
build dependency downloaded (`libqemu-v10.1-v0.13`). The QBox platform build
uses this checkout through CPM's local source override instead of cloning
libqemu into `sources/qbox/build/_deps/libqemu-src`.

## Source revisions

| Source | Path | Revision | Shallow |
| --- | --- | --- | --- |
| QBox | `sources/qbox` | `7ece7381b08715372f8984a6b38980df6fd2b821` (`v6.0.0-28-g7ece7381b087`) | `false` |
| QEMU/libqemu | `sources/qemu` | `99d1f1559caa661a61ceb07803c2886f429b7be7` (`libqemu-v10.1-v0.13`) | `false` |
| Buildroot | `sources/buildroot` | `0141ca3fa5302c0c3c583cb898bd3f8792bced69` (`2026.02.1`) | `false` |
| Linux | `sources/linux` | `27d128c1cff64c3b8012cc56dd5a1391bb4f1821` (`v7.0-13891-g27d128c1cff6`) | `false` |

## Configuration changes verified

- `.gitmodules` registers `sources/qemu` with `shallow = false`.
- `scripts/build_qbox_buildroot_platform.sh` defaults
  `QBOX_LIBQEMU_SRC` to `${repo_root}/sources/qemu`.
- The QBox configure step passes `-DCPM_libqemu_SOURCE=${libqemu_src}`.
- `CCACHE_BASEDIR` is `/build/qbox_dev`, so QBox and the external QEMU checkout
  share a stable ccache base.

## Commands run

```bash
bash -n scripts/build_qbox_buildroot_platform.sh \
  scripts/check_buildroot_arm64_lane.sh \
  scripts/run_qbox_buildroot_boot.sh \
  scripts/build_qbox_buildroot_arm64.sh \
  scripts/build_qbox_linux_arm64.sh \
  scripts/stage_buildroot_artifacts.sh

scripts/check_buildroot_arm64_lane.sh

rm -rf sources/qbox/build
./scripts/build_qbox_buildroot_platform.sh \
  2>&1 | tee build/verification/qbox-libqemu-submodule-rebuild-2026-04-26.log

for i in 1 2; do
  QBOX_BOOT_TIMEOUT=15 \
  QBOX_BOOT_LOG="build/verification/qbox-libqemu-submodule-boot-${i}-2026-04-26.log" \
  ./scripts/run_qbox_buildroot_boot.sh
  rg -n 'Linux version|Run /sbin/init as init process|qbox-a710 login:|Simulation Time' \
    "build/verification/qbox-libqemu-submodule-boot-${i}-2026-04-26.log"
done
```

## Rebuild evidence

| Check | Evidence |
| --- | --- |
| Local libqemu source selected | Build log line contains `CPM: Adding package libqemu@ (/build/qbox_dev/sources/qemu)` |
| QEMU Meson source directory | Build log line contains `Source dir: /build/qbox_dev/sources/qemu` |
| No CPM libqemu download | Build log line contains `No download step for 'qemu'` |
| CMake cache source override | `sources/qbox/build/CMakeCache.txt` contains `CPM_libqemu_SOURCE=/build/qbox_dev/sources/qemu` |
| CMake cache final source dir | `sources/qbox/build/CMakeCache.txt` contains `libqemu_SOURCE_DIR=/build/qbox_dev/sources/qemu` |
| QBox ccache enabled | `CMAKE_C_COMPILER_LAUNCHER=/usr/bin/ccache` and `CMAKE_CXX_COMPILER_LAUNCHER=/usr/bin/ccache` in `CMakeCache.txt` |
| Runtime artifacts rebuilt | `sources/qbox/build/platforms-vp`, `cpu_arm_cortexA710.so`, `arm_gicv3.so`, `uart-pl011.so`, `router.so` exist |
| libqemu artifact rebuilt | `sources/qbox/build/_deps/libqemu-build/qemu-prefix/lib/libqemu-system-aarch64.so` exists (`114M`) |
| QEMU checkout clean after build | `git -C sources/qemu status --short` produced no output |
| QBox checkout clean after build | `git -C sources/qbox status --short` produced no output |

Build log:

- `build/verification/qbox-libqemu-submodule-rebuild-2026-04-26.log`

## Boot evidence

Both runs intentionally used `QBOX_BOOT_TIMEOUT=15`, so exit status `124` means
`timeout(1)` stopped an otherwise interactive QBox session after the login prompt
was reached. This is expected for bounded CI/Codex smoke runs.

| Run | Log | Key markers |
| --- | --- | --- |
| 1 | `build/verification/qbox-libqemu-submodule-boot-1-2026-04-26.log` | `Linux version` at line 13, `Run /sbin/init as init process` at line 254, `qbox-a710 login:` at line 268, `Simulation Time: 14.8523SC_SEC` |
| 2 | `build/verification/qbox-libqemu-submodule-boot-2-2026-04-26.log` | `Linux version` at line 13, `Run /sbin/init as init process` at line 254, `qbox-a710 login:` at line 268, `Simulation Time: 14.8702SC_SEC` |

## Notes

- The QEMU Meson build may fetch QEMU wrap fallback projects such as
  `keycodemapdb`, `rpclib`, or `virclrenderer` under the QEMU source tree during
  configure. The checkout remained clean according to `git status --short`.
- No QEMU code changes were made in this step; the new submodule exists so
  future QEMU/libqemu changes can be edited, rebuilt, and reviewed normally.
