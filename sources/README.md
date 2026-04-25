# Source submodules

This workspace keeps large upstream source trees as git submodules instead of
vendoring generated copies.

| Path | Upstream | Pin |
| --- | --- | --- |
| `qbox/` | <https://github.com/quic/qbox.git> | local branch `feature/aarch64_buildroot` |
| `sources/buildroot/` | <https://gitlab.com/buildroot.org/buildroot.git> | `2026.02.1` |
| `sources/linux/` | <https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git> | mainline `master` (`27d128c1cff64c3b8012cc56dd5a1391bb4f1821`) |

Initialize with:

```bash
git submodule update --init --recursive qbox sources/buildroot sources/linux
```

The Linux and Buildroot submodules are configured for full history, not shallow
clones. If an older shallow checkout already exists, refresh it with:

```bash
git -C sources/linux config remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*'
git -C sources/linux fetch --unshallow --tags origin
git -C sources/linux fetch origin +refs/heads/master:refs/remotes/origin/master
git -C sources/linux checkout -B mainline-latest origin/master
git -C sources/buildroot config remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*'
git -C sources/buildroot fetch --unshallow --tags origin
```

Build ownership:

- `sources/buildroot/` is used for the rootfs/DTB lane only; the QBox defconfig
  intentionally excludes `BR2_LINUX_KERNEL`.
- `sources/linux/` is built by `scripts/build_qbox_linux_arm64.sh` to produce
  the standalone `Image` consumed by QBox.
- Buildroot, Linux, and QBox platform builds use ccache by default:
  - Buildroot cache: `build/ccache/buildroot`
  - Linux cache: `build/ccache/linux`
  - QBox cache: `build/ccache/qbox`
  - Set `QBOX_USE_CCACHE=0` for the Linux/QBox scripts only when debugging
    ccache-specific problems.
