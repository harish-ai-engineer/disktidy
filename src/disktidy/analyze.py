"""Disk usage analysis: drive overview, biggest folders, biggest files."""
from __future__ import annotations

import heapq
import os
from dataclasses import dataclass, field

from .util import Drive, dir_size, list_drives


@dataclass
class FolderUsage:
    path: str
    size: int


@dataclass
class FileUsage:
    path: str
    size: int


@dataclass
class AnalysisResult:
    root: str
    drives: list[Drive] = field(default_factory=list)
    folders: list[FolderUsage] = field(default_factory=list)
    files: list[FileUsage] = field(default_factory=list)


def biggest_folders(root: str, top: int = 15) -> list[FolderUsage]:
    """Size each immediate child directory of `root` and return the largest."""
    results: list[FolderUsage] = []
    try:
        with os.scandir(root) as it:
            for entry in it:
                try:
                    if entry.is_symlink():
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        results.append(FolderUsage(entry.path, dir_size(entry.path)))
                except OSError:
                    continue
    except OSError:
        return []
    results.sort(key=lambda f: f.size, reverse=True)
    return results[:top]


def biggest_files(root: str, top: int = 15) -> list[FileUsage]:
    """Stream the whole tree and keep the `top` largest files (heap, low memory)."""
    heap: list[tuple[int, str]] = []
    stack = [root]
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
                            size = entry.stat(follow_symlinks=False).st_size
                            if len(heap) < top:
                                heapq.heappush(heap, (size, entry.path))
                            elif size > heap[0][0]:
                                heapq.heapreplace(heap, (size, entry.path))
                    except OSError:
                        continue
        except OSError:
            continue
    return [FileUsage(p, s) for s, p in sorted(heap, reverse=True)]


def analyze(root: str, top: int = 15, want_files: bool = False) -> AnalysisResult:
    root = os.path.abspath(root)
    result = AnalysisResult(root=root)
    result.drives = list_drives()
    result.folders = biggest_folders(root, top)
    if want_files:
        result.files = biggest_files(root, top)
    return result
