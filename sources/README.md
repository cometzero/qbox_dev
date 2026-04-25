# Source submodules

This workspace keeps large upstream source trees as git submodules instead of
vendoring generated copies.

| Path | Upstream | Pin |
| --- | --- | --- |
| `qbox/` | <https://github.com/quic/qbox.git> | local branch `feature/aarch64_buildroot` |
| `sources/buildroot/` | <https://gitlab.com/buildroot.org/buildroot.git> | `2026.02.1` |
| `sources/linux/` | <https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git> | `v7.0` (`028ef9c96e96197026887c0f092424679298aae8`) |

Initialize with:

```bash
git submodule update --init --recursive qbox sources/buildroot sources/linux
```

Build ownership:

- `sources/buildroot/` is used for the rootfs/DTB lane only; the QBox defconfig
  intentionally excludes `BR2_LINUX_KERNEL`.
- `sources/linux/` is built by `scripts/build_qbox_linux_arm64.sh` to produce
  the standalone `Image` consumed by QBox.
