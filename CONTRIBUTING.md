# Contributing to disktidy

Thanks for your interest in improving **disktidy**! This project is small,
dependency-free, and deliberately conservative — please keep those qualities in
mind when contributing.

## Development setup

```bash
git clone https://github.com/harish-ai-engineer/disktidy
cd disktidy
python -m pip install -e .        # editable install
python -m pip install pytest      # for the tests
```

Run it from source:

```bash
python -m disktidy report
python -m disktidy analyze . --files
```

Run the tests:

```bash
python -m pytest -q
```

## Project layout

| File | Responsibility |
|------|----------------|
| `src/disktidy/cli.py` | Argument parsing and command dispatch |
| `src/disktidy/analyze.py` | Disk usage analysis (biggest folders/files) |
| `src/disktidy/consumers.py` | Probes for known space consumers |
| `src/disktidy/docker_reclaim.py` | Safe Docker reclamation + vhdx compaction |
| `src/disktidy/caches.py` | Package-manager cache detection/cleaning |
| `src/disktidy/render.py` | Terminal rendering (banner, tables, colors) |
| `src/disktidy/util.py` | Sizing, colors, subprocess, platform helpers |

## Guidelines

- **Zero runtime dependencies.** Keep the package standard-library only.
- **Safety first.** Scanning must stay read-only; anything that deletes or
  modifies the filesystem must require an explicit `--apply` flag, and must
  never touch Docker volumes or tagged images.
- **Never follow directory symlinks/junctions** when sizing directories.
- **Cross-platform.** Guard platform-specific code (e.g. Windows `diskpart`
  compaction) behind checks; degrade gracefully elsewhere.
- Add or update tests in `tests/` for any new behavior.
- Keep terminal output aligned: pad plain text before applying ANSI color
  (see `render.table`).

## Releasing

1. Bump the version in **both** `pyproject.toml` and `src/disktidy/__init__.py`.
2. Add a section to `CHANGELOG.md`.
3. Commit, then tag and push:
   ```bash
   git tag vX.Y.Z
   git push origin main --tags
   ```
4. CI takes over:
   - **`release.yml`** tests, builds, and publishes to PyPI (`PYPI_API_TOKEN`).
   - **`docker.yml`** builds and pushes the image to GHCR.

## License

By contributing, you agree that your contributions are licensed under the
[MIT License](LICENSE).
