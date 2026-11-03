"""settings.json skills-switch IO (WorkBuddy/CodeBuddy schema).

Pure path-in/path-out helpers; no config globals and nothing here is
patched through the sync package seam."""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from pathlib import Path


def _enable_in_settings(settings_path: Path, skill_name: str, verbose: bool = True) -> str:
    """Enable a skill in a product's settings.json.

    Generic handler for the ``skills-switch`` settings mode (declared in
    products.py): the file carries a top-level ``"skills": {name: bool}``
    map - confirmed for WorkBuddy and CodeBuddy.  The caller is responsible
    for only invoking this when the product is actually set up on the
    machine (see the A9 guard in sync_skill); the file itself may be
    missing and will be created inside its existing product directory.

    Returns:
        ``"ok"``     - settings updated successfully
        ``"locked"`` - the file is held by another process (most often the
                       product IDE is running and holds an exclusive lock on
                       settings.json). The skill link exists but is NOT
                       enabled in the product.
        ``"failed"`` - any other error.
    """
    try:
        if settings_path.exists():
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        else:
            settings = {}

        skills_config = settings.setdefault("skills", {})
        skills_config[skill_name] = True

        _write_json_atomic(settings_path, settings)
        if verbose:
            print(f"  {'':>10}   Updated settings.json")
        return "ok"
    except (PermissionError, OSError) as e:
        # WinError 5 / EACCES: the file is locked by a running IDE. The
        # junction was created but the skill is not enabled - surfaced
        # prominently by sync_skill instead of swallowed here.
        if verbose:
            print(f"  {'':>10}   Warning: could not update settings.json: {e}")
        if getattr(e, "winerror", None) == 5 or getattr(e, "errno", None) in (5, 13):
            return "locked"
        return "failed"
    except Exception as e:
        if verbose:
            print(f"  {'':>10}   Warning: could not update settings.json: {e}")
        return "failed"

def _disable_in_settings(settings_path: Path, skill_name: str) -> bool:
    """Remove a skill from a product's settings.json (``skills-switch`` mode).

    Returns:
        True if an entry was removed, False otherwise (quietly).
    """
    try:
        if settings_path.exists():
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            if "skills" in settings and skill_name in settings["skills"]:
                del settings["skills"][skill_name]
                _write_json_atomic(settings_path, settings)
                return True
    except Exception:
        pass
    return False

def _write_json_atomic(path: Path, data: dict) -> None:
    """Write *data* as JSON to *path* atomically.

    A temp file is created in the same parent directory (same volume on every
    platform, which is what ``os.replace`` requires for atomicity on
    Windows), fsync'd, and then swapped into place via ``os.replace``.  If
    the process dies mid-write the original file is untouched and a stray
    ``.<name>.<rand>.tmp`` file is left behind for the next successful
    write to overwrite.

    Stdlib only - no new dependencies.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            # Some filesystems / platforms don't support fsync; the
            # os.replace below is still atomic at the rename layer.
            with contextlib.suppress(OSError):
                os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        # Best-effort cleanup so we don't leak temp files on failure.
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise
