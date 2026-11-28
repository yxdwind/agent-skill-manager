"""CLI entry point for agent-skill-manager."""

import argparse
import json
import platform
import shutil
import sys
from collections.abc import Callable
from pathlib import Path

from ..config.products import (
    CENTRAL_DIR,
    LOCALAPPDATA,
    PRODUCTS,
    get_all_product_dirs,
    get_product_path,
)
from ..services.audit import analyze_skill_dir
from ..services.ci_format import (
    audit_annotations,
    grades_failed,
    parse_fail_on,
    verify_annotations,
)
from ..services.doctor import doctor_report
from ..services.get import get_skill
from ..services.manifest import bundle_manifest, install_manifest
from ..services.overlap import overlap_rows, render_overlap
from ..services.paths_export import build_path_records
from ..services.publish import publish_skill
from ..services.remediation import build_fix_plan, render_plan
from ..services.scaffold import create_skill
from ..services.sync import (
    FOOTER,
    adopt_from_platform,
    audit_all,
    audit_skill,
    gc_dead_links,
    get_status,
    install_skill,
    list_skills,
    pack_skill,
    print_onboarding,
    remove_skill,
    residency_report,
    sync_skill,
)
from ..utils.filesystem import read_skill_metadata


def _print_product_paths():
    """Emit the full portable cross-platform declaration as JSON.

    Kept as a separate entry point so ``_print_products`` retains the
    long-standing signature that shell completion and tests patch against.
    """
    records = build_path_records(
        PRODUCTS, home=Path.home(), localappdata=LOCALAPPDATA,
    )
    print(json.dumps(records, ensure_ascii=False, indent=2))
    return 0


def _print_products(*, quiet=False, json_mode=False):
    """Print all supported products and their paths."""
    if json_mode:
        # Flatten per-product into JSON objects with the platform-relevant
        # resolved path / extra dirs and a one-letter sync_method. Stable
        # enough for downstream tools to consume.
        out = []
        for p in PRODUCTS:
            primary = get_product_path(p)
            out.append({
                "name": p["name"],
                "short": p["short"],
                "sync_method": p["sync_method"],
                "primary_path": str(primary) if primary else None,
                "extra_paths": [
                    str(d) for d in get_all_product_dirs(p)[1:]
                    if d is not None
                ],
                "note": p.get("note", ""),
            })
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    print(f"\n{'='*60}")
    print(f"Supported Products ({len(PRODUCTS)})")
    print(f"{'='*60}")
    if not quiet:
        print(f"Platform: {platform.system()}")
        print(f"Central repo: {CENTRAL_DIR}")
        print(f"{'='*60}\n")

    for p in PRODUCTS:
        print(f"  [{p['short']}] {p['name']}")
        if p["sync_method"] == "native":
            path = get_product_path(p)
            print(f"    Path: {path} (native, no sync needed)")
        elif p["sync_method"] == "pack":
            print("    Path: App-managed (use 'pack' command)")
        else:
            primary = get_product_path(p)
            if primary:
                exists = "[ok]" if primary.exists() else "[--]"
                print(f"    Path: {primary} {exists}")
            else:
                print("    Path: N/A on this platform (see note)")
        extra_dirs = get_all_product_dirs(p)
        for d in extra_dirs[1:]:
            exists = "[ok]" if d.exists() else "[--]"
            print(f"    Alt:  {d} {exists}")
        if p.get("note"):
            print(f"    Note: {p['note']}")
        print()


def _print_list(*, quiet=False, json_mode=False):
    """List all skills in the central repository."""
    skills = list_skills()
    if not skills:
        if json_mode:
            print(json.dumps([], ensure_ascii=False))
        elif not quiet:
            if not CENTRAL_DIR.exists():
                print(f"Central repository not found: {CENTRAL_DIR}")
            else:
                print(f"No skills found in {CENTRAL_DIR}")
            print_onboarding()
        return

    if json_mode:
        from ..services.spec import parse_frontmatter
        entries = []
        for s in skills:
            meta = read_skill_metadata(s)
            report = analyze_skill_dir(s)
            fields, _ = parse_frontmatter(
                (s / "SKILL.md").read_text(encoding="utf-8", errors="replace")
            )
            entries.append({
                "skill": s.name,
                "description": meta.get("description", ""),
                # publish-relevant frontmatter (None when absent) - lets
                # scripts spot skills that would fail the publish gate
                "version": fields.get("version"),
                "description_zh": fields.get("description_zh"),
                "audit_score": report["score"],
                "audit_grade": report["grade"],
                "audit_verdict": report["verdict"],
            })
        print(json.dumps(entries, ensure_ascii=False, indent=2))
        return

    print(f"\nSkills in central repository ({CENTRAL_DIR}):")
    print(f"{'-'*50}")
    verdict_icon = {"safe": "OK", "caution": "CAUTION", "risky": "RISKY", "dangerous": "DANGEROUS"}
    for s in skills:
        meta = read_skill_metadata(s)
        report = analyze_skill_dir(s)
        print(f"  {s.name}  [score {report['score']}/100 grade {report['grade']} {verdict_icon[report['verdict']]}]")
        if meta.get("description"):
            desc = meta["description"][:80]
            print(f"    -> {desc}...")
    print()


