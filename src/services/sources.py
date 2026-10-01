"""Source tracking: record where each skill came from, check for updates.

``askill install <github-url>`` writes an entry into
``~/.agents/skills/.askill-sources.json``; ``askill update [skill]`` then
compares the recorded repo's latest commit against the recorded one and
reports / applies upgrades.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional

from ..config.products import CENTRAL_DIR

SOURCES_FILE = CENTRAL_DIR / ".askill-sources.json"


# ---------------------------------------------------------------- io

def load_sources() -> dict:
    """Load the sources registry; {} when missing or corrupt."""
    try:
        if SOURCES_FILE.exists():
            return json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    return {}


def save_sources(data: dict) -> None:
    """Persist the sources registry (utf-8, stable formatting)."""
    SOURCES_FILE.parent.mkdir(parents=True, exist_ok=True)
    SOURCES_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def record_source(
    skill_name: str,
    repo_url: str,
    sub_path: str = "",
    branch: Optional[str] = None,
    commit: Optional[str] = None,
) -> None:
    """Record (or overwrite) the origin of one skill."""
    data = load_sources()
    data[skill_name] = {
        "repo_url": repo_url.rstrip("/"),
        "sub_path": sub_path,
        "branch": branch,
        "commit": commit,
        "installed_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%S"),
    }
    save_sources(data)


def remove_source(skill_name: str) -> None:
    """Drop the tracking entry for a removed skill."""
    data = load_sources()
    if skill_name in data:
        del data[skill_name]
        save_sources(data)


# ---------------------------------------------------------------- update

def _latest_commit(repo_url: str, branch: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Fetch the remote HEAD commit sha (and resolved branch) via ls-remote.

    Returns (sha, branch) - (None, None) on network/git failure.
    """
    cmd = ["git", "ls-remote", repo_url]
    if branch:
        cmd += [branch]
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=60,
        )
        if r.returncode != 0:
            return None, None
        for line in r.stdout.splitlines():
            sha, ref = line.split("\t", 1)
            ref = ref.strip()
            if ref.startswith("refs/heads/") or ref == "HEAD":
                resolved = ref.removeprefix("refs/heads/")
                return sha, resolved
        return None, None
    except (subprocess.TimeoutExpired, OSError):
        return None, None


def check_update(skill_name: str) -> dict:
    """Check one skill for a remote update.

    Returns dict: {skill, status, remote_commit?, local_commit?, branch?}
    status: tracked | untracked | missing | up-to-date | update-available | error
    """
    sources = load_sources()
    info = sources.get(skill_name)
    if not info:
        return {"skill": skill_name, "status": "untracked"}
    skill_dir = CENTRAL_DIR / skill_name
    if not skill_dir.exists():
        return {"skill": skill_name, "status": "missing"}

    sha, branch = _latest_commit(info["repo_url"], info.get("branch"))
    if not sha:
        return {"skill": skill_name, "status": "error"}

    local = info.get("commit")
    # The previous ``if local and sha.startswith(local) or local == sha``
    # relied on Python's ``A and B or C`` short-circuit; it happened to be
    # correct in practice (``sha`` is always a non-empty hex hash from
    # ``_latest_commit``) but the mixed-priority chain is easy to break in
    # future edits. Spell the predicate out so the intent is unambiguous
    # and the unrecorded (``local is None``) boundary is explicit.
    if local:
        is_up_to_date = sha.startswith(local) or local == sha
    else:
        is_up_to_date = False
    if is_up_to_date:
        return {
            "skill": skill_name, "status": "up-to-date",
            "remote_commit": sha[:8], "branch": branch or info.get("branch"),
        }
    return {
        "skill": skill_name, "status": "update-available",
        "remote_commit": sha[:8], "local_commit": (local or "?")[:8],
        "branch": branch or info.get("branch"),
    }


def check_all_updates() -> list[dict]:
    """Check every tracked skill; untracked skills are listed once at the end."""
    sources = load_sources()
    results = [check_update(name) for name in sorted(sources)]
    return results


def update_skill(skill_name: str, verbose: bool = True) -> bool:
    """Re-install one skill from its recorded origin and re-sync everywhere.

    The old directory is replaced atomically-ish (moved aside first).
    """
    import shutil
    import tempfile

    sources = load_sources()
    info = sources.get(skill_name)
    if not info:
        if verbose:
            print(f"No source recorded for '{skill_name}' (installed locally?)")
        return False

    url = info["repo_url"]
    if info.get("sub_path"):
        url = f"{url}/tree/{info.get('branch') or 'HEAD'}/{info['sub_path']}"
    elif info.get("branch"):
        url = f"{url}/tree/{info['branch']}"

    skill_dir = CENTRAL_DIR / skill_name
    if skill_dir.exists():
        with tempfile.TemporaryDirectory() as tmp:
            shutil.move(str(skill_dir), str(Path(tmp) / "old"))
        if verbose:
            print(f"Removed old version of '{skill_name}'")

    # reuse the URL installer so behaviour (incl. source recording) matches
    from .sync import _install_from_url, sync_skill
    name, ok = _install_from_url(url, verbose=verbose)
    if not ok or name != skill_name:
        if verbose:
            print(f"Update failed for '{skill_name}'")
        return False

    # stamp the new commit
    sha, _ = _latest_commit(info["repo_url"], info.get("branch"))
    record_source(
        skill_name, info["repo_url"], info.get("sub_path", ""),
        info.get("branch"), sha,
    )
    sync_skill(skill_name, verbose=verbose)
    if verbose:
        print(f"Updated '{skill_name}' and synced to all products.")
    return True
