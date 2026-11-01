"""Central-repo skill enumeration (read-only inventory layer).

Split out of :mod:`services.sync` so ``spec`` can enumerate skills without
importing the sync engine (spec ⇄ sync formed a module-level import cycle,
found by the 2026-10-31 architecture health check §3). ``sync`` keeps a
thin ``list_skills()`` wrapper that reads its own ``CENTRAL_DIR`` module
attribute, so the established ``patch sync.CENTRAL_DIR`` test seam keeps
working for every existing consumer.
"""

from __future__ import annotations

from pathlib import Path

from ..config.products import CENTRAL_DIR

__all__ = ["list_skills"]


def list_skills(central: Path | None = None) -> list[Path]:
    """List all skills in the central repository.

    Args:
        central: override the central repository (tests, tooling).
            Defaults to the configured ``CENTRAL_DIR``.

    Returns:
        Sorted list of skill directory paths (directories that contain
        a ``SKILL.md``).
    """
    base = Path(central) if central is not None else CENTRAL_DIR
    if not base.exists():
        return []
    return sorted(
        d for d in base.iterdir()
        if d.is_dir() and (d / "SKILL.md").exists()
    )