def _print_status_grouped(sn, by_skill, product_shorts, term_w, central):
    """Render one skill as a grouped block (v0.25.1, replaces the 6-char
    squeezed table when 15 products can not fit the terminal).

    Products are grouped by status with full (untruncated) short names,
    wrapped to the terminal width.  ``ok`` hides the per-product method
    (junction/link/native) - that detail lives in ``--json`` and in the
    wide-table mode; the value here is who has the skill and who does not.
    """
    import textwrap

    verdict_icon = {"safe": "OK", "caution": "CAUTION", "risky": "RISKY", "dangerous": "DANGEROUS"}
    print(f"\n{sn}")
    groups: dict[str, list[str]] = {}
    for ps in product_shorts:
        if ps in by_skill[sn]:
            status, _method = by_skill[sn][ps]
        else:
            status = "missing"
        groups.setdefault(status, []).append(ps)
    order = ["ok", "manual", "n/a", "conflict", "missing"]
    for status in order + [s for s in groups if s not in order]:
        names = groups.get(status)
        if not names:
            continue
        label = f"  {status} ({len(names)})".ljust(14)
        print(textwrap.fill(
            ", ".join(names),
            width=max(term_w, 60),
            initial_indent=label,
            subsequent_indent=" " * 14,
        ))
    skill_dir = Path(central) / sn
    if skill_dir.exists():
        report = analyze_skill_dir(skill_dir)
        print(f"  {'score'.ljust(14)}{report['score']}/{report['grade']} {verdict_icon[report['verdict']]}")


def _print_status(skill_name=None, *, quiet=False, json_mode=False):
    """Print installation status of skills across all products.

    Column widths adapt to fit the terminal:
    - skill name column: longest name in current results (cap 30, floor 10)
    - product cell:      12 chars
    - score column:      dropped first when the table gets too wide; the audit
                         verdict is the least actionable info once packed in
    - when even the score-less table can not fit (15 products on an 80-col
      terminal), the whole matrix switches to a grouped vertical layout:
      one block per skill, products listed by status with full short names
      (v0.25.1 - replaces the old 6-char truncated columns that squeezed
      'ok junction' into 'ok li…').

    Args:
        quiet: suppress non-essential output (banner, score column for
            empty central, etc.). Errors always print.
        json_mode: emit one JSON object (list of per-product StatusEntry
            records) instead of the formatted table.
    """
    results = get_status(skill_name)
    if not results:
        if json_mode:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        elif skill_name:
            print(f"Skill not found: {skill_name}")
        else:
            if not quiet:
                print("No skills found in central repository.")
                print_onboarding()
        return

    # Group results by skill (skill -> {product_short: (status, method)})
    verdict_icon = {"safe": "OK", "caution": "CAUTION", "risky": "RISKY", "dangerous": "DANGEROUS"}
    by_skill: dict[str, dict[str, tuple]] = {}
    order: list[str] = []
    for r in results:
        sn = r["skill_name"]
        if sn not in by_skill:
            by_skill[sn] = {}
            order.append(sn)
        by_skill[sn][r["product_short"]] = (r["status"], r["method"])

    product_shorts = [p["short"] for p in PRODUCTS]
    n_prod = len(product_shorts)

    # Column body widths (each column is rendered as " " + body, padded to body_w).
    skill_w = max((len(s) for s in order), default=5)
    skill_w = min(max(skill_w, 10), 30)
    cell_w = 12     # fits "ok junction" (11) + slack
    score_w = 13    # fits "100/A DANGEROUS"

    # Adapt to terminal width. Falls back to 120 cols when not a TTY
    # (piped to grep/cat/less) so the table stays usable in scripts.
    term_w = shutil.get_terminal_size((120, 20)).columns
    total = skill_w + (cell_w + 1) * n_prod + (score_w + 1)
    show_score = True
    if total > term_w:
        show_score = False
        total -= score_w + 1
    # v0.25.1: when even the score-less table can not fit, switch to the
    # grouped vertical layout instead of truncating every product cell to
    # 6 chars ('ok junction' became unreadable 'ok li…').
    grouped = total > term_w and not json_mode

    def _cell(label: str, n: int) -> str:
        """Format one cell as ' ' + label left-justified to n body chars
        (truncated with an ellipsis if the label is wider than n)."""
        if len(label) > n:
            label = label[: n - 1] + "\u2026"
        return f" {label:<{n}}"

    header = f"{'Skill':<{skill_w}}"
    for ps in product_shorts:
        header += _cell(ps, cell_w)
    if show_score:
        header += _cell("score", score_w)
    # quiet strips decoration (banner/header/footer) but keeps the data rows;
    # an orphan header with zero rows is worse than either.
    if not json_mode and not quiet and not grouped:
        print(f"\n{header}")
        print("-" * len(header))

    for sn in order:
        if grouped:
            _print_status_grouped(sn, by_skill, product_shorts, term_w, CENTRAL_DIR)
            continue
        row = f"{sn[:skill_w]:<{skill_w}}"
        for ps in product_shorts:
            if ps in by_skill[sn]:
                status, method = by_skill[sn][ps]
                if status == "ok":
                    cell = f"ok {method}"
                elif status == "missing":
                    cell = "--"
                elif status == "manual":
                    cell = "manual"
                elif status == "n/a":
                    cell = "n/a"
                else:
                    cell = status
            else:
                cell = "--"
            row += _cell(cell, cell_w)
        if show_score and not json_mode:
            skill_dir = CENTRAL_DIR / sn
            if skill_dir.exists():
                report = analyze_skill_dir(skill_dir)
                row += _cell(f"{report['score']}/{report['grade']} {verdict_icon[report['verdict']]}", score_w)
            else:
                row += _cell("n/a", score_w)
        if not json_mode:
            print(row)
    if not json_mode and not quiet:
        # A2 (health check 2026-10-31): explain degraded cells once, below
        # the table, instead of widening every cell.
        reasons = sorted({r["reason"] for r in results if r.get("reason")})
        if reasons:
            print(f"\n  note: {'; '.join(reasons)}")
    if json_mode:
        # Augment the StatusEntry rows with a per-skill audit score / verdict
        # so consumers don't have to re-read the central repo to render it.
        enriched: list[dict] = []
        for r in results:
            entry = dict(r)
            skill_dir = CENTRAL_DIR / str(entry["skill_name"])
            if skill_dir.exists():
                rep = analyze_skill_dir(skill_dir)
                entry["audit_score"] = rep["score"]
                entry["audit_grade"] = rep["grade"]
                entry["audit_verdict"] = rep["verdict"]
            enriched.append(entry)
        print(json.dumps(enriched, ensure_ascii=False, indent=2))
    elif not quiet:
        print(f"  --  {FOOTER}")
        print()


