"""skills.sh ecosystem integration (v0.11.0).

skills.sh (by Vercel Labs) is the de-facto registry of the open Agent
Skills ecosystem (agentskills.io).  This module gives askill first-class,
stdlib-only access to it:

- :func:`search_skills` - query the public skills.sh search API
- :func:`resolve_source` - normalize ecosystem shorthand sources to GitHub
- :func:`find_skill_dir` - locate one skill's directory inside a cloned repo

Shorthand source formats accepted by ``askill install`` (mirroring the
``npx skills`` CLI so every command documented on skills.sh works verbatim):

    owner/repo                          -> https://github.com/owner/repo
    owner/repo@skill                    -> same, then pick the ``skill`` dir
    https://skills.sh/owner/repo/skill  -> same as owner/repo@skill

Plain GitHub URLs and local paths keep working exactly as before.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SKILLS_SH_API = "https://skills.sh/api/search"
USER_AGENT = "askill (+https://github.com/yxdwind/agent-skill-manager)"
REQUEST_TIMEOUT_S = 15

# owner/repo or owner/repo@skill - the drive-letter colon of Windows paths
# (C:/...) never matches, so local paths stay local.
_SHORTHAND_RE = re.compile(
    r"^([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)(?:@([A-Za-z0-9_.-]+))?$"
)


class RegistryError(RuntimeError):
    """skills.sh registry unreachable or returned an unusable response."""


# ---------------------------------------------------------------- search

def search_skills(query: str, limit: int = 10, timeout: float = REQUEST_TIMEOUT_S) -> list[dict]:
    """Search the skills.sh registry.

    Returns a list of ``{"source", "skill_id", "name", "installs"}`` dicts,
    best match first.  Raises :class:`RegistryError` on network/API failure
    so callers can fall back or report cleanly.
    """
    url = f"{SKILLS_SH_API}?q={urllib.parse.quote(query.strip())}"
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise RegistryError(f"skills.sh unreachable: {exc}") from exc

    results = []
    for item in data.get("skills", []):
        if not isinstance(item, dict):
            continue
        results.append({
            "source": item.get("source", ""),
            "skill_id": item.get("skillId", ""),
            "name": item.get("name") or item.get("skillId", ""),
            "installs": int(item.get("installs", 0) or 0),
        })
        if len(results) >= limit:
            break
    return results


# ---------------------------------------------------------------- resolve

def resolve_source(source: str) -> dict | None:
    """Normalize a skills.sh-ecosystem source into GitHub install parameters.

    Returns ``{"repo_url", "skill", "original"}`` for shorthand sources, or
    ``None`` when *source* is not ecosystem shorthand (caller then treats it
    as a local path or plain URL, unchanged).
    """
    src = source.strip()
    if "://" in src or src.startswith("git@"):
        # skills.sh page URLs: https://skills.sh/owner/repo[/skill]
        if "skills.sh/" in src:
            path = src.split("skills.sh/", 1)[1].strip("/")
            parts = [p for p in path.split("/") if p]
            if len(parts) >= 2:
                return {
                    "repo_url": f"https://github.com/{parts[0]}/{parts[1]}",
                    "skill": parts[2] if len(parts) > 2 else None,
                    "original": source,
                }
        return None

    match = _SHORTHAND_RE.match(src.strip("/"))
    if not match:
        return None
    return {
        "repo_url": f"https://github.com/{match.group(1)}/{match.group(2)}",
        "skill": match.group(3),
        "original": source,
    }


def find_skill_dir(repo_root: Path, skill_id: str) -> Path | None:
    """Locate the directory of one skill inside a cloned repo.

    Checked in order: ``<root>/<skill_id>``, ``<root>/skills/<skill_id>``,
    then a full scan for a directory named *skill_id* containing SKILL.md
    (the registry id carries no path information, so the layout varies).
    """
    for candidate in (repo_root / skill_id, repo_root / "skills" / skill_id):
        if (candidate / "SKILL.md").is_file():
            return candidate
    for skill_md in sorted(repo_root.rglob("SKILL.md")):
        if skill_md.parent.name == skill_id:
            return skill_md.parent
    return None
