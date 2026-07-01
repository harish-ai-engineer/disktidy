"""Detect and clean package-manager caches (npm, pnpm, pip, yarn).

All of these are pure download caches that tools rebuild on demand, so
cleaning them is non-destructive.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from .util import dir_size, run, which


@dataclass
class CacheEntry:
    name: str
    path: str
    size: int
    clean_cmd: list[str]


# tool -> (path-query command, clean command)
_TOOLS = {
    "npm": (["npm", "config", "get", "cache"], ["npm", "cache", "clean", "--force"]),
    "pnpm": (["pnpm", "store", "path"], ["pnpm", "store", "prune"]),
    "pip": (["pip", "cache", "dir"], ["pip", "cache", "purge"]),
    "yarn": (["yarn", "cache", "dir"], ["yarn", "cache", "clean"]),
}


def detect() -> list[CacheEntry]:
    entries: list[CacheEntry] = []
    for name, (path_cmd, clean_cmd) in _TOOLS.items():
        if which(name) is None:
            continue
        res = run(path_cmd, timeout=30)
        if not res.ok or not res.out.strip():
            continue
        path = res.out.strip().splitlines()[-1].strip()
        if not path or not os.path.exists(path):
            continue
        entries.append(CacheEntry(name, path, dir_size(path), clean_cmd))
    entries.sort(key=lambda c: c.size, reverse=True)
    return entries


def clean(entry: CacheEntry) -> tuple[bool, str]:
    res = run(entry.clean_cmd, timeout=300)
    detail = (res.out.strip() or res.err.strip() or "done").splitlines()[-1]
    return res.ok, detail