def _print_sync(skill_name=None, *, force=False, quiet=False, only=None, gc=False):
    if gc:
        gc_dead_links(verbose=not quiet)
        return 0
    """Sync skills and print results.

    ``quiet`` flips ``sync_skill(verbose=...)`` to False. Conflict +
    SECURITY WARNING prints stay untouched because they go through
    ``sync_skill`` directly.

    Returns 1 when a named skill was not found (exit-code contract),
    else 0 - per-product conflicts/failures are reported data, not a
    command failure.
    """
    results = sync_skill(skill_name, verbose=not quiet, force=force, only=only)
    return 1 if (skill_name and not results) else 0


def _print_install(source, sync=False, audit=False, no_audit=False, *, quiet=False, only=None):
    """Install a skill and print results. Returns 1 on failure."""
    ok = install_skill(source, sync=sync, audit=audit, no_audit=no_audit, verbose=not quiet,
                       only=only)
    return 0 if ok else 1


def _print_remove(skill_name, *, quiet=False):
    """Remove a skill and print results."""
    remove_skill(skill_name, verbose=not quiet)


def _print_pack(skill_name=None, *, quiet=False):
    """Pack a skill and print results. Returns 1 on failure."""
    return 0 if pack_skill(skill_name, verbose=not quiet) else 1


def _print_adopt(platform_short, skill_name=None, *, quiet=False):
    """Adopt skills from one platform to all others. Returns 1 on unknown platform."""
    from ..config.products import get_product_by_short
    if platform_short != "all" and get_product_by_short(platform_short) is None:
        print(f"Unknown platform: {platform_short}")
        print(f"Available: {', '.join(p['short'] for p in PRODUCTS)} (or 'all')")
        return 1
    adopt_from_platform(platform_short, skill_name, verbose=not quiet)
    return 0


def _print_audit(
    skill_name=None, *, quiet=False, json_mode=False,
    fail_on=None, gh_format=False,
):
    """Audit one or all skills and print reports.

    CI mode (``--format github`` / ``--fail-on``) gathers the machine-readable
    reports first so a grade gate can drive the exit code; the default human
    path is left byte-for-byte unchanged.
    """
    fail_on = fail_on or set()
    if json_mode or fail_on or gh_format:
        reports = (
            [audit_skill(skill_name, verbose=False)]
            if skill_name
            else audit_all(verbose=False)
        )
        reports = [r for r in reports if r is not None]
        failed = grades_failed(reports, fail_on)
        if json_mode:
            print(json.dumps(reports, ensure_ascii=False, indent=2))
            return 1 if failed else 0
        if gh_format:
            for line in audit_annotations(reports, fail_on=fail_on):
                print(line)
        elif not quiet:
            summary = ", ".join(f"{r['skill']}={r['grade']}" for r in reports) or "(none)"
            print(f"askill audit - {len(reports)} skill(s): {summary}")
        if failed and not quiet:
            print("  gate failed for: " + ", ".join(failed))
        return 1 if failed else 0
    if skill_name:
        audit_skill(skill_name, verbose=not quiet)
    else:
        audit_all(verbose=not quiet)


def _print_overlap(*, quiet=False, json_mode=False, threshold=0.6):
    """Deterministic description-overlap report (P1-9)."""
    rows = overlap_rows(CENTRAL_DIR, threshold=threshold)
    if json_mode:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    if not quiet:
        print(render_overlap(rows, threshold))
    return 0



_SUPPORTED_NAMES = ", ".join(p["name"] for p in PRODUCTS)

