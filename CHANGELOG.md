# Changelog

All notable changes to **disktidy** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this
project adheres to [Semantic Versioning](https://semver.org/).

## [0.2.3] - 2026-07-01

### Added
- Docker image published to GitHub Container Registry
  (`ghcr.io/harish-ai-engineer/disktidy`) via a `docker.yml` workflow.
- `Dockerfile` and `.dockerignore` for a containerized build.
- README version/Python/license badges and a changelog section.

### Changed
- Release workflow now publishes to PyPI using the `PYPI_API_TOKEN` secret
  (token-based) instead of trusted publishing.

## [0.2.1] - 2026-07-01

### Changed
- Brighter color palette; refreshed banner and safety badges.

## [0.2.0] - 2026-07-01

### Added
- Colorful terminal dashboard: Unicode boxed tables, per-drive usage bars,
  color-coded sizes, safety badges, and a "safe to reclaim now" summary.
- `FORCE_COLOR` support (still honors `NO_COLOR` and non-TTY output).

## [0.1.0] - 2026-07-01

### Added
- Initial release with four commands:
  - `report` — drive overview + biggest known space consumers.
  - `analyze` — biggest folders/files under a path.
  - `docker` — safe prune (build cache, dangling images, stopped containers)
    plus optional WSL2 `.vhdx` compaction; never touches volumes or tagged
    images.
  - `caches` — detect and clean npm/pnpm/pip/yarn caches.
- Dry-run by default; destructive actions require `--apply`.
- JSON output, zero dependencies, no telemetry, no network calls.

[0.2.3]: https://github.com/harish-ai-engineer/disktidy/releases/tag/v0.2.3
[0.2.1]: https://pypi.org/project/disktidy/0.2.1/
[0.2.0]: https://pypi.org/project/disktidy/0.2.0/
[0.1.0]: https://pypi.org/project/disktidy/0.1.0/
