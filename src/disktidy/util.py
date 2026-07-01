"""Shared helpers: sizing, formatting, colors, subprocess, platform checks."""
from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass


# --------------------------------------------------------------------------- #
# Formatting
# --------------------------------------------------------------------------- #
def human_size(num: float) -> str:
    """Format a byte count as a human-readable string (binary units)."""
    num = float(num)
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if abs(num) < 1024.0:
            if unit == "B":
                return f"{num:.0f} {unit}"
            return f"{num:.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} EB"


# --------------------------------------------------------------------------- #
# Color output (opt-out, TTY-aware)
# --------------------------------------------------------------------------- #
class Style:
    def __init__(self, enabled: bool):
        self.enabled = enabled

    def _wrap(self, code: str, text: str) -> str:
        if not self.enabled:
            return text
        return f"\033[{code}m{text}\033[0m"

    def bold(self, t: str) -> str:
        return self._wrap("1", t)

    def dim(self, t: str) -> str:
        return self._wrap("2", t)

    def red(self, t: str) -> str:
        return self._wrap("31", t)

    def green(self, t: str) -> str:
        return self._wrap("32", t)

    def yellow(self, t: str) -> str:
        return self._wrap("33", t)

    def cyan(self, t: str) -> str:
        return self._wrap("36", t)


def make_style(no_color: bool) -> Style:
    enabled = (not no_color) and sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
    if enabled and os.name == "nt":
        # Enable ANSI on legacy Windows consoles.
        try:
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass
    return Style(enabled)


# --------------------------------------------------------------------------- #
# Disk sizing (no symlink following, error-tolerant)
# --------------------------------------------------------------------------- #
def dir_size(path: str) -> int:
    """Total size in bytes of everything under `path`, iteratively.

    Never follows directory symlinks/junctions and silently skips entries it
    cannot access (permissions, races) — the same conservative behaviour we
    used when analysing the drive by hand.
    """
    total = 0
    stack = [path]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                for entry in it:
                    try:
                        if entry.is_symlink():
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(entry.path)
                        else:
                            total += entry.stat(follow_symlinks=False).st_size
                    except OSError:
                        continue
        except OSError:
            continue
    return total


@dataclass
class Drive:
    name: str
    total: int
    used: int
    free: int

    @property
    def pct_free(self) -> float:
        return (self.free / self.total * 100) if self.total else 0.0


def list_drives() -> list[Drive]:
    """Return usage for each mounted filesystem/drive."""
    drives: list[Drive] = []
    if os.name == "nt":
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for i in range(26):
            if bitmask & (1 << i):
                letter = f"{chr(65 + i)}:\\"
                try:
                    usage = shutil.disk_usage(letter)
                    drives.append(Drive(letter[:2], usage.total, usage.used, usage.free))
                except OSError:
                    continue
    else:
        seen = set()
        for mount in ("/", "/home", os.path.expanduser("~")):
            try:
                real = os.path.realpath(mount)
                if real in seen:
                    continue
                seen.add(real)
                usage = shutil.disk_usage(mount)
                drives.append(Drive(mount, usage.total, usage.used, usage.free))
            except OSError:
                continue
    return drives


# --------------------------------------------------------------------------- #
# Subprocess
# --------------------------------------------------------------------------- #
@dataclass
class Cmd:
    rc: int
    out: str
    err: str

    @property
    def ok(self) -> bool:
        return self.rc == 0


def run(args, timeout: int = 600) -> Cmd:
    """Run a command, capturing output. Returns rc=127 if the binary is missing."""
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
        return Cmd(proc.returncode, proc.stdout or "", proc.stderr or "")
    except FileNotFoundError:
        return Cmd(127, "", f"not found: {args[0] if args else args}")
    except subprocess.TimeoutExpired:
        return Cmd(124, "", "timed out")


def which(name: str) -> str | None:
    return shutil.which(name)


# --------------------------------------------------------------------------- #
# Platform / privilege
# --------------------------------------------------------------------------- #
def is_windows() -> bool:
    return os.name == "nt"


def is_admin() -> bool:
    if is_windows():
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
    try:
        return os.geteuid() == 0  # type: ignore[attr-defined]
    except AttributeError:
        return False