USAGE = f"""\
Agent Skill Manager - Cross-platform skill management for domestic AI agent products.

Supports {len(PRODUCTS)} products: {_SUPPORTED_NAMES}

Usage:
    askill status [skill-name]       Show installation status across products
    askill sync [skill-name]         Sync skill(s) to all products
        [--force]                    Overwrite differing real dirs (conflicts)
    askill list                      List skills in central repository
    askill install [--sync] <source> Install a skill, optionally sync to all
        [--audit] [--no-audit]       Sources: local path, GitHub URL, or
                                     skills.sh shorthand (owner/repo,
                                     owner/repo@skill, skills.sh URL).
                                     Spec + security checks run by default
    askill search <query> [--install N]  Search skills.sh; N installs that result
    askill new <name>                Scaffold a new skill (frontmatter
        [--target short] [--minimal] prefilled from product requirements)
    askill publish <skill> --repo owner/name   Publish to a git repo
        [--push] [--root] [--create] (default: dry run, additive subdir)
    askill verify [skill-name]       Check skills against the agentskills.io spec
                                     plus per-product frontmatter requirements
    askill remove <skill-name>       Remove a skill from all products
    askill pack <skill-name>         Package a skill as .zip for DuMate
    askill adopt <platform|all> [skill]  Adopt skills from one platform (or
                                     every product) into the central repo
    askill audit [skill-name]        Security audit of skill(s) in central repo
    askill watch                     Watch central repo; auto-sync changes
        [--interval N]               Poll/fallback seconds (native inotify /
                                     kqueue / ReadDirectoryChangesW events
                                     wake syncs instantly when available)
    askill update [skill-name]       Check/apply updates for tracked skills
    askill drift [product]           Report product-dir skills diverging
                                     from the central repo (new / differs)
    askill products [--paths]        List products / export portable paths as JSON
    askill version                   Show version

Exit codes: 0 success (incl. dry runs / empty results) · 1 operational
failure (install/verify/publish/... could not do its job) · 2 usage error.
"""


def main(argv=None):
    """CLI entry point.

    Args: pass an explicit argv for testability (defaults to ``sys.argv[1:]``).
    """
    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        print(USAGE)
        return

    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        # ``--help`` exits 0: argparse already wrote the message, stop
        # cleanly. Subparser usage errors raise SystemExit(2) directly
        # (exit_on_error does not propagate into subparsers), and that
        # code is the scripting-facing signal - re-raise it unchanged.
        if e.code not in (None, 0):
            raise
        return
    except argparse.ArgumentError as e:
        # Main-parser level validation failure (bad flag / unknown command).
        # For ``install`` we keep the project's usage block instead of
        # argparse's default error so users get the skills.sh shorthand
        # examples they expect. Usage errors must not exit 0 - scripts
        # pipe askill output and rely on exit codes to detect failure.
        if argv and argv[0] == "install":
            print(_INSTALL_HELP)
        else:
            print(f"Error: {e}")
        sys.exit(2)

    cmd = args.command

    # Global ``--version`` wins before anything else - command dispatch, the
    # ``cmd is None`` usage dump, and the first-run welcome (which we don't
    # want to print for a version query). Note the distinct dest
    # (``show_version``) declared at the parser - it must match here, and it
    # must NOT collide with ``new --version``'s ``version`` frontmatter attr.
    if getattr(args, "show_version", False):
        _print_version()
        return

    if cmd is None:
        print(USAGE)
        return

    quiet = bool(getattr(args, "quiet", False))
    json_mode = bool(getattr(args, "json_mode", False))
    # normalize onto the namespace so every dispatch entry can read them
    # directly (some subparsers don't declare --json; absence means False)
    args.quiet = quiet
    args.json_mode = json_mode

    # One-time first-run welcome (never in quiet/json/script modes).
    if cmd != "version":
        from ..services import welcome
        welcome.maybe_print_welcome(quiet=quiet, json_mode=json_mode)

    handler = _HANDLERS.get(cmd)
    if handler is None:
        print(f"Unknown command: {cmd}")
        print(USAGE)
        rc = 2
    else:
        # `watch` never returns; handlers returning None count as success.
        rc = handler(args) or 0

    # Exit-code contract: 0 success, 1 operational failure, 2 usage error.
    if rc:
        sys.exit(rc)


def _build_parser() -> argparse.ArgumentParser:
    """Build the argparse subcommand parser.

    The command definitions live in ``controllers/parsers`` (three command
    families). This wrapper stays here so ``main()`` and introspection keep a
    single stable entry point; all flags and registration order are unchanged.
    """
    from .parsers import build_parser

    return build_parser(len(PRODUCTS))



_INSTALL_HELP = """\
Usage: askill install [--sync] [--audit] [--no-audit] <source>
  Sources: local path, GitHub URL, or skills.sh shorthand:
    owner/repo                     e.g. anthropics/skills
    owner/repo@skill               e.g. anthropics/skills@pdf
    https://skills.sh/owner/repo/skill
  --sync      Also sync to all products after install
  --audit     Print the full audit report after install
  --no-audit  Skip the default spec + security checks
"""


