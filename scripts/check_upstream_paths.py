#!/usr/bin/env python3
"""Read-only drift check between askill's declared paths and upstream tables.

Compares the portable paths exported by ``askill products --json --paths``
against two upstream registries:

* ``vercel-labs/skills`` ``docs/agents.md``  (columns: Agent / --agent / Project / Global)
* ``MichengAI/dsh-skills-manager`` ``README.md`` (columns: product / user path / env / project path)

Design rules (see ``docs/optimization-report-2026-11-15.md`` P1-6):

* **Never edits** ``src/config/products.py``. A drift is a finding for a human
  to verify, not an automatic change.
* Network failures are reported as ``unknown`` and **do not fail the run**;
  a scheduled job must never cry wolf or silently claim "no drift".
* Stdlib only. Local file inputs (``--agents FILE --dsh FILE``) make the whole
  check reproducible offline and in tests.

Examples:
    python scripts/check_upstream_paths.py
    askill products --json --paths > /tmp/paths.json
    python scripts/check_upstream_paths.py --input /tmp/paths.json \\
        --agents /tmp/agents.md --dsh /tmp/dsh.md --date 2026-11-15 \\
        --output upstream-path-report.md
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import urllib.request
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EXPORT_MODULE = REPO / "src" / "services" / "paths_export.py"

DEFAULT_AGENTS = (
    "https://raw.githubusercontent.com/vercel-labs/skills/main/docs/agents.md"
)
DEFAULT_DSH = (
    "https://raw.githubusercontent.com/MichengAI/dsh-skills-manager/master/README.md"
)


def load_helpers():
    """Load slug/name helpers without installing the package."""
    spec = importlib.util.spec_from_file_location("askill_paths_helpers", EXPORT_MODULE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load helpers at {EXPORT_MODULE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fetch(spec: str, timeout: float) -> tuple[str | None, str | None]:
    """Return ``(text, None)`` on success, ``(None, error)`` otherwise."""
    try:
        if spec.startswith(("http://", "https://")):
            request = urllib.request.Request(
                spec, headers={"User-Agent": "askill-path-check"},
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read().decode("utf-8", "replace"), None
        return Path(spec).read_text(encoding="utf-8"), None
    except Exception as exc:  # best-effort upstream probe; never fail the job
        return None, f"{type(exc).__name__}: {exc}"[:200]


def _label(cell: str) -> str:
    """Extract a product label, stripping DSH's inline <img> brand tags."""
    alt = re.search(r'alt="([^"]+)"', cell)
    if alt:
        return alt.group(1).strip()
    return re.sub(r"<[^>]+>", "", cell).strip()


def _looks_like_path(value: str) -> bool:
    return value.startswith(("~", "/", "%"))


