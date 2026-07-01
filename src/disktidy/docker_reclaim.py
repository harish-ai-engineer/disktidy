"""Safe Docker space reclamation: prune junk, then optionally compact the vhdx.

Safety model (mirrors what we did by hand):
  * Only removes build cache, dangling (untagged) images, and stopped
    containers. NEVER prunes volumes or tagged images -> no data loss.
  * Compaction of the WSL2 vhdx is Windows-only, needs admin, and stops
    Docker/WSL first. It is opt-in via --compact.
"""
from __future__ import annotations

import os
import tempfile
import time
from dataclasses import dataclass

from .util import is_admin, is_windows, run, which


@dataclass
class Step:
    label: str
    detail: str
    ok: bool = True


def docker_available() -> bool:
    if which("docker") is None:
        return False
    return run(["docker", "info"], timeout=30).ok


def df() -> str:
    res = run(["docker", "system", "df"], timeout=60)
    return res.out if res.ok else res.err


def safe_prune(apply: bool) -> list[Step]:
    """Reclaim junk inside the Docker disk. Dry-run unless apply=True."""
    steps: list[Step] = []
    plan = [
        ("Build cache", ["docker", "builder", "prune", "-a", "-f"]),
        ("Stopped containers", ["docker", "container", "prune", "-f"]),
        ("Dangling images", ["docker", "image", "prune", "-f"]),
    ]
    for label, cmd in plan:
        if not apply:
            steps.append(Step(label, "would run: " + " ".join(cmd)))
            continue
        res = run(cmd, timeout=600)
        detail = (res.out.strip().splitlines() or [""])[-1] if res.ok else res.err.strip()
        steps.append(Step(label, detail or "done", res.ok))
    return steps


def find_vhdx() -> str | None:
    if not is_windows():
        return None
    local = os.environ.get("LOCALAPPDATA", os.path.expanduser(r"~\AppData\Local"))
    for rel in (
        ("Docker", "wsl", "disk", "docker_data.vhdx"),
        ("Docker", "wsl", "data", "ext4.vhdx"),
    ):
        path = os.path.join(local, *rel)
        if os.path.exists(path):
            return path
    return None


def _stop_docker_and_wsl() -> None:
    # Best-effort stop of Docker Desktop, then shut down WSL so the vhdx unlocks.
    for proc in ("Docker Desktop.exe", "com.docker.backend.exe", "com.docker.build.exe"):
        run(["taskkill", "/IM", proc, "/F"], timeout=30)
    time.sleep(3)
    run(["wsl", "--shutdown"], timeout=60)
    time.sleep(3)


def compact_vhdx(apply: bool) -> list[Step]:
    """Compact the WSL2 vhdx to return freed space to the host drive."""
    steps: list[Step] = []
    if not is_windows():
        steps.append(Step("Compact", "vhdx compaction is Windows/WSL2 only — skipped", True))
        return steps

    vhdx = find_vhdx()
    if not vhdx:
        steps.append(Step("Compact", "no Docker vhdx found — skipped", True))
        return steps

    before = os.path.getsize(vhdx)
    steps.append(Step("Target", f"{vhdx} ({before} bytes)"))

    if not apply:
        steps.append(Step("Compact", "would stop Docker+WSL and run diskpart 'compact vdisk'"))
        return steps

    if not is_admin():
        steps.append(Step(
            "Compact",
            "SKIPPED: needs Administrator. Re-run in an elevated terminal.",
            False,
        ))
        return steps

    _stop_docker_and_wsl()

    script = (
        f'select vdisk file="{vhdx}"\n'
        "attach vdisk readonly\n"
        "compact vdisk\n"
        "detach vdisk\n"
        "exit\n"
    )
    fd, script_path = tempfile.mkstemp(suffix=".txt", text=True)
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(script)
        res = run(["diskpart", "/s", script_path], timeout=1800)
        after = os.path.getsize(vhdx) if os.path.exists(vhdx) else before
        reclaimed = before - after
        if res.ok:
            steps.append(Step("Compact", f"reclaimed {reclaimed} bytes to host", True))
        else:
            steps.append(Step("Compact", res.err.strip() or "diskpart failed", False))
    finally:
        try:
            os.remove(script_path)
        except OSError:
            pass
    return steps
