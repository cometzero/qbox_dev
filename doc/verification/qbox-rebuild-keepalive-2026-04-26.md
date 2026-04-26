# QBox Buildroot A710 Rebuild and Boot Stability Verification (2026-04-26)

## Summary

A clean QBox rebuild reproduced the cold post-rebuild early-exit failure: the
first boot stopped around the early `hw-breakpoint`/cpuidle phase before
Buildroot userspace. The Buildroot AArch64 platform now instantiates QBox's
existing `keep_alive` SystemC component, and the platform build/run scripts
require the matching `keep_alive.so` module.

After the change, a clean rebuild completed with local `sources/qemu`/libqemu
and ccache. Three consecutive post-rebuild boot smokes reached `/sbin/init` and
the `qbox-a710 login:` prompt; each run was stopped only by the intentional
20-second verification timeout.

## Changed runtime contract

- `sources/qbox/platforms/buildroot/conf_aarch64.lua`
  - Adds `keep_alive_0 = { moduletype = "keep_alive"; }`.
- `scripts/build_qbox_buildroot_platform.sh`
  - Builds the `keep_alive` dynamic module with the Buildroot platform target
    set.
- `scripts/run_qbox_buildroot_boot.sh`
  - Treats `keep_alive.so` as a required runtime module before launching QBox.
- `scripts/check_buildroot_arm64_lane.sh`
  - Checks the keep-alive platform, build, and run-script contract.

## Rebuild evidence

Command:

```sh
rm -rf sources/qbox/build
./scripts/build_qbox_buildroot_platform.sh \
  2>&1 | tee build/verification/qbox-rebuild-verify-after-keepalive-2026-04-26.log
```

Selected evidence from
`build/verification/qbox-rebuild-verify-after-keepalive-2026-04-26.log`:

- `-- CPM: Adding package libqemu@ (/build/qbox_dev/sources/qemu)`
- `No download step for 'qemu'`
- `Source dir: /build/qbox_dev/sources/qemu`
- `[100%] Built target keep_alive`
- `QBox Buildroot platform runtime built in /build/qbox_dev/sources/qbox/build`
- `QBox ccache launcher: /usr/bin/ccache`
- `QBox ccache dir: /build/qbox_dev/build/ccache/qbox`
- `QBox ccache basedir: /build/qbox_dev`

## Boot smoke evidence

Command shape:

```sh
for i in 1 2 3; do
  QBOX_BOOT_TIMEOUT=20 \
  QBOX_BOOT_LOG="build/verification/qbox-keepalive-boot-${i}-2026-04-26.log" \
    ./scripts/run_qbox_buildroot_boot.sh
  # Expected exit code: 124, because the verification timeout intentionally
  # stops the otherwise interactive/unlimited runner after login is reached.
done
```

Results:

| Run | Exit | Init marker | Login marker | Stop reason |
| --- | ---: | --- | --- | --- |
| 1 | 124 | `[    1.434952] Run /sbin/init as init process` | `qbox-a710 login:` | 20s verification timeout |
| 2 | 124 | `[    1.355201] Run /sbin/init as init process` | `qbox-a710 login:` | 20s verification timeout |
| 3 | 124 | `[    1.401404] Run /sbin/init as init process` | `qbox-a710 login:` | 20s verification timeout |

Log files:

- `build/verification/qbox-keepalive-boot-1-2026-04-26.log`
- `build/verification/qbox-keepalive-boot-2-2026-04-26.log`
- `build/verification/qbox-keepalive-boot-3-2026-04-26.log`

## Conclusion

The cold post-rebuild early-exit path is fixed for the current A710 Buildroot
lane. The default `scripts/run_qbox_buildroot_boot.sh` behavior remains
unlimited and interactive when `QBOX_BOOT_TIMEOUT` is unset or `0`; bounded smoke
verification should set `QBOX_BOOT_TIMEOUT` explicitly.
