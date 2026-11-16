#!/usr/bin/env python3
"""Render an upstream-ready agents.md fragment from askill's product registry.

Offline by default. Reads the declaration through ``askill products --paths``
(or ``--input`` from a file / stdin), then renders a markdown table suitable
for a PR against npx skills' ``docs/agents.md``.

``--upstream`` takes a *local snapshot* of that file (e.g. downloaded with
``curl``) and appends a "not covered upstream" section. The script itself
never touches the network — consistent with the project's offline-first
stance — and never submits anything to an external repository.

Examples:
    python scripts/export_agents_md.py
    askill products --json --paths > /tmp/askill-paths.json
    python scripts/export_agents_md.py --input /tmp/askill-paths.json \\
        --upstream /tmp/agents.md --date 2026-11-15 --output docs/agents-fragment.md
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EXPORT_MODULE = REPO / "src" / "services" / "paths_export.py"


def load_export_module():
    """Load the renderer without installing the package (fresh-clone friendly)."""
    spec = importlib.util.spec_from_file_location("askill_paths_export", EXPORT_MODULE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load renderer at {EXPORT_MODULE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_records(source: str | None) -> list[dict]:
    """Obtain the exported JSON array from a file, stdin, or the installed CLI."""
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
                "offline with `askill products --json --paths > paths.json` "
                "and pass --input paths.json.",
                file=sys.stderr,
            )
            raise SystemExit(2)
        proc = subprocess.run(
            [exe, "products", "--paths"],
            capture_output=True, text=True, check=False,
        )
        if proc.returncode != 0:
            print(
                f"error: askill exited {proc.returncode}: {proc.stderr.strip()}",
                file=sys.stderr,
            )
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
    parser.add_argument(
        "--input", metavar="FILE|-",
        help="Read a pre-exported JSON array instead of calling `askill`",
    )
    parser.add_argument(
        "--upstream", metavar="FILE",
        help="Local snapshot of npx skills docs/agents.md; append a gap report",
    )
    parser.add_argument(
        "--output", metavar="FILE",
        help="Write the fragment to a file instead of stdout",
    )
    parser.add_argument(
        "--date", metavar="YYYY-MM-DD",
        help="Override the export date (reproducible output for tests / diffs)",
    )
    args = parser.parse_args(argv)

    renderer = load_export_module()
    records = read_records(args.input)
    upstream = (
        Path(args.upstream).read_text(encoding="utf-8")
        if args.upstream else None
    )
    fragment = renderer.render_agents_md(
        records, upstream_text=upstream, generated_on=args.date,
    )

    if args.output:
        Path(args.output).write_text(fragment, encoding="utf-8")
        print(f"wrote {args.output} ({len(records)} products)")
    else:
        sys.stdout.write(fragment)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
