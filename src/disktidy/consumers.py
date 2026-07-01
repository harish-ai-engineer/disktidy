"""Probe well-known space consumers and describe how to reclaim each."""
from __future__ import annotations

import os
from dataclasses import dataclass

from .util import dir_size, is_windows, run, which


@dataclass
class Consumer:
    name: str
    size: int
    path: str
    what: str          # human description
    reclaim: str       # how to get the space back
    safety: str        # "safe" | "caution" | "manual"


def _size_if_exists(path: str) -> int:
    if path and os.path.exists(path):
        if os.path.isfile(path):
            try:
                return os.path.getsize(path)
            except OSError:
                return 0
        return dir_size(path)
    return 0


def _docker_vhdx() -> list[Consumer]:
    out: list[Consumer] = []
    if not is_windows():
        return out
    local = os.environ.get("LOCALAPPDATA", os.path.expanduser(r"~\AppData\Local"))
    candidates = [
        os.path.join(local, "Docker", "wsl", "disk", "docker_data.vhdx"),
        os.path.join(local, "Docker", "wsl", "data", "ext4.vhdx"),
        os.path.join(local, "Docker", "wsl", "main", "ext4.vhdx"),
    ]
    for path in candidates:
        size = _size_if_exists(path)
        if size:
            out.append(Consumer(
                name="Docker virtual disk",
                size=size,
                path=path,
                what="WSL2 virtual disk holding Docker images/containers/volumes",
                reclaim="disktidy docker --apply --compact",
                safety="caution",
            ))
    return out


def _package_caches() -> list[Consumer]:
    out: list[Consumer] = []
    probes = [
        ("npm cache", ["npm", "config", "get", "cache"], "npm cache clean --force"),
        ("pnpm store", ["pnpm", "store", "path"], "pnpm store prune"),
        ("pip cache", ["pip", "cache", "dir"], "pip cache purge"),
        ("yarn cache", ["yarn", "cache", "dir"], "yarn cache clean"),
    ]
    for name, cmd, reclaim in probes:
        if which(cmd[0]) is None:
            continue
        res = run(cmd, timeout=30)
        path = res.out.strip().splitlines()[-1].strip() if res.ok and res.out.strip() else ""
        size = _size_if_exists(path)
        if size:
            out.append(Consumer(
                name=name,
                size=size,
                path=path,
                what="Package-manager download cache (rebuilds on demand)",
                reclaim=reclaim,
                safety="safe",
            ))
    return out


def _large_git_dirs(roots: list[str], threshold: int = 500 * 1024 * 1024) -> list[Consumer]:
    """Find unusually large .git directories under the given roots (depth<=3)."""
    out: list[Consumer] = []
    seen: set[str] = set()
    for root in roots:
        if not os.path.isdir(root):
            continue
        base_depth = root.rstrip(os.sep).count(os.sep)
        for dirpath, dirnames, _ in os.walk(root):
            depth = dirpath.count(os.sep) - base_depth
            if depth > 3:
                dirnames[:] = []
                continue
            if ".git" in dirnames:
                git_path = os.path.join(dirpath, ".git")
                if git_path in seen:
                    continue
                seen.add(git_path)
                size = dir_size(git_path)
                if size >= threshold:
                    out.append(Consumer(
                        name=".git history",
                        size=size,
                        path=git_path,
                        what="Git repository history - may hold accidentally committed blobs",
                        reclaim="Investigate with 'git count-objects -vH' / git filter-repo",
                        safety="manual",
                    ))
                # do not descend into the repo's own .git
                dirnames[:] = [d for d in dirnames if d != ".git"]
    return out


def _windows_extras() -> list[Consumer]:
    out: list[Consumer] = []
    if not is_windows():
        return out
    local = os.environ.get("LOCALAPPDATA", os.path.expanduser(r"~\AppData\Local"))
    temp = os.environ.get("TEMP", os.path.join(local, "Temp"))
    for path, name, what, reclaim, safety in [
        (temp, "User temp files", "Temporary files (safe to clear)", "Delete contents / cleanmgr", "safe"),
        (os.path.join(local, "Packages"), "Windows Store apps", "Installed Store app data", "Uninstall unused Store apps", "manual"),
        (r"C:\Windows\SoftwareDistribution\Download", "Windows Update cache", "Downloaded update packages", "cleanmgr / Disk Cleanup", "safe"),
    ]:
        size = _size_if_exists(path)
        if size:
            out.append(Consumer(name, size, path, what, reclaim, safety))
    return out


def scan_consumers(git_roots: list[str] | None = None) -> list[Consumer]:
    """Return all detected consumers, largest first."""
    home = os.path.expanduser("~")
    git_roots = git_roots or [
        os.path.join(home, "Projects"),
        os.path.join(home, "Desktop"),
    ]
    consumers: list[Consumer] = []
    consumers += _docker_vhdx()
    consumers += _package_caches()
    consumers += _windows_extras()
    consumers += _large_git_dirs(git_roots)
    consumers.sort(key=lambda c: c.size, reverse=True)
    return consumers
