# QBox Buildroot ARM64 boot verification - 2026-04-25

## Result

PASS for Milestone 1 boot smoke: QBox loads a standalone Linux `Image` built
from `sources/linux`, a Buildroot-generated DTB/rootfs, brings up 4 Cortex-A710
CPUs, starts `/sbin/init`, and reaches the Buildroot login prompt on `ttyAMA0`.

The run command is intentionally timeout-bounded; exit code `124` means the
simulation was stopped after the login prompt was observed.

## Source pins

| Source | Path | Pin |
| --- | --- | --- |
| QBox | `qbox/` | `7ece7381b08715372f8984a6b38980df6fd2b821` on `feature/aarch64_buildroot` |
| Buildroot | `sources/buildroot/` | `2026.02.1` / `0141ca3fa5302c0c3c583cb898bd3f8792bced69` |
| Linux | `sources/linux/` | `v7.0` / `028ef9c96e96197026887c0f092424679298aae8` |

## Artifact contract

| Artifact | Producer | Staged path | Size |
| --- | --- | --- | ---: |
| Linux Image | `scripts/build_qbox_linux_arm64.sh` from `sources/linux` | `qbox/platforms/buildroot/fw/Artifacts/Image.bin` | 41445888 |
| DTB | Buildroot post-image hook | `qbox/platforms/buildroot/fw/Artifacts/qbox_a710_soc.dtb` | 2841 |
| initramfs | Buildroot rootfs-only build | `qbox/platforms/buildroot/fw/Artifacts/rootfs.cpio` | 3809280 |

Buildroot kernel build is intentionally disabled. Verification evidence:

```text
# BR2_LINUX_KERNEL is not set
```

## Commands executed

```bash
bash -n scripts/build_qbox_buildroot_arm64.sh \
  scripts/build_qbox_linux_arm64.sh \
  scripts/build_qbox_buildroot_platform.sh \
  scripts/stage_buildroot_artifacts.sh \
  scripts/run_qbox_buildroot_boot.sh \
  scripts/check_buildroot_arm64_lane.sh \
  buildroot/external/qbox_arm64/board/qbox/a710_soc/post-build.sh \
  buildroot/external/qbox_arm64/board/qbox/a710_soc/post-image.sh

bash scripts/check_buildroot_arm64_lane.sh
bash scripts/check_arm64_boot_lane.sh
scripts/build_qbox_buildroot_arm64.sh --config-only
scripts/build_qbox_buildroot_arm64.sh
scripts/build_qbox_linux_arm64.sh --config-only
scripts/build_qbox_linux_arm64.sh
scripts/stage_buildroot_artifacts.sh
scripts/build_qbox_buildroot_platform.sh
QBOX_BOOT_TIMEOUT=35 scripts/run_qbox_buildroot_boot.sh
```

## Boot-log proof

Boot log: `build/verification/qbox-a710-buildroot-boot.log`

| Check | Status | Evidence |
| --- | --- | --- |
| Linux kernel started | PASS | `Linux version` present |
| 4 x A710 CPUs online | PASS | `SMP: Total of 4 processors activated.` |
| PL011 console bound | PASS | `ttyAMA0 at MMIO 0x10000000` |
| initramfs userspace reached | PASS | `Run /sbin/init as init process`, `qbox-a710 login:` |

Relevant excerpt:

```text
SMP: Total of 4 processors activated.
10000000.serial: ttyAMA0 at MMIO 0x10000000 (irq = 13, base_baud = 0) is a PL011 rev1
Run /sbin/init as init process
Starting syslogd: OK
Starting klogd: OK
Starting network: OK
QBox A710 Buildroot
qbox-a710 login:
```

## Notes and blockers

- No M1 boot blocker remains after adding early `/dev` fallback nodes and an
  explicit initramfs `devtmpfs` mount before `/dev/pts` setup.
- The boot smoke is not an interactive login test; it stops at the login prompt.
- R52, M55, ext4 rootfs, and SystemC device additions remain deferred follow-up
  milestones per `doc/spec/`.
