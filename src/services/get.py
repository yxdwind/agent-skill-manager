"""Reference tier: read a skill without installing it (``askill get``, v0.22.0).

Borrowed from asm's ``get`` / ``borrow`` flow: a skill's SKILL.md body is
only useful while it is loaded, so trying a skill should not require
installing it into the central repo.  ``askill get <source>`` prints the
SKILL.md to stdout; ``--dir`` copies the full skill folder (supporting
files, scripts, references) to a temp path for the caller to inspect and
clean up; ``--list`` shows what a repo offers.  Nothing is installed,
synced, audited, or recorded in source tracking - get is strictly
read-only.
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from .sync.install import _report_clone_failure, _shallow_clone

__all__ = ["get_skill"]


def _resolve_repo(source: str) -> tuple[str | None, str | None]:
    """Map a source to (repo_url, skill_hint) for preview.

    Accepts the same shorthands as install (owner/repo, owner/repo@skill,
    skills.sh links) plus plain GitHub repo and /tree/ URLs.
    """
    from .registry import resolve_source

    resolved = resolve_source(source)
    if resolved:
        return resolved["repo_url"], resolved["skill"]
    if source.startswith("http") and "github.com" in source:
        if "/tree/" in source:
            parts = source.split("/tree/", 1)
            segs = parts[1].lstrip("/").split("/")
            hint = segs[-1] if len(segs) > 1 else None
            return parts[0], hint
        return source.rstrip("/"), None
    return None, None


def _find_skill_dirs(root: Path) -> list[Path]:
    """Directories containing a SKILL.md, shallowest first (root included)."""
    found = [p.parent for p in root.rglob("SKILL.md")]
    found.sort(key=lambda d: (len(d.parts), str(d).lower()))
    return found


def _get_local(src: Path, *, to_dir: bool, list_only: bool) -> int:
    """Preview a local skill directory without installing (v0.25.0)."""
    dirs = _find_skill_dirs(src)
    if list_only:
        if not dirs:
            print(f"No SKILL.md found under {src}.")
            return 1
        print(f"{len(dirs)} skill(s) under {src}:")
        for d in dirs:
            label = "(this dir)" if d == src else str(d.relative_to(src))
            print(f"  {d.name}  {label}")
        return 0

    if dirs and dirs[0] == src:
        skill_dir = src
    elif len(dirs) == 1:
        skill_dir = dirs[0]
    elif [d for d in dirs if d.name == src.name]:
        skill_dir = next(d for d in dirs if d.name == src.name)
    else:
        print("No SKILL.md in this directory or single skill subfolder; found:")
        for d in dirs[:8]:
            print(f"  {d.name}")
        return 1

    if to_dir:
        out = Path(tempfile.gettempdir()) / "askill-get" / skill_dir.name
        if out.exists():
            shutil.rmtree(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(skill_dir, out)
        print(f"Borrowed to: {out}")
        print("Plain temp copy - delete the folder when done.")
        return 0

    print((skill_dir / "SKILL.md").read_text(encoding="utf-8", errors="replace"))
    return 0


def get_skill(
    source: str,
    *,
    to_dir: bool = False,
    list_only: bool = False,
    verbose: bool = True,
) -> int:
    """Preview a skill without installing. Returns a process exit code."""
    # v0.25.0: local directory - same read-only semantics, no clone
    if not source.startswith("http"):
        src = Path(source)
        if src.exists() and src.is_dir():
            return _get_local(src, to_dir=to_dir, list_only=list_only)

    repo_url, hint = _resolve_repo(source)
    if not repo_url:
        print("Unsupported source. Use owner/repo@skill, owner/repo, or a GitHub URL.")
        return 2

    with tempfile.TemporaryDirectory() as tmp:
        ok, err = _shallow_clone(repo_url, None, Path(tmp))
        if not ok:
            if verbose:
                _report_clone_failure(err)
            return 1
        root = Path(tmp)

        dirs = _find_skill_dirs(root)

        if list_only:
            if not dirs:
                print("No SKILL.md found in this repo.")
                return 1
            print(f"{len(dirs)} skill(s) in {repo_url}:")
            for d in dirs:
                label = "(repo root)" if d == root else str(d.relative_to(root))
                print(f"  {d.name}  {label}")
            print("\nPreview one: askill get <repo>@<skill>")
            return 0

        if hint:
            match = next((d for d in dirs if d.name == hint), None)
            if match is None:
                print(f"Skill '{hint}' not found in {repo_url}.")
                print("List what exists: askill get <repo> --list")
                return 1
            skill_dir = match
        elif dirs and dirs[0] == root:
            skill_dir = root
        elif len(dirs) == 1:
            skill_dir = dirs[0]
        else:
            print("No SKILL.md at repo root and multiple skill folders found:")
            for d in dirs:
                print(f"  {d.name}")
            print("Pick one: askill get <repo>@<skill>")
            return 1

        if to_dir:
            out = Path(tempfile.gettempdir()) / "askill-get" / skill_dir.name
            if out.exists():
                shutil.rmtree(out)
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(skill_dir, out)
            print(f"Borrowed to: {out}")
            print("Plain temp copy - read SKILL.md and the supporting files,")
            print("then delete the folder when done.")
            return 0

        print((skill_dir / "SKILL.md").read_text(encoding="utf-8", errors="replace"))
        return 0