def _cmd_drift(product_short, *, quiet=False, json_mode=False):
    """``askill drift [product]`` body (v0.16.0)."""
    from ..services.drift import find_drift
    report = find_drift(product_short)
    if report["error"]:
        print(f"Error: {report['error']}")
        return 1
    if json_mode:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    drifted = {s: e for s, e in report["products"].items() if e["new"] or e["differs"]}
    print(f"\nDrift scan ({_platform_label()}): {len(report['scanned'])} product(s) scanned\n")
    if not drifted:
        print("No drift - every real skill dir matches the central repo.")
        print()
        return 0
    for short, entry in drifted.items():
        print(f"  [{short}]")
        if entry["new"]:
            print(f"    new:     {', '.join(entry['new'])}")
        if entry["differs"]:
            print(f"    differs: {', '.join(entry['differs'])}")
    print()
    print("  new     -> askill adopt <product> [skill]   pull into central")
    print("  differs -> decide which side wins:")
    print("            askill sync <skill> --force        keep central, overwrite product")
    print("            (or copy the product version back into the central repo by hand)")
    print()
    return 0


def _platform_label() -> str:
    return {"Windows": "Windows", "Darwin": "macOS"}.get(platform.system(), platform.system())


def _cmd_new(name, targets, description, description_zh, version, minimal,
             *, quiet=False, json_mode=False):
    """``askill new <name>`` body (v0.15.0, docs/v0.15.0-plan.md R1)."""
    report = create_skill(
        name,
        targets=targets,
        description=description,
        description_zh=description_zh,
        version=version,
        minimal=minimal,
    )
    if json_mode:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["created"] else 1
    if report["error"]:
        print(f"Error: {report['error']}")
        return 1
    path = report["path"]
    fields = list(report["frontmatter"])
    spec = report["spec"] or {}
    spec_part = "spec PASS" if spec.get("ok") else "spec FAIL"
    if report["product_issues"]:
        spec_part = "spec FAIL (product frontmatter issues)"
    print(f"Created skill skeleton: {path}")
    if not quiet:
        print(f"  frontmatter: {', '.join(fields)}")
        print(f"  verify: {spec_part} (scaffold is compliant as generated)")
        print("Next steps:")
        print(f"  1. Edit SKILL.md in {path} - replace the TODO placeholders")
        print("  2. askill sync            distribute to all products")
        print(f"  3. askill verify {name}   re-check after your edits")


def _cmd_publish(name, repo, *, root=False, force=False, https=False,
                 create=False, push=False, targets=None, quiet=False):
    """``askill publish <skill> --repo owner/name`` body (v0.15.0 R2)."""
    report = publish_skill(
        name, repo,
        root=root, force=force, https=https, create=create, push=push,
        targets=targets,
        verbose=not quiet,
    )
    if report["error"]:
        print(f"Error: {report['error']}")
        for p in report.get("problems", []):
            print(f"  gate: {p}")
        return 1
    if report.get("risky"):
        print("  !! CAUTION: audit flagged this skill (risky/caution) - review before sharing")
    if not report["ok"]:
        return
    if not push:
        print("dry run complete - nothing was pushed. Re-run with --push to publish.")
        return
    entry = report["published"]
    skill, repo_name = entry["skill"], entry["repo"]
    print(f"Published: {skill} -> {entry['url']} ({entry['layout']} layout, {entry['commit']})")
    if entry["layout"] == "root":
        print(f"Install with:   askill install {repo_name}")
        print(f"          or:   npx skills add {repo_name}")
    else:
        print(f"Install with:   askill install {repo_name}@{skill}")
        print(f"          or:   npx skills add {repo_name} --skill {skill}")
    print("skills.sh lists repos automatically once installs happen (no publish API).")


def _cmd_search(query_parts, install_idx, *, quiet=False, json_mode=False):
    """``askill search`` body; extracted from main() so it stays readable."""
    from ..services.registry import RegistryError, search_skills
    if not query_parts:
        if json_mode:
            print(json.dumps({"error": "missing query"}))
        elif not quiet:
            print("Usage: askill search <query> [--install N]")
            print("  e.g. askill search pdf --install 1")
        return
    query = " ".join(query_parts)
    try:
        results = search_skills(query)
    except RegistryError as e:
        if json_mode:
            print(json.dumps({"error": f"skills.sh unreachable: {e}"}))
        elif not quiet:
            print(f"skills.sh registry unavailable: {e}")
        return 1
    if not results:
        if json_mode:
            print(json.dumps({"query": query, "results": []}, ensure_ascii=False))
        elif not quiet:
            print(f"No skills found for {query!r} on skills.sh.")
        return
    if json_mode:
        # Validate --install BEFORE emitting anything so stdout stays a
        # single parseable JSON document (an error doc appended after the
        # results doc would produce an unparseable concatenated stream).
        if install_idx is not None and not (1 <= install_idx <= len(results)):
            print(json.dumps({"error": f"--install {install_idx} out of range 1-{len(results)}"}))
            return 1
        print(json.dumps({"query": query, "results": results}, ensure_ascii=False, indent=2))
        # ``--install N`` inside JSON mode is unusual; we honour it but skip
        # the human-friendly "Installing result #N" line so the stdout
        # stream is parseable JSON only. Caveat: install-time SECURITY
        # WARNING / [product] prints are unconditional by design and can
        # still appear after the JSON document.
        if install_idx is not None:
            pick = results[install_idx - 1]
            install_skill(f"{pick['source']}@{pick['skill_id']}", verbose=False)
        return

    print(f"\nskills.sh results for {query!r}:")
    print(f"{'-'*70}")
    for n, r in enumerate(results, start=1):
        label = f"{r['source']}@{r['skill_id']}"
        if len(label) > 52:
            label = label[:49] + "..."
        installs = f"{r['installs']:,}" if r["installs"] else "-"
        print(f"  {n}. {label:<50} {installs:>10} installs")
        if r["name"] != r["skill_id"]:
            print(f"     {r['name'][:70]}")
    print()
    top = results[0]
    print(f"Install one:  askill install {top['source']}@{top['skill_id']}")
    print(f"         or:  askill search {query} --install 1")
    print()
    if install_idx is None:
        return 0
    if install_idx < 1 or install_idx > len(results):
        print(f"Invalid --install index: pick 1-{len(results)}")
        return 1
    pick = results[install_idx - 1]
    print(f"Installing result #{install_idx}: {pick['source']}@{pick['skill_id']}")
    install_skill(f"{pick['source']}@{pick['skill_id']}", verbose=not quiet)
    print("\nRun 'askill sync' to distribute, or 'askill watch' to auto-sync.")


