"""Utility functions for cross-platform file system operations."""

import os
import shutil
import subprocess
import platform
from pathlib import Path

IS_WINDOWS = platform.system() == "Windows"


def is_symlink_or_junction(path: Path) -> bool:
    """Check if path is a symlink (macOS/Linux) or junction (Windows).

    Args:
        path: Path to check.

    Returns:
        True if the path is a symlink or junction point.
    """
    if not path.exists() and not path.is_symlink():
        return False
    if IS_WINDOWS:
        try:
            result = subprocess.run(
                ["fsutil", "reparsepoint", "query", str(path)],
                capture_output=True, text=True, encoding="utf-8", errors="replace"
            )
            return result.returncode == 0
        except Exception:
            return False
    else:
        return path.is_symlink()


def create_link(src: Path, dst: Path, force: bool = False) -> tuple:
    """Create symlink (macOS) or junction (Windows) from src to dst.

    Automatically falls back to copy if link creation fails.

    Conflict protection (v0.13.0): if ``dst`` already exists as a *real*
    directory (not a link) whose content differs from ``src``, it is left
    untouched and ``(False, "conflict", ...)`` is returned - a plain
    ``rm + link`` here would silently destroy a user-maintained skill.
    Identical content is safe to replace with a link and proceeds.  Pass
    ``force=True`` to overwrite a differing directory anyway.

    Args:
        src: Source directory (must exist).
        dst: Destination path for the link.
        force: Overwrite an existing real directory even when it differs.

    Returns:
        Tuple of (success, method, message) where method is one of:
        'symlink', 'junction', 'copy', 'conflict', 'error'.
    """
    src = Path(src).resolve()
    dst = Path(dst)

    if not src.exists():
        return False, "error", f"Source does not exist: {src}"

    dst.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing link/dir if present
    if dst.exists() or dst.is_symlink():
        if is_symlink_or_junction(dst):
            dst.rmdir()
        elif dst.is_dir():
            if not force and not _dirs_equivalent(src, dst):
                return (
                    False,
                    "conflict",
                    f"Real directory differs from central repo: {dst} "
                    "(use --force to overwrite, or 'askill adopt' to keep a copy)",
                )
            shutil.rmtree(dst)
        else:
            dst.unlink()

    if IS_WINDOWS:
        return _create_junction(src, dst)
    else:
        return _create_symlink(src, dst)


def _dirs_equivalent(a: Path, b: Path) -> bool:
    """Cheap recursive comparison: same relative file paths and sizes.

    Content hashes would be exact but slow for big skills; path+size catches
    the realistic "user edited something" case while keeping sync fast.
    """
    def listing(root: Path) -> dict[str, int] | None:
        out: dict[str, int] = {}
        try:
            for p in root.rglob("*"):
                if p.is_symlink():
                    return None  # any link inside -> treat as different
                if p.is_file():
                    out[str(p.relative_to(root).as_posix())] = p.stat().st_size
                elif p.is_dir():
                    out[str(p.relative_to(root).as_posix()) + "/"] = -1
        except OSError:
            return None
        return out

    la, lb = listing(Path(a)), listing(Path(b))
    if la is None or lb is None:
        return False
    return la == lb


def _create_junction(src: Path, dst: Path) -> tuple:
    """Create a Windows junction point. Falls back to copy on failure."""
    try:
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(dst), str(src)],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        if result.returncode == 0:
            return True, "junction", f"Junction created: {dst} -> {src}"
        else:
            shutil.copytree(src, dst)
            return True, "copy", f"Junction failed, copied: {dst}"
    except Exception as e:
        shutil.copytree(src, dst)
        return True, "copy", f"Junction error ({e}), copied: {dst}"


def _create_symlink(src: Path, dst: Path) -> tuple:
    """Create a Unix/macOS symlink. Falls back to copy on failure."""
    try:
        os.symlink(str(src), str(dst))
        return True, "symlink", f"Symlink created: {dst} -> {src}"
    except OSError as e:
        shutil.copytree(src, dst)
        return True, "copy", f"Symlink failed ({e}), copied: {dst}"


def copy_skill(src: Path, dst: Path) -> None:
    """Copy a skill directory from src to dst, replacing if exists.

    Args:
        src: Source directory.
        dst: Destination directory.
    """
    src = Path(src).resolve()
    dst = Path(dst)

    if dst.exists() or dst.is_symlink():
        if is_symlink_or_junction(dst):
            dst.rmdir()
        elif dst.is_dir():
            shutil.rmtree(dst)
        else:
            dst.unlink()

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst)


def remove_path(path: Path) -> None:
    """Remove a path whether it's a symlink, junction, directory, or file.

    Args:
        path: Path to remove.
    """
    path = Path(path)
    if not path.exists() and not path.is_symlink():
        return
    if is_symlink_or_junction(path):
        path.rmdir()
    elif path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def read_skill_metadata(skill_dir: Path) -> dict:
    """Read metadata from a skill's SKILL.md frontmatter.

    Args:
        skill_dir: Directory containing SKILL.md.

    Returns:
        Dict with 'name' and 'description' keys (may be empty).
    """
    meta = {"name": "", "description": ""}
    skill_md = Path(skill_dir) / "SKILL.md"
    if not skill_md.exists():
        return meta
    try:
        content = skill_md.read_text(encoding="utf-8")
        for line in content.split("\n"):
            if line.startswith("name:"):
                meta["name"] = line.split(":", 1)[1].strip()
            elif line.startswith("description:"):
                meta["description"] = line.split(":", 1)[1].strip()
                break
    except Exception:
        pass
    return meta