def parse_table(text: str, layout: str) -> list[dict[str, str]]:
    """Parse ``(label, user-level path)`` pairs from an upstream table."""
    path_col = 3 if layout == "agents" else 1
    entries: list[dict[str, str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) <= path_col:
            continue
        label = _label(cells[0])
        if not label or label.lower() in {"agent", "产品", "---"}:
            continue
        literals = re.findall(r"`([^`]+)`", cells[path_col])
        raw = (literals or [cells[path_col]])[0].strip()
        if not _looks_like_path(raw):
            continue
        entries.append({"label": label, "path": raw})
    return entries


def _norm(path: str | None) -> str:
    """Normalise a path for comparison (trailing slash, separators)."""
    if not path:
        return ""
    return path.strip().strip("`").rstrip("/").replace("\\", "/")


def match_entries(record: dict, entries: list[dict[str, str]], helpers) -> list[dict]:
    """Conservative name match with an exact-match fast path.

    1. Exact slug equality wins. This prevents a merged ``Trae CN`` row from
       being attributed to the international ``Trae`` product.
    2. Only when no exact row exists, allow a contained slug (``kimi`` inside
       ``Kimi Code CLI``) or a long upstream slug as a prefix of ours
       (``qodercn`` -> ``qodercnide``). Short generic tokens cannot match
       *into* a record, so ``qwen-code`` never covers ``qwenwork``.
    """
    candidates = {
        helpers._slug(helpers._base_name(record["name"])),
        helpers._slug(record["short"]),
    }
    candidates.discard("")
    slugged = [(entry, helpers._slug(entry["label"])) for entry in entries]
    exact = [entry for entry, token in slugged if token and token in candidates]
    if exact:
        return exact
    return [
        entry for entry, token in slugged
        if token and any(
            c in token or (len(token) >= 6 and c.startswith(token))
            for c in candidates
        )
    ]


def build_report(
    records: list[dict],
    sources: list[tuple[str, str, str]],
    *,
    helpers,
    day: str,
    timeout: float,
) -> dict:
    """Run the comparison. Returns a JSON-serialisable report dict."""
    status = []
    drifts = []
    uncovered = []
    for name, spec, layout in sources:
        text, error = fetch(spec, timeout)
        if error:
            status.append({"source": name, "state": "unknown", "entries": 0, "error": error})
            continue
        # ``fetch`` guarantees text is not None when error is None.
        entries = parse_table(text or "", layout)
        status.append({"source": name, "state": "ok", "entries": len(entries), "error": ""})
        matched_shorts = set()
        for record in records:
            hits = match_entries(record, entries, helpers)
            if not hits:
                continue
            matched_shorts.add(record["short"])
            ours = _norm(record["macos_path"])
            theirs = sorted({_norm(h["path"]) for h in hits} - {""})
            if ours and theirs and ours not in theirs:
                drifts.append({
                    "source": name,
                    "product": record["name"],
                    "short": record["short"],
                    "ours": ours,
                    "upstream": theirs,
                    "matched_labels": sorted({h["label"] for h in hits}),
                })
        uncovered.append({
            "source": name,
            "shorts": sorted({r["short"] for r in records} - matched_shorts),
        })
    return {
        "date": day,
        "sources": status,
        "drifts": drifts,
        "uncovered": uncovered,
        "note": "Read-only. Verify each finding on a real install before editing products.py.",
    }


def render_markdown(report: dict) -> str:
    lines = [
        f"# 上游路径漂移复核（{report['date']}）",
        "",
        "> 只读检查：不修改 `src/config/products.py`。名称匹配是保守启发式，每条分歧都需真机复核后人工决策。",
        "",
        "## 数据源状态",
        "",
        "| 来源 | 状态 | 解析条目 | 备注 |",
        "|---|---|---:|---|",
    ]
    for s in report["sources"]:
        note = s["error"] or "—"
        lines.append(f"| `{s['source']}` | {s['state']} | {s['entries']} | {note} |")

    drifts = report["drifts"]
    lines += [
        "",
        f"## 路径分歧（{len(drifts)}）",
        "",
        "| 来源 | 产品 | short | 本项目 macOS 路径 | 上游路径 | 匹配到的上游条目 |",
        "|---|---|---|---|---|---|",
    ]
    if not drifts:
        lines.append("| — | 无 | — | — | — | — |")
    for d in drifts:
        labels = ", ".join(f"`{x}`" for x in d["matched_labels"])
        upstream = ", ".join(f"`{x}`" for x in d["upstream"])
        lines.append(
            f"| `{d['source']}` | {d['product']} | `{d['short']}` | `{d['ours']}` | "
            f"{upstream} | {labels} |"
        )

    lines += ["", "## 上游无同名条目（供人工判断：可能是不同产品，也可能是待补路径）", ""]
    for u in report["uncovered"]:
        shorts = ", ".join(f"`{s}`" for s in u["shorts"]) or "—"
        lines.append(f"- `{u['source']}`：{shorts}")
    lines += ["", f"> {report['note']}", ""]
    return "\n".join(lines)


def read_records(source: str | None) -> list[dict]:
    if source:
        text = (
            sys.stdin.read()
            if source == "-"
            else Path(source).read_text(encoding="utf-8")
        )
    else:
        exe = shutil.which("askill")
        if not exe:
            print(
                "error: `askill` not found. Run `pip install -e .`, or export "
                "`askill products --json --paths > paths.json` and use --input.",
                file=sys.stderr,
            )
            raise SystemExit(2)
        proc = subprocess.run(
            [exe, "products", "--paths"],
            capture_output=True, text=True, check=False,
        )
        if proc.returncode != 0:
            print(f"error: askill exited {proc.returncode}: {proc.stderr.strip()}",
                  file=sys.stderr)
            raise SystemExit(proc.returncode)
        text = proc.stdout
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        print(f"error: expected a JSON array from `products --paths`: {exc}",
              file=sys.stderr)
        raise SystemExit(1) from exc
    if not isinstance(data, list):
        print("error: expected a JSON array of product records", file=sys.stderr)
        raise SystemExit(1)
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agents", default=DEFAULT_AGENTS,
                        help="Local file or URL of npx skills docs/agents.md")
    parser.add_argument("--dsh", default=DEFAULT_DSH,
                        help="Local file or URL of dsh-skills-manager README.md")
    parser.add_argument("--input", metavar="FILE|-",
                        help="Pre-exported `products --paths` JSON")
    parser.add_argument("--output", metavar="FILE", help="Write report to a file")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="Emit JSON instead of Markdown")
    parser.add_argument("--date", metavar="YYYY-MM-DD", help="Override report date")
    parser.add_argument("--timeout", type=float, default=15.0,
                        help="Per-source network timeout in seconds")
    args = parser.parse_args(argv)

    helpers = load_helpers()
    records = read_records(args.input)
    sources = [
        ("npx-skills", args.agents, "agents"),
        ("dsh", args.dsh, "dsh"),
    ]
    report = build_report(
        records, sources, helpers=helpers,
        day=args.date or date.today().isoformat(), timeout=args.timeout,
    )
    output = (
        json.dumps(report, ensure_ascii=False, indent=2)
        if args.as_json else render_markdown(report)
    ) + "\n"
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"wrote {args.output} ({len(report['drifts'])} drifts)")
    else:
        sys.stdout.write(output)
    # Findings are informational: never fail a scheduled check on drift or
    # on an unreachable upstream (that would be a false alarm).
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
