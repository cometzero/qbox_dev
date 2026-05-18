# Source submodules

This workspace keeps large upstream source trees as git submodules instead of
vendoring generated copies.

| Path | Upstream | Pin |
| --- | --- | --- |
| `sources/qbox/` | <https://github.com/quic/qbox.git> | local branch `feature/aarch64_buildroot` |
| `sources/buildroot/` | <https://gitlab.com/buildroot.org/buildroot.git> | `2026.02.1` |
| `sources/linux/` | <https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git> | mainline `master` (`27d128c1cff64c3b8012cc56dd5a1391bb4f1821`) |
| `sources/qemu/` | <https://github.com/quic/qemu.git> | `libqemu-v10.1-v0.13` (`99d1f1559caa661a61ceb07803c2886f429b7be7`) |
| `sources/iree/` | <https://github.com/iree-org/iree.git> | `main` (`b46def4476d709db249406e0ca3b9a59a16a5196`) |
| `sources/hexagon-mlir/` | <https://github.com/qualcomm/hexagon-mlir.git> | `main` (`7a39f6929d934fc5deeb1bf9462ce647d5565e80`) |

Initialize with:

```bash
git submodule update --init --recursive sources/qbox
git submodule update --init sources/buildroot sources/linux sources/qemu sources/iree sources/hexagon-mlir
```

The Linux, Buildroot, and QEMU submodules are configured for full history, not
shallow clones. IREE and Hexagon-MLIR are configured as shallow source
checkouts because the current workspace only needs pinned upstream trees for
Apollo HAL and compiler integration work. If an older shallow checkout already
exists, refresh it with:

```bash
git -C sources/linux config remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*'
git -C sources/linux fetch --unshallow --tags origin
git -C sources/linux fetch origin +refs/heads/master:refs/remotes/origin/master
git -C sources/linux checkout -B mainline-latest origin/master
git -C sources/buildroot config remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*'
git -C sources/buildroot fetch --unshallow --tags origin
git -C sources/qemu config remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*'
git -C sources/qemu fetch --unshallow --tags origin
```

Build ownership:

- `sources/buildroot/` is used for the rootfs/DTB lane only; the QBox defconfig
  intentionally excludes `BR2_LINUX_KERNEL`.
- `sources/linux/` is built by `scripts/build_qbox_linux_arm64.sh` to produce
  the standalone `Image` consumed by QBox.
- `sources/qemu/` is the libqemu/QEMU checkout consumed by
  `scripts/build_qbox_buildroot_platform.sh` through CPM's
  `CPM_libqemu_SOURCE` override, so QEMU/libqemu patches can be made in a
  normal submodule workspace and rebuilt by QBox.
- `sources/iree/` is the upstream IREE checkout reserved for Apollo HAL device
  registry and Buildroot/package integration work. The Apollo Buildroot
  external tree builds the runtime-only `iree-run-module` target from this
  checkout through `BR2_PACKAGE_IREE_RUNTIME=y`; use
  `scripts/build_iree_runtime_buildroot.sh` for a package-only build.
- `sources/hexagon-mlir/` is the upstream Hexagon-MLIR compiler checkout
  reserved for future Apollo Hexagon/Triton/PyTorch lowering experiments.
- Buildroot, Linux, and QBox platform builds use ccache by default:
  - Buildroot cache: `build/ccache/buildroot`
  - Linux cache: `build/ccache/linux`
  - QBox cache: `build/ccache/qbox`
  - Set `QBOX_USE_CCACHE=0` for the Linux/QBox scripts only when debugging
    ccache-specific problems.
