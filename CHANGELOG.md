# Changelog

All notable changes to **agent-skill-manager** are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

> The package is published on PyPI as **`cn-skill-sync`** (the import
> name `agent_skill_manager` is kept for the python package to avoid
> confusion with skill-creator projects). ``pip install cn-skill-sync``.

## [Unreleased]

### Added
- Global **`--quiet / -q`** flag suppresses non-essential output on every
  subcommand (`sync`, `list`, `status`, `install`, `audit`, `search`,
  `verify`, `update`, `products`). Errors, conflict warnings and SECURITY
  WARNING lines always print.
- Global **`--json`** flag emits machine-readable JSON to stdout for
  `status`, `list`, `audit`, `search`, `verify`, `update`, `products`,
  suitable for piping into Agent workflows and CI scripts.
- **`tests/fixtures/malicious/`** — 12 golden-sample skills covering
  every audit rule (curl|sh, reverse shell, prompt injection, exfil via
  webhook, hardcoded secrets, executable payloads, etc.). Backed by a
  parametrized regression test so adding a new attack vector is one
  new directory + one EXPECTED_TRIGGERS row.
- **CI**: new `Lint (ruff)` and `Type check (mypy)` jobs on
  ubuntu-latest in addition to the 6-platform test matrix. Configuration
  lives in `pyproject.toml` (`[tool.ruff]`, `[tool.mypy]`).

### Changed
- `sync_skill` decomposed from a 143-line function into a 3-layer
  structure: `sync_skill` (orchestration), `_sync_one_product`
  (per-product sync, shared-dir dedup, settings.json enable),
  `_sync_extra_dirs` (extra_dirs sweep). Behaviour unchanged.
- `sync_skill` and `audit_all` now run their per-product / per-skill
  work through a `ThreadPoolExecutor` (max 8 workers). `synced_dirs` is
  guarded by a `Lock`; `print()` for progress lines also serialises so
  output stays in order. No third-party deps introduced.

### Fixed
- Bug (audit.py): `for f in findings` loop variable shadowed the outer
  `for f in files: f: Path`, so the score-summary `dict[str, int]`
  counted the wrong key. Renamed to `finding`.

## [0.13.0] - 2026-09-30

### Added
- **Conflict protection** in `create_link`: if the destination already
  exists as a *real* directory whose content differs from the central
  repo, the sync is skipped (data preserved) and a ``SKIP conflict``
  warning is printed. Pass `--force` on `askill sync` to overwrite.
- **Per-product frontmatter requirements** (`required_frontmatter` in
  `ProductSpec`). Currently used by QwenWork, which requires `name`,
  `version`, `description` and `description_zh`. ``askill verify`` and
  the post-install checks surface the gap.
- **Source tracking** (`.askill-sources.json` in central repo) records
  the GitHub URL of every install. ``askill update [skill]`` checks
  `git ls-remote` and applies updates in place.

### Changed
- `sync_skill` now re-syncs each product's declared `extra_dirs_*` (e.g.
  Kimi's `~/.kimi-code/skills/`) on the next run, not just on first
  install.

### Fixed
- Linux support: 8 of the 15 products now work on Linux (CLI tools and
  those using the dotdir convention). The remaining 7 are desktop / IDE
  apps without a Linux build; ``askill products`` shows ``N/A`` for them
  instead of trying to create dead directories.
- `extra_dirs` are no longer created on machines where the product's
  primary skills dir does not exist (A9 guard).

## [0.7.0] - 2025-XX-XX

### Changed
- CI matrix runs Python 3.10 / 3.13 on ubuntu, windows, macos (was
  3.8 across the board). setuptools ≥ 64 required.

## [0.6.0] - 2025-XX-XX

### Added
- Initial Linux paths for CLI-class products (AutoClaw2, Kimi,
  MiniMax Code, CodeBuddy, Comate, ZCode).
- `native` sync_method for MiniMax Code (already reads `~/.agents/skills/`
  via Mavis; no symlink required).

## [0.1.0] - 2025-XX-XX

### Added
- Initial release. Cross-platform `askill sync` of skill directories
  across 6 then-current Chinese AI agent products via symlinks (macOS,
  Linux) and junctions (Windows). Zero third-party deps.