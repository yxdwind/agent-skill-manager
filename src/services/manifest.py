"""Team manifest sync: export the central skill list, align another machine.

``askill bundle`` writes ``askill-manifest.json``: every central-repo skill
with its name plus - when sources tracking has it - the origin needed to
reinstall.  ``askill install --manifest PATH`` aligns the local central
repo to that list: missing skills are installed from their recorded
origin, present ones are reported, skills without a usable source are
listed for manual handling.

The manifest is deliberately human-readable JSON so it can be committed
to a team repository and reviewed like code.  Zero network on bundle;
install touches the network only for git-sourced skills that are missing.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..config.products import CENTRAL_DIR
from .inventory import list_skills
from .sources import load_sources
from .sync.install import _install_from_url

MANIFEST_NAME = "askill-manifest.json"
MANIFEST_VERSION = 1

__all__ = ["MANIFEST_NAME", "MANIFEST_VERSION", "bundle_manifest", "install_manifest"]


def bundle_manifest(
    output: Path | None = None,
    central: Path | None = None,
    verbose: bool = True,
) -> Path:
    """Write the manifest for the central repository.

    Args:
        output: where to write (default: ``<central-parent>/askill-manifest.json``).
        central: override the central repository (tests).
        verbose: print a one-line summary.

    Returns:
        Path of the written manifest.
    """
    base = Path(central) if central is not None else CENTRAL_DIR
    sources = load_sources()
    skills: list[dict] = []
    for d in list_skills(base):
        info = sources.get(d.name)
        source = None
        if info and info.get("repo_url"):
            source = {
                "kind": "git",
                "repo_url": info["repo_url"],
                "sub_path": info.get("sub_path") or "",
                "branch": info.get("branch"),
            }
        skills.append({"name": d.name, "source": source})

    manifest = {
        "version": MANIFEST_VERSION,
        "generated_by": "askill",
        "skills": skills,
    }
    out = Path(output) if output is not None else base.parent / MANIFEST_NAME
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if verbose:
        tracked = sum(1 for s in skills if s["source"])
        print(f"Manifest written: {out}")
        print(f"  {len(skills)} skill(s), {tracked} with reinstall source")
    return out


def install_manifest(
    path: Path,
    central: Path | None = None,
    verbose: bool = True,
) -> dict:
    """Align the local central repository to a manifest.

    Missing skills are installed from their recorded git origin (network
    only for those); present skills are reported; skills without a usable
    source are returned in ``manual`` for the human to place by hand.

    Returns:
        ``{"ok", "error", "installed", "present", "failed", "manual"}``.
        ``ok`` is False only when the manifest itself cannot be read or is
        an unsupported version; per-skill problems surface in the lists.
    """
    report: dict = {
        "ok": True, "error": None,
        "installed": [], "present": [], "failed": [], "manual": [],
    }
    p = Path(path)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        report["ok"] = False
        report["error"] = f"cannot read manifest: {e}"
        return report
    if data.get("version") != MANIFEST_VERSION:
        report["ok"] = False
        report["error"] = (
            f"unsupported manifest version {data.get('version')!r} "
            f"(expected {MANIFEST_VERSION})"
        )
        return report

    base = Path(central) if central is not None else CENTRAL_DIR
    base.mkdir(parents=True, exist_ok=True)

    for entry in data.get("skills", []):
        name = entry.get("name")
        if not name:
            continue
        dest = base / name
        if dest.exists():
            report["present"].append(name)
            if verbose:
                print(f"  {name}: already in central repo")
            continue
        source = entry.get("source") or {}
        if source.get("kind") != "git" or not source.get("repo_url"):
            report["manual"].append((name, "no reinstall source recorded"))
            if verbose:
                print(f"  {name}: no source recorded - install manually")
            continue
        url = source["repo_url"]
        if source.get("sub_path"):
            url = f"{url}/tree/{source.get('branch') or 'HEAD'}/{source['sub_path']}"
        elif source.get("branch"):
            url = f"{url}/tree/{source['branch']}"
        if verbose:
            print(f"  {name}: installing from {url}")
        try:
            installed_name, ok = _install_from_url(url, verbose=verbose)
        except Exception as e:  # network/git failures must not abort the run
            installed_name, ok = None, False
            if verbose:
                print(f"  {name}: install error: {e}")
        if ok and installed_name:
            report["installed"].append(installed_name)
        else:
            report["failed"].append((name, "install failed (see output above)"))
    return report
