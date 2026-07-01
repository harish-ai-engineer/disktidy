# disktidy — Build Log

A short record of how this project came to be, from a full disk to a published
package.

## 1. The problem: a nearly-full SSD

A Windows machine's `C:` drive was down to **3.5 GB free of 237.6 GB**. A manual
top-down analysis found the biggest consumers:

| Location | Size | What it was |
|----------|------|-------------|
| `AppData\Local\Docker` | ~59 GB | A single WSL2 virtual disk (`docker_data.vhdx`) |
| `C:\Windows` | ~43 GB | OS |
| Package-manager caches | ~8 GB+ | pnpm/npm/pip |
| `.git` (home dir) | ~11 GB | Home-directory repo |

## 2. Reclaiming the space

- **Docker (~32 GB reclaimed):** safe prune (build cache, dangling images,
  stopped containers) — never touching volumes or tagged images — then
  compacting the `.vhdx` with `diskpart` (`58.9 GB → 26.6 GB`).
- **Stale dev artifacts (~5 GB):** removed `node_modules`/venvs for projects
  untouched 40+ days.

Result: **~3.5 GB → ~30 GB free.**

## 3. Turning the workflow into a tool

The manual steps — analyze the drive, safely reclaim Docker space, clean caches
— were packaged into **disktidy**, a conservative, cross-platform, dependency-free
CLI. Same philosophy throughout: scanning is read-only; anything destructive
requires an explicit `--apply`.

Commands: `report`, `analyze`, `docker`, `caches`.

## 4. Shipping it

- **PyPI:** published `disktidy` (0.1.0 → 0.2.3) — `pip install disktidy`.
- **Colorful UI (0.2.0–0.2.1):** boxed tables, per-drive usage bars,
  color-coded sizes, and safety badges.
- **GitHub:** repo at `harish-ai-engineer/disktidy` with README badges,
  a tagged release, `CHANGELOG.md`, and `CONTRIBUTING.md`.
- **CI:** `release.yml` publishes to PyPI on version tags (token auth);
  `docker.yml` builds and pushes an image to GHCR
  (`ghcr.io/harish-ai-engineer/disktidy`).

## 5. Release process

```bash
# bump version in pyproject.toml + src/disktidy/__init__.py, update CHANGELOG.md
git tag vX.Y.Z
git push origin main --tags   # -> PyPI + GHCR, automatically
```