def _cmd_verify(skill_name, *, quiet=False, json_mode=False, fmt="table"):
    """``askill verify [skill-name]`` body."""
    from ..services.spec import (
        check_all_specs,
        check_spec,
        product_frontmatter_issues,
    )
    target_dir = None
    if skill_name:
        skill_dir = CENTRAL_DIR / skill_name
        if not skill_dir.exists():
            if json_mode:
                print(json.dumps({"error": f"skill not found: {skill_name}"}))
            elif not quiet:
                print(f"Skill not found in central repo: {skill_name}")
            return
        target_dir = skill_dir
        reports = [check_spec(skill_dir)]
    else:
        reports = check_all_specs(CENTRAL_DIR)
    if not reports:
        if json_mode:
            print(json.dumps({"results": [], "product_issues": []}))
        elif not quiet:
            print("No skills found in central repository.")
        return

    if target_dir is not None:
        product_issues = [(target_dir.name, product_frontmatter_issues(target_dir))]
    else:
        product_issues = [
            (d.name, product_frontmatter_issues(d)) for d in list_skills()
        ]
    flagged = [(sn, iss) for sn, iss in product_issues if iss]
    if fmt == "github":
        if json_mode:
            print("Error: --format github cannot be combined with --json",
                  file=sys.stderr)
            return 2
        for line in verify_annotations(reports, flagged, central=CENTRAL_DIR):
            print(line)
        return 1 if any(not r["ok"] for r in reports) else 0
    if json_mode:
        print(json.dumps({
            "results": reports,
            "product_issues": flagged,
        }, ensure_ascii=False, indent=2))
        return

    passed = 0
    print(f"\nAgent Skills spec check (agentskills.io) - {len(reports)} skill(s):\n")
    for r in reports:
        icon = "PASS" if r["ok"] else "FAIL"
        print(f"  [{icon}] {r['skill']}")
        for e in r["errors"]:
            print(f"        error:   {e}")
        for w in r["warnings"]:
            print(f"        warning: {w}")
        passed += 1 if r["ok"] else 0
    print(f"\n{passed}/{len(reports)} skill(s) ready for the skills.sh ecosystem.")
    if passed < len(reports):
        print("Fix the errors above so agents and skills.sh can index the skill.")
        rc = 1
    else:
        rc = 0
    if flagged:
        print("\nProduct-specific frontmatter requirements:\n")
        for sn, iss in flagged:
            for issue in iss:
                print(f"  [{sn}] {issue}")
        print("  Add the fields above to the skill's SKILL.md frontmatter;")
        print("  affected products will not load the skill until then.")
    else:
        print("All per-product frontmatter requirements satisfied.")
    print()
    return rc


def _cmd_update(skill_name, check_only, *, quiet=False, json_mode=False):
    """``askill update [skill-name] [--check]`` body."""
    from ..services.sources import (
        check_all_updates,
        check_update,
        update_skill,
    )
    if check_only:
        if skill_name:
            result = check_update(skill_name)
            if json_mode:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            elif not quiet:
                status = result["status"]
                skill = result["skill"]
                if status == "up-to-date":
                    print(f"{skill}: up-to-date ({result.get('branch', '')})")
                elif status == "update-available":
                    print(
                        f"{skill}: UPDATE {result.get('local_commit')} -> "
                        f"{result.get('remote_commit')} ({result.get('branch', '')})"
                    )
                elif status == "untracked":
                    print(f"{skill}: untracked (no source recorded - installed locally)")
                elif status == "missing":
                    print(f"{skill}: missing (skill directory not found in central repo)")
                elif status == "error":
                    print(f"{skill}: error (remote unreachable / git failed)")
                else:
                    print(f"{skill}: {status}")
            return
        results = check_all_updates()
        if json_mode:
            print(json.dumps(results, ensure_ascii=False, indent=2))
            return
        if not quiet:
            print("Update check (askill update --check)\n")
            print("  status legend:")
            print("    up-to-date       local matches the tracked remote")
            print("    update-available newer commit available on the remote")
            print("    untracked        no source recorded (installed locally)")
            print("    missing          skill directory gone from the central repo")
            print("    error            remote unreachable / git failed")
            print()
            for r in results:
                status = r["status"]
                skill = r["skill"]
                if status == "up-to-date":
                    print(f"  {skill:<28} up-to-date ({r.get('branch', '')})")
                elif status == "update-available":
                    print(
                        f"  {skill:<28} UPDATE {r.get('local_commit')} -> "
                        f"{r.get('remote_commit')} ({r.get('branch', '')})"
                    )
                elif status == "untracked":
                    print(f"  {skill:<28} untracked")
                elif status == "missing":
                    print(f"  {skill:<28} missing (skill dir gone)")
                elif status == "error":
                    print(f"  {skill:<28} remote unreachable")
                else:
                    print(f"  {skill:<28} {status}")
            if not results:
                print("  no tracked skills (install via GitHub URL to enable tracking)")
        return
    if skill_name:
        update_skill(skill_name)
        return
    results = check_all_updates()
    if not results:
        if json_mode:
            print(json.dumps({"tracked_skills": []}))
        elif not quiet:
            print("No tracked skills (install via GitHub URL to enable tracking).")
        return
    pending = [r["skill"] for r in results if r["status"] == "update-available"]
    if not pending:
        if json_mode:
            print(json.dumps({"pending_updates": []}))
        elif not quiet:
            print("All tracked skills are up to date.")
        return
    if json_mode:
        # json_mode applies; perform the update and emit the planned list
        # instead of running the side-effect-heavy updater.
        print(json.dumps({"pending_updates": pending}, ensure_ascii=False, indent=2))
        return
    print(f"Updating {len(pending)} skill(s): {', '.join(pending)}")
    for name in pending:
        update_skill(name, verbose=not quiet)


