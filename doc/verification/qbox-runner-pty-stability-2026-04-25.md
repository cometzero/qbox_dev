# QBox boot runner PTY stability verification - 2026-04-25

Workspace: `/build/qbox_dev`

## Symptom

Immediately after rebuilding QBox, the first one or two invocations of
`./scripts/run_qbox_buildroot_boot.sh` could stop during early kernel boot around
`cpuidle` / `hw-breakpoint` and print only the SystemC summary:

```text
[    0.535509] thermal_sys: Registered thermal governor 'power_allocator'
[    0.538721] cpuidle: using governor menu
[    0.544590] hw-breakpoint: found 6 breakpoint and 4 watchpoint registers.
Simulation Time: 1.08259SC_SEC
Simulation Duration: 1s (Wall Clock)
```

This was not a Linux panic. The QBox process exited normally with command exit
code `0`, before `/sbin/init` or the login prompt.

## Root cause

The Buildroot platform uses QBox's `char_backend_stdio` for the PL011 UART:

```lua
charbackend_stdio_0 = {
    moduletype = "char_backend_stdio";
    read_write = true;
};
```

That stdio-backed UART is sensitive to stdin EOF/HUP while Linux is still
booting. The previous runner delegated PTY management to util-linux `script(1)`.
In tmux/Codex and some post-build invocations, `script(1)` can propagate a
transient stdin EOF/HUP to the child PTY on the first cold run, allowing QBox to
stop before userspace is reached.

## Fix

`run_qbox_buildroot_boot.sh` now prefers the repo-local
`scripts/qbox_pty_runner.py` before falling back to `script(1)`.

The Python runner uses only the standard library and:

- opens a dedicated child PTY for QBox,
- mirrors UART output to stdout and the selected log file,
- forwards real terminal input for interactive login sessions,
- keeps the child PTY open when parent stdin reaches EOF/HUP,
- forwards `Ctrl-C` as `SIGINT` to the QBox process group.

`QBOX_BOOT_PTY=0` still forces the old plain line-buffered path for debugging,
but that path can reproduce early EOF-sensitive exits.

## Verification

Commands executed:

```bash
python3 -m py_compile scripts/qbox_pty_runner.py
bash -n scripts/run_qbox_buildroot_boot.sh \
  scripts/build_qbox_buildroot_platform.sh \
  scripts/check_buildroot_arm64_lane.sh
scripts/check_buildroot_arm64_lane.sh
scripts/build_qbox_buildroot_platform.sh
QBOX_BOOT_TIMEOUT=8 ./scripts/run_qbox_buildroot_boot.sh
QBOX_BOOT_TIMEOUT=8 QBOX_BOOT_LOG=build/verification/qbox-a710-buildroot-boot-nontty.log \
  ./scripts/run_qbox_buildroot_boot.sh >/tmp/qbox-nontty-smoke.stdout 2>&1
```

Results:

| Check | Result | Evidence |
| --- | --- | --- |
| Python runner syntax | PASS | `python3 -m py_compile scripts/qbox_pty_runner.py` |
| Shell syntax | PASS | `bash -n ...` |
| Lane contract | PASS | `scripts/check_buildroot_arm64_lane.sh` |
| First bounded run after QBox rebuild | PASS | `Run /sbin/init as init process`, `qbox-a710 login:` |
| Non-TTY bounded run | PASS | `build/verification/qbox-a710-buildroot-boot-nontty.log` reached login prompt |

Bounded smoke exit code remains `124` when `QBOX_BOOT_TIMEOUT` is non-zero,
because `timeout(1)` stops the otherwise interactive simulation after the login
prompt. Default execution remains unlimited and interactive:

```bash
./scripts/run_qbox_buildroot_boot.sh
```
