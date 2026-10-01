"""Typed shape of a supported product's registry entry."""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict


class ProductSpec(TypedDict, total=False):
    """Static description of one supported AI agent product.

    Declared ``total=False`` because some products (e.g. DuMate) omit the
    platform-specific path keys or the optional ``settings_file`` /
    ``extra_dirs_*`` keys.  ``linux_path`` is omitted entirely for products
    without a Linux build.
    """

    name: str
    short: str
    macos_path: Path | None
    windows_path: Path | None
    linux_path: Path | None
    sync_method: str  # "symlink" | "native" | "pack"
    note: str
    extra_dirs_macos: list[Path]
    extra_dirs_windows: list[Path]
    extra_dirs_linux: list[Path]
    settings_file: Path
    settings_mode: str  # "skills-switch": settings.json {"skills": {name: bool}}
    required_frontmatter: list[str]  # extra SKILL.md fields this product mandates