# ---------------------------------------------------------------- dispatch
# Command -> handler table (health check 2026-10-31 §9). Each handler takes
# the parsed Namespace and returns an exit code (None counts as success).
# `--version` / the welcome banner are handled in main() before this runs;
# main() normalizes args.quiet/args.json_mode for uniform access below.


def _print_version() -> None:
    from .. import __version__

    print(f"agent-skill-manager v{__version__}")


def _dispatch_install(args: argparse.Namespace) -> int:
    if args.manifest:
        return _cmd_install_manifest(args.manifest, quiet=args.quiet)
    # nargs="?" lets a missing <source> parse fine; keep the project's
    # shorthand examples here instead of crashing in resolve_source(None).
    if args.source is None:
        print(_INSTALL_HELP)
        sys.exit(2)
    return _print_install(
        args.source, sync=args.sync, audit=args.audit,
        no_audit=args.no_audit, quiet=args.quiet, only=args.only,
    )


def _cmd_bundle(args: argparse.Namespace) -> int:
    try:
        bundle_manifest(
            output=Path(args.output) if args.output else None,
            verbose=not args.quiet,
            external_only=getattr(args, "external_only", False),
        )
    except OSError as e:
        print(f"Error: {e}")
        return 1
    return 0


def _cmd_get(args: argparse.Namespace) -> int:
    return get_skill(
        args.source,
        to_dir=args.dir,
        list_only=args.list,
        verbose=not args.quiet,
    )


def _cmd_doctor(args: argparse.Namespace) -> int:
    fix = getattr(args, "fix", False)
    apply_repairs = getattr(args, "apply", False)
    if apply_repairs and not fix:
        print("Error: --apply requires --fix", file=sys.stderr)
        return 2
    if fix:
        return _cmd_doctor_fix(args, apply_repairs)
    if args.json_mode:
        print(json.dumps(doctor_report(verbose=False), ensure_ascii=False, indent=2))
        return 0
    report = doctor_report(verbose=True)
    return 0 if report["ok"] else 1


def _cmd_doctor_fix(args: argparse.Namespace, apply_repairs: bool) -> int:
    """Print (and optionally execute) a repair plan derived from doctor."""
    report = doctor_report(verbose=False)
    central = Path(report["central"]["dir"])
    # Local import keeps the sync-package test seams untouched.
    from ..services.inventory import list_skills as list_skills_at
    central_names = (
        {d.name for d in list_skills_at(central)} if central.exists() else set()
    )
    plan = build_fix_plan(report, central_names)

    if args.json_mode:
        applied: list[str] = []
        if apply_repairs:
            try:
                applied = _apply_fix_plan(plan, quiet=True)
            except OSError as e:
                print(json.dumps({"plan": plan, "error": str(e)},
                                 ensure_ascii=False, indent=2))
                return 1
        print(json.dumps({"plan": plan, "applied": applied},
                         ensure_ascii=False, indent=2))
        return 0

    print(render_plan(plan, applying=apply_repairs))
    if not apply_repairs:
        if not plan["noop"]:
            print("\n  dry-run only - re-run with `askill doctor --fix --apply` to execute.")
        return 0

    try:
        executed = _apply_fix_plan(plan, quiet=args.quiet)
    except OSError as e:
        print(f"Error during repair: {e}", file=sys.stderr)
        return 1
    print("\n  executed: " + (", ".join(executed) if executed else "nothing to execute"))
    return 0


def _apply_fix_plan(plan: dict, *, quiet: bool) -> list[str]:
    """Execute only ``auto`` actions, reusing the existing sync primitives."""
    ids = {a["id"] for a in plan["actions"]}
    executed: list[str] = []
    if "relink" in ids:
        sync_skill(verbose=not quiet)
        executed.append("askill sync")
    if "gc" in ids:
        gc_dead_links(verbose=not quiet)
        executed.append("askill sync --gc")
    return executed


