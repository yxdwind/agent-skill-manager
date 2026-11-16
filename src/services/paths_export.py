"""Machine-readable export of the declarative product registry.

Design constraints (see ``docs/optimization-report-2026-11-15.md`` P1-5):

* ``config/products.py`` stays the **only** source of truth. Every field here
  is derived from a ``ProductSpec``; nothing is hard-coded.
* Stdlib only, and **no intra-package imports**. The companion script
  ``scripts/export_agents_md.py`` loads this module by file path, so the export
  works from a fresh clone without ``pip install -e .`` and without dragging a
  package hierarchy into ``sys.path``.
* Absolute home paths are rendered as portable ``~/...`` / ``%LOCALAPPDATA%/...``
  strings — an upstream PR must never contain a maintainer's home directory.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from datetime import date
from pathlib import Path
from typing import Any

PLATFORMS = ("macos", "windows", "linux")
UPSTREAM_AGENTS_MD_URL = (
    "https://github.com/vercel-labs/skills/blob/main/docs/agents.md"
)


def _portable(path: Any, *, home: Path, localappdata: Path) -> str | None:
    """Render an absolute path as ``~/...`` / ``%LOCALAPPDATA%/...``.

    ``LOCALAPPDATA`` is checked first because on Windows it usually lives
    *under* the home directory; checking home first would hide it.
    Unknown roots fall back to the absolute POSIX form rather than being
    silently rewritten.
    """
    if path is None:
        return None
    p = Path(path)
    for prefix, label in ((localappdata, "%LOCALAPPDATA%"), (home, "~")):
        try:
            rel = p.relative_to(prefix)
        except (ValueError, TypeError):
            continue
        return label if str(rel) == "." else f"{label}/{rel.as_posix()}"
    return p.as_posix()


def build_path_records(
    products: Iterable[Mapping[str, Any]],
    *,
    home: Path,
    localappdata: Path,
) -> list[dict[str, Any]]:
    """Derive a full cross-platform, portable record per declared product."""
    def rel(value: Any) -> str | None:
        return _portable(value, home=home, localappdata=localappdata)

    records: list[dict[str, Any]] = []
    for p in products:
        records.append({
            "name": p.get("name", ""),
            "short": p.get("short", ""),
            "sync_method": p.get("sync_method", ""),
            "macos_path": rel(p.get("macos_path")),
            "windows_path": rel(p.get("windows_path")),
            "linux_path": rel(p.get("linux_path")),
            "extra_dirs": {
                plat: [rel(d) for d in (p.get(f"extra_dirs_{plat}") or [])]
                for plat in PLATFORMS
            },
            "settings_file": rel(p.get("settings_file")),
            "settings_mode": p.get("settings_mode"),
            "required_frontmatter": list(p.get("required_frontmatter") or []),
            "note": p.get("note", ""),
        })

    # ``shared_with`` is derived, never declared: two products sharing both
    # primary paths are directory aliases (Trae CN / TRAE SOLO CN, etc.).
    # Pack products have no paths and therefore never form a shared group.
    groups: dict[tuple[str | None, str | None], list[str]] = {}
    for rec in records:
        key = (rec["macos_path"], rec["windows_path"])
        if key[0] or key[1]:
            groups.setdefault(key, []).append(rec["short"])
    for rec in records:
        key = (rec["macos_path"], rec["windows_path"])
        rec["shared_with"] = [s for s in groups.get(key, []) if s != rec["short"]]
    return records


def _slug(value: str) -> str:
    """Normalise a product/agent label for conservative name matching."""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _base_name(name: str) -> str:
    """Drop company suffixes and aliases: ``Comate / Wenxin ...`` -> ``Comate``."""
    return name.split("/")[0].split("(")[0].strip()


def parse_upstream_agents(text: str) -> set[str]:
    """Extract normalised agent labels from an upstream ``agents.md`` table.

    Only the first three columns of markdown table rows are considered
    (agent name, ``--agent`` identifiers, project path); backticked literals
    are indexed separately so ``trae-cn`` matches the ``Trae CN`` label.
    """
    tokens: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        for cell in cells[:3]:
            for literal in re.findall(r"`([^`]+)`", cell):
                slug = _slug(literal)
                if slug:
                    tokens.add(slug)
            slug = _slug(cell)
            if slug:
                tokens.add(slug)
    return tokens


def match_upstream(record: dict[str, Any], tokens: set[str]) -> str | None:
    """Return the upstream token that covers this record, or ``None``.

    Deliberately conservative: the record's base-name slug must equal a token
    or be contained in one (``kimi`` -> ``kimicodecli``). Short generic tokens
    are not allowed to match *into* a record, so ``qwen-code`` does not
    silently cover ``qwenwork``.
    """
    candidates = {_slug(_base_name(record["name"])), _slug(record["short"])}
    candidates.discard("")
    exact = sorted(token for token in tokens if token in candidates)
    if exact:
        return exact[0]
    # Multi-agent rows ("Cline, Kimi Code CLI, Zed, ...") produce one very
    # long token; prefer the shortest containing token so the gap report
    # shows `kimicodecli` rather than that whole merged cell.
    partial = [t for t in tokens if any(c in t for c in candidates)]
    return min(partial, key=lambda t: (len(t), t)) if partial else None


def render_agents_md(
    records: list[dict[str, Any]],
    *,
    upstream_text: str | None = None,
    generated_on: str | None = None,
) -> str:
    """Render a paste-ready upstream contribution fragment.

    ``upstream_text`` is an optional local snapshot of the upstream
    ``agents.md``; when supplied, a "not covered yet" section is appended so
    a PR author knows exactly which rows are worth proposing.
    """
    day = generated_on or date.today().isoformat()

    def cell(value: str | None) -> str:
        return f"`{value}`" if value else "—"

    lines = [
        f"# askill product paths (exported {day})",
        "",
        "> Source of truth: `src/config/products.py`, exported via `askill products --json --paths`.",
        f"> Intended for upstream contributions such as [npx skills agents.md]({UPSTREAM_AGENTS_MD_URL}).",
        "> Project Path is `—`: askill manages user-level directories only; project-level paths must be confirmed by the upstream maintainer.",
        "",
        "| Agent | `--agent` | Project Path | Global Path (macOS) | Global Path (Windows) | Linux | sync | shared_with | note |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in records:
        note = (r.get("note") or "").replace("|", "\\|")
        shared = ", ".join(r.get("shared_with") or []) or "—"
        lines.append(
            f"| {r['name']} | `{r['short']}` | — | {cell(r['macos_path'])} | "
            f"{cell(r['windows_path'])} | {cell(r['linux_path'])} | "
            f"{r['sync_method']} | {shared} | {note} |"
        )

    if upstream_text is not None:
        tokens = parse_upstream_agents(upstream_text)
        missing = [r for r in records if match_upstream(r, tokens) is None]
        lines += [
            "",
            f"## Not covered upstream ({len(missing)} of {len(records)}, snapshot {day})",
            "",
            "> Name matching is conservative and automatic — verify each row against the live upstream file before opening a PR.",
            "",
            "| Agent | short | Global Path (macOS) | Global Path (Windows) |",
            "|---|---|---|---|",
        ]
        for r in missing:
            lines.append(
                f"| {r['name']} | `{r['short']}` | {cell(r['macos_path'])} | "
                f"{cell(r['windows_path'])} |"
            )
        lines += ["", "Covered rows:", ""]
        for r in records:
            token = match_upstream(r, tokens)
            if token:
                lines.append(f"- `{r['short']}` → `{token}`")
    return "\n".join(lines) + "\n"
