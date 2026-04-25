#!/usr/bin/env python3
"""Run a command under a stable PTY while mirroring output to stdout and a log.

QBox's stdio UART backend is sensitive to stdin EOF/HUP during early boot. This
runner keeps the child PTY open even when the parent stdin is non-interactive or
has no more input, while still forwarding real terminal input for interactive
login sessions.
"""

from __future__ import annotations

import argparse
import errno
import fcntl
import os
import pty
import select
import signal
import subprocess
import sys
import termios
import time
import tty
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", required=True, help="output log path")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="command after --")
    args = parser.parse_args()
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    if not args.command:
        parser.error("missing command")
    return args


def copy_winsize(src_fd: int, dst_fd: int) -> None:
    try:
        winsize = fcntl.ioctl(src_fd, termios.TIOCGWINSZ, b"\0" * 8)
        fcntl.ioctl(dst_fd, termios.TIOCSWINSZ, winsize)
    except OSError:
        pass


def set_child_controlling_tty(slave_fd: int) -> None:
    os.setsid()
    try:
        fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)
    except OSError:
        # The PTY still works as stdin/stdout/stderr even if controlling-TTY
        # assignment is unavailable on a platform.
        pass


def terminate_process_group(proc: subprocess.Popen[bytes], sig: int) -> None:
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, sig)
    except ProcessLookupError:
        pass


def write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    while view:
        try:
            written = os.write(fd, view)
        except BlockingIOError:
            continue
        view = view[written:]


def main() -> int:
    args = parse_args()
    log_path = Path(args.log)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    master_fd, slave_fd = pty.openpty()
    stdin_fd = sys.stdin.fileno()
    stdout_fd = sys.stdout.fileno()
    interactive_stdin = os.isatty(stdin_fd)

    if interactive_stdin:
        copy_winsize(stdin_fd, slave_fd)

    old_tty_attrs = None
    proc: subprocess.Popen[bytes] | None = None

    def handle_winch(signum: int, frame: object) -> None:
        if interactive_stdin:
            copy_winsize(stdin_fd, master_fd)

    previous_winch = signal.getsignal(signal.SIGWINCH)
    signal.signal(signal.SIGWINCH, handle_winch)

    try:
        if interactive_stdin:
            old_tty_attrs = termios.tcgetattr(stdin_fd)
            tty.setcbreak(stdin_fd)

        with log_path.open("wb") as log_file:
            proc = subprocess.Popen(
                args.command,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                close_fds=True,
                preexec_fn=lambda: set_child_controlling_tty(slave_fd),
            )
            os.close(slave_fd)
            slave_fd = -1

            input_open = True
            child_exit_seen_at: float | None = None
            read_fds: list[int] = [master_fd]
            if input_open:
                read_fds.append(stdin_fd)

            while read_fds:
                try:
                    readable, _, _ = select.select(read_fds, [], [], 0.2)
                except InterruptedError:
                    continue

                if master_fd in readable:
                    try:
                        data = os.read(master_fd, 4096)
                    except OSError as exc:
                        if exc.errno == errno.EIO:
                            read_fds.remove(master_fd)
                            continue
                        raise
                    if not data:
                        read_fds.remove(master_fd)
                        continue
                    write_all(stdout_fd, data)
                    log_file.write(data)
                    log_file.flush()

                if input_open and stdin_fd in readable:
                    try:
                        data = os.read(stdin_fd, 4096)
                    except OSError:
                        data = b""
                    if data:
                        try:
                            write_all(master_fd, data)
                        except OSError:
                            input_open = False
                            if stdin_fd in read_fds:
                                read_fds.remove(stdin_fd)
                    else:
                        # Do not close the child PTY on parent stdin EOF/HUP.
                        # QBox's stdio UART backend can otherwise see EOF and
                        # stop the simulation before Linux reaches userspace.
                        input_open = False
                        if stdin_fd in read_fds:
                            read_fds.remove(stdin_fd)

                if proc.poll() is not None:
                    if input_open:
                        input_open = False
                        if stdin_fd in read_fds:
                            read_fds.remove(stdin_fd)
                    if child_exit_seen_at is None:
                        child_exit_seen_at = time.monotonic()
                    elif time.monotonic() - child_exit_seen_at > 0.5:
                        # Some PTY implementations do not report EOF promptly
                        # once the child exits. The child is gone, so stop after
                        # a short drain window instead of waiting for stdin.
                        break
                else:
                    child_exit_seen_at = None

            return proc.wait()
    except KeyboardInterrupt:
        if proc is not None:
            terminate_process_group(proc, signal.SIGINT)
            try:
                return proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                terminate_process_group(proc, signal.SIGTERM)
                try:
                    return proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    terminate_process_group(proc, signal.SIGKILL)
                    return proc.wait()
        return 130
    finally:
        if old_tty_attrs is not None:
            termios.tcsetattr(stdin_fd, termios.TCSADRAIN, old_tty_attrs)
        signal.signal(signal.SIGWINCH, previous_winch)
        for fd in (master_fd, slave_fd):
            if fd >= 0:
                try:
                    os.close(fd)
                except OSError:
                    pass


if __name__ == "__main__":
    raise SystemExit(main())