def _cmd_rollback(args: argparse.Namespace) -> int:
    from ..services.sources import list_rollbackable, rollback_skill

    if args.list:
        items = list_rollbackable()
        if not items:
            print("No rollback snapshots (taken automatically before each 'askill update').")
            return 0
        print("Rollback snapshot(s) - one per skill, from its last update:")
        for n, when in items:
            print(f"  {n}  (snapshot taken {when})")
        return 0
    if not args.skill_name:
        print("Usage: askill rollback <skill> | askill rollback --list")
        return 2
    return 0 if rollback_skill(args.skill_name, verbose=not args.quiet) else 1


def _cmd_install_manifest(path: str, quiet: bool) -> int:
    report = install_manifest(Path(path), verbose=not quiet)
    if not report["ok"]:
        print(f"Error: {report['error']}")
        return 1
    if not quiet:
        print(
            f"\nAligned: {len(report['installed'])} installed, "
            f"{len(report['present'])} present, "
            f"{len(report['failed'])} failed, "
            f"{len(report['manual'])} need manual handling"
        )
        for name, why in report["manual"]:
            print(f"  - {name}: {why}")
    return 1 if (report["failed"] or report["manual"]) else 0


def _dispatch_audit(args: argparse.Namespace) -> int:
    """Route the three audit modes and validate CI flags."""
    residency = getattr(args, "residency", False)
    overlap = getattr(args, "overlap", False)
    if residency and overlap:
        print("Error: --residency and --overlap are mutually exclusive",
              file=sys.stderr)
        return 2
    fail_on: set[str] = set()
    if getattr(args, "fail_on", None):
        try:
            fail_on = parse_fail_on(args.fail_on)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2
    gh_format = getattr(args, "format", "table") == "github"
    if overlap:
        return _print_overlap(quiet=args.quiet, json_mode=args.json_mode)
    if residency:
        return _print_residency(quiet=args.quiet, json_mode=args.json_mode)
    return _print_audit(
        args.skill_name, quiet=args.quiet, json_mode=args.json_mode,
        fail_on=fail_on, gh_format=gh_format,
    )


def _print_residency(*, quiet: bool = False, json_mode: bool = False) -> int:
    rows = residency_report(CENTRAL_DIR)
    if json_mode:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    if not rows:
        if not quiet:
            print("No skills found in central repository.")
        return 0
    if not quiet:
        print(f"\n{'skill':<28} {'desc':>6} {'~tok':>6} {'lines':>6} {'kb':>7}  suggestion")
        print("-" * 66)
        for r in rows:
            print(
                f"{r['skill'][:27]:<28} {r['desc_chars']:>6} "
                f"{r['desc_tokens_est']:>6} {r['body_lines']:>6} "
                f"{r['dir_kb']:>7}  {r['suggestion']}"
            )
        print()
        print("  --  " + FOOTER)
    return 0


def _dispatch_watch(args: argparse.Namespace) -> None:
    # lazy import: pulling the watcher drags in the platform-specific
    # ReadDirectoryChangesW/inotify/kqueue layer; `status` stays fast.
    from ..services.watch import watch_loop

    watch_loop(interval=args.interval, json_events=args.json_mode)


_HANDLERS: dict[str, Callable[[argparse.Namespace], int | None]] = {
    "status": lambda a: _print_status(a.skill_name, quiet=a.quiet, json_mode=a.json_mode),
    "sync": lambda a: _print_sync(a.skill_name, force=a.force, quiet=a.quiet, only=a.only, gc=a.gc),
    "list": lambda a: _print_list(quiet=a.quiet, json_mode=a.json_mode),
    "install": _dispatch_install,
    "bundle": _cmd_bundle,
    "get": _cmd_get,
    "doctor": _cmd_doctor,
    "rollback": _cmd_rollback,
    "remove": lambda a: _print_remove(a.skill_name, quiet=a.quiet),
    "pack": lambda a: _print_pack(skill_name=a.skill_name, quiet=a.quiet),
    "adopt": lambda a: _print_adopt(a.platform_short.lower(), a.skill_name, quiet=a.quiet),
    "audit": _dispatch_audit,
    "search": lambda a: _cmd_search(a.query, a.install_idx, quiet=a.quiet, json_mode=a.json_mode),
    "new": lambda a: _cmd_new(
        a.name, a.target, a.description, a.description_zh, a.version,
        a.minimal, quiet=a.quiet, json_mode=a.json_mode,
    ),
    "publish": lambda a: _cmd_publish(
        a.skill_name, a.repo, root=a.root, force=a.force, https=a.https,
        create=a.create, push=a.push, targets=a.target, quiet=a.quiet,
    ),
    "verify": lambda a: _cmd_verify(
        a.skill_name, quiet=a.quiet, json_mode=a.json_mode, fmt=a.format,
    ),
    "watch": _dispatch_watch,
    "update": lambda a: _cmd_update(a.skill_name, a.check, quiet=a.quiet, json_mode=a.json_mode),
    "products": lambda a: (
        _print_product_paths()
        if getattr(a, "paths", False)
        else _print_products(quiet=a.quiet, json_mode=a.json_mode)
    ),
    "drift": lambda a: _cmd_drift(a.product_short, quiet=a.quiet, json_mode=a.json_mode),
    "version": lambda a: _print_version(),
}


if __name__ == "__main__":
    main()
