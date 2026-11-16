"""Derive a repair plan from a ``doctor`` report (P1-7).

This module is **pure**: it never touches the filesystem, never invokes sync,
and never imports the sync package. It only classifies what ``doctor`` already
found into (a) actions ``--apply`` may execute and (b) actions that need a
human. Execution lives in the CLI so the read-only guarantee of
``services/doctor.py`` stays intact.

Classification of a dead link is the same rule ``gc_dead_links`` uses:
a dead link whose name still exists in the central repo is re-linkable by a
normal ``askill sync``; one whose name is gone is stale and belongs to
``askill sync --gc``. Real directories are never repairable automatically -
they are drift/adopt territory.
"""

from __future__ import annotations

from typing import Any

__all__ = ["build_fix_plan", "render_plan"]


def build_fix_plan(
    report: dict[str, Any],
    central_names: set[str] | None = None,
) -> dict[str, Any]:
    """Return a machine-readable repair plan derived from a doctor report."""
    names = central_names or set()
    actions: list[dict[str, Any]] = []
    manual: list[dict[str, str]] = []

    relink: list[str] = []
    stale: list[str] = []
    for row in report.get("products", []):
        short = row.get("short", "?")
        for name in row.get("broken_names") or []:
            target = f"{short}/{name}"
            (relink if name in names else stale).append(target)

    if relink:
        actions.append({
            "id": "relink",
            "command": "askill sync",
            "auto": True,
            "reason": "dead link(s) still named after a central skill - a normal sync reconnects them",
            "items": sorted(relink),
        })
    if stale:
        actions.append({
            "id": "gc",
            "command": "askill sync --gc",
            "auto": True,
            "reason": "dead link(s) with no matching central skill - safe to remove",
            "items": sorted(stale),
        })

    locked = [
        row.get("short", "?") for row in report.get("products", [])
        if row.get("settings_writable") is False
    ]
    if locked:
        manual.append({
            "id": "settings-locked",
            "command": "close the running IDE, then re-run: askill sync",
            "reason": "settings.json is locked; sync can create links but cannot enable the skill",
            "items": ", ".join(sorted(locked)),
        })

    orphans = report.get("central", {}).get("orphan_sources") or []
    if orphans:
        manual.append({
            "id": "orphan-sources",
            "command": "edit .askill-sources.json in the central repo",
            "reason": "source-tracking entries without a matching skill",
            "items": ", ".join(orphans),
        })

    drift = [
        row.get("short", "?") for row in report.get("products", [])
        if (row.get("fork_dirs") or 0) > 0
    ]
    if drift:
        manual.append({
            "id": "drift-candidates",
            "command": "askill drift (then askill adopt or askill sync --force)",
            "reason": "real directories shadow central skills - never overwritten automatically",
            "items": ", ".join(sorted(drift)),
        })

    if not report.get("central", {}).get("exists", True):
        manual.append({
            "id": "missing-central",
            "command": "askill install <source>",
            "reason": "central repository does not exist yet",
            "items": "",
        })

    for check in report.get("checks", []):
        if check.get("severity") == "fail":
            manual.append({
                "id": f"env:{check.get('id', '?')}",
                "command": "fix the environment, then re-run: askill doctor",
                "reason": check.get("detail", ""),
                "items": "",
            })

    manual.append({
        "id": "rollbacks",
        "command": "askill rollback --list",
        "reason": "snapshots taken before each update are available if a new version misbehaves",
        "items": "",
    })

    return {
        "actions": actions,
        "manual": manual,
        "auto_count": len(actions),
        "manual_count": len(manual),
        "noop": not actions,
    }


def render_plan(plan: dict[str, Any], *, applying: bool = False) -> str:
    """Human-readable plan. ``applying`` only changes the header wording."""
    mode = "applying repair plan" if applying else "repair plan (dry-run, no changes made)"
    lines = [f"askill doctor --fix - {mode}", ""]
    if plan["noop"]:
        lines.append("  No automatic repairs needed: no stale or re-linkable dead links found.")
    for action in plan["actions"]:
        lines.append(f"  [auto]   {action['command']}")
        lines.append(f"           {action['reason']}")
        items = action["items"]
        if items:
            lines.append(f"           affected: {', '.join(items[:6])}"
                         + (" ..." if len(items) > 6 else ""))
    if plan["manual"]:
        lines += ["", "  Manual steps (never executed automatically):"]
        for item in plan["manual"]:
            lines.append(f"    - {item['id']}: {item['command']}")
            if item["items"]:
                lines.append(f"      affected: {item['items']}")
            if item["reason"]:
                lines.append(f"      why: {item['reason']}")
    lines += ["", "  Real directories are never overwritten; use drift/adopt/--force explicitly."]
    return "\n".join(lines)
