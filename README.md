# diskteddy

[![PyPI version](https://img.shields.io/pypi/v/disktidy.svg)](https://pypi.org/project/disktidy/)
[![Python versions](https://img.shields.io/pypi/pyversions/disktidy.svg)](https://pypi.org/project/disktidy/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A conservative, cross-platform command-line tool that **analyzes where your
disk space went** and helps you **safely reclaim it** — from Docker, package
manager caches, and other well-known space hogs.

> **Latest release: v0.2.3** — `pip install --upgrade disktidy`

It follows one rule, borrowed from good cleanup tools everywhere:
**looking is free and safe; anything destructive requires an explicit flag.**

## Why

Developer machines fill up in predictable ways: a Docker `.vhdx` that never
shrinks, gigabytes of npm/pnpm/pip cache, bloated `.git` histories, Windows
Store apps. `disktidy` finds those automatically and tells you exactly how
to get the space back — instead of you hunting through folders by hand.

## Install

```bash
pip install disktidy
# or, for isolation:
pipx install disktidy
```

Run it from source without installing:

```bash
python -m disktidy report
```

## Quick start

```bash
# Drive overview + biggest known consumers (this is the default command)
disktidy
disktidy report

# Biggest folders under any path (add --files for biggest single files)
disktidy analyze C:\Users\me --top 20 --files

# Docker: see what's reclaimable (dry-run — nothing is deleted)
disktidy docker

# Docker: actually prune junk AND compact the virtual disk
disktidy docker --apply --compact          # (compact needs admin on Windows)

# Package caches: inspect, then clean
disktidy caches
disktidy caches --apply

# Machine-readable output for scripts/CI
disktidy report --json
```

## Commands

| Command | What it does |
|---|---|
| `report` (default) | Per-drive usage + a table of the biggest known consumers, each with a description, a reclaim command, and a safety rating. |
| `analyze [PATH]` | Sizes every child folder of `PATH` and lists the largest; `--files` also finds the biggest individual files. |
| `docker` | Reclaims Docker space: prunes build cache, dangling images, and stopped containers, then optionally compacts the WSL2 `.vhdx`. |
| `caches` | Detects npm / pnpm / pip / yarn caches and cleans them on `--apply`. |

## Safety

* **Dry-run by default.** `docker` and `caches` only *report* until you pass
  `--apply`.
* **Never touches your data.** The Docker path removes build cache, dangling
  images, and stopped containers only — **never volumes or tagged images**.
* **No symlink following** when sizing directories.
* **Compaction is opt-in** (`--compact`), Windows/WSL2-only, and requires an
  elevated (Administrator) terminal — it stops Docker and WSL first, then runs
  `diskpart`.
* **No telemetry, no network calls.**

## Development

```bash
python -m pip install -e .
python -m pytest
python -m disktidy report
```

## Changelog

### 0.2.3
- Colorful terminal dashboard: boxed tables, per-drive usage bars, color-coded
  sizes, and safety badges (`FORCE_COLOR` supported; honors `NO_COLOR`).
- Simplified the GitHub Actions release workflow (PyPI trusted publishing).

### 0.1.0
- Initial release: `report`, `analyze`, `docker`, and `caches` commands;
  dry-run by default; zero dependencies.

## License

MIT
