"""CLI entry point for agent-skill-manager."""

import argparse
import json
import platform
import shutil
import sys

from ..config.products import (
    CENTRAL_DIR,
    PRODUCTS,
    get_all_product_dirs,
    get_product_path,
)
from ..services.audit import analyze_skill_dir
from ..services.publish import publish_skill
from ..services.scaffold import create_skill
from ..services.sync import (
    FOOTER,
    adopt_from_platform,
    audit_all,
    audit_skill,
    get_status,
    install_skill,
    list_skills,
    pack_skill,
    print_onboarding,
    remove_skill,
    sync_skill,
)
from ..utils.filesystem import read_skill_metadata


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


def _print_status(skill_name=None, *, quiet=False, json_mode=False):
    """Print installation status of skills across all products.

    Column widths adapt to fit the terminal:
    - skill name column: longest name in current results (cap 30, floor 10)
    - product cell:      12 chars; shrinks to 6 (truncated with ellipsis) when
                         the full table would overflow the terminal
    - score column:      dropped first when the table gets too wide; the audit
                         verdict is the least actionable info once packed in

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
    abbrev_note = ""
    if total > term_w:
        show_score = False
        total -= score_w + 1
    if total > term_w:
        cell_w = 6   # 5-char short + "…" prefix
        abbrev_note = "  (product names abbreviated to 6 chars)"

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
    if not json_mode and not quiet:
        print(f"\n{header}{abbrev_note}")
        print("-" * (len(header) + len(abbrev_note)))

    for sn in order:
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


def _print_sync(skill_name=None, *, force=False, quiet=False):
    """Sync skills and print results.

    ``quiet`` flips ``sync_skill(verbose=...)`` to False. Conflict +
    SECURITY WARNING prints stay untouched because they go through
    ``sync_skill`` directly.

    Returns 1 when a named skill was not found (exit-code contract),
    else 0 - per-product conflicts/failures are reported data, not a
    command failure.
    """
    results = sync_skill(skill_name, verbose=not quiet, force=force)
    return 1 if (skill_name and not results) else 0


def _print_install(source, sync=False, audit=False, no_audit=False, *, quiet=False):
    """Install a skill and print results. Returns 1 on failure."""
    ok = install_skill(source, sync=sync, audit=audit, no_audit=no_audit, verbose=not quiet)
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


def _print_audit(skill_name=None, *, quiet=False, json_mode=False):
    """Audit one or all skills and print reports."""
    if json_mode:
        # audit_all returns the SkillReport list; audit_skill returns None
        # if the skill doesn't exist. We avoid the verbose path entirely
        # so JSON output isn't prepended by formatted findings.
        reports = (
            [audit_skill(skill_name, verbose=False)]
            if skill_name
            else audit_all(verbose=False)
        )
        reports = [r for r in reports if r is not None]
        print(json.dumps(reports, ensure_ascii=False, indent=2))
        return
    if skill_name:
        audit_skill(skill_name, verbose=not quiet)
    else:
        audit_all(verbose=not quiet)



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
    askill products                  List all supported products
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
    if cmd is None:
        print(USAGE)
        return

    quiet = bool(getattr(args, "quiet", False))
    json_mode = bool(getattr(args, "json_mode", False))

    # One-time first-run welcome (never in quiet/json/script modes).
    if cmd != "version":
        from ..services import welcome
        welcome.maybe_print_welcome(quiet=quiet, json_mode=json_mode)

    rc = 0
    if cmd == "status":
        rc = _print_status(args.skill_name, quiet=quiet, json_mode=json_mode)
    elif cmd == "sync":
        rc = _print_sync(args.skill_name, force=args.force, quiet=quiet)
    elif cmd == "list":
        rc = _print_list(quiet=quiet, json_mode=json_mode)
    elif cmd == "install":
        if args.source is None:
            # nargs="?" lets a missing <source> parse fine; keep the
            # project's shorthand examples here instead of crashing in
            # resolve_source(None).
            print(_INSTALL_HELP)
            sys.exit(2)
        rc = _print_install(
            args.source, sync=args.sync, audit=args.audit,
            no_audit=args.no_audit, quiet=quiet,
        )
    elif cmd == "remove":
        rc = _print_remove(args.skill_name, quiet=quiet)
    elif cmd == "pack":
        rc = _print_pack(skill_name=args.skill_name, quiet=quiet)
    elif cmd == "adopt":
        rc = _print_adopt(args.platform_short.lower(), args.skill_name, quiet=quiet)
    elif cmd == "audit":
        rc = _print_audit(args.skill_name, quiet=quiet, json_mode=json_mode)
    elif cmd == "search":
        rc = _cmd_search(args.query, args.install_idx,
                         quiet=quiet, json_mode=json_mode)
    elif cmd == "new":
        rc = _cmd_new(
            args.name, args.target, args.description,
            args.description_zh, args.version, args.minimal,
            quiet=quiet, json_mode=json_mode,
        )
    elif cmd == "publish":
        rc = _cmd_publish(
            args.skill_name, args.repo,
            root=args.root, force=args.force, https=args.https,
            create=args.create, push=args.push, quiet=quiet,
        )
    elif cmd == "verify":
        rc = _cmd_verify(args.skill_name, quiet=quiet, json_mode=json_mode)
    elif cmd == "watch":
        from ..services.watch import watch_loop
        watch_loop(interval=args.interval, json_events=json_mode)
    elif cmd == "update":
        rc = _cmd_update(args.skill_name, args.check,
                         quiet=quiet, json_mode=json_mode)
    elif cmd == "products":
        rc = _print_products(quiet=quiet, json_mode=json_mode)
    elif cmd == "drift":
        rc = _cmd_drift(args.product_short, quiet=quiet, json_mode=json_mode)
    elif cmd == "version":
        from .. import __version__
        print(f"agent-skill-manager v{__version__}")
    else:
        print(f"Unknown command: {cmd}")
        print(USAGE)
        rc = 2

    # Exit-code contract: 0 success, 1 operational failure, 2 usage error.
    if rc:
        sys.exit(rc)


def _build_parser() -> argparse.ArgumentParser:
    """Build the argparse subcommand parser.

    Extracted so tests can introspect it. Keeps every flag / positional
    compatible with the hand-rolled parser that lived here before; the
    only visible user-output change is the format of ``--help``.
    """
    parser = argparse.ArgumentParser(
        prog="askill",
        description=(
            "Agent Skill Manager - Cross-platform skill management for "
            f"{len(PRODUCTS)} domestic AI agent products."
        ),
        exit_on_error=False,   # raise ArgumentError instead of sys.exit (Py3.9+)
    )
    # ``-q/--quiet`` is universal; ``--json`` only exists on subcommands
    # that actually emit JSON (status/list/products/audit/search/verify/
    # update). Attaching it everywhere made ``askill sync --json`` silently
    # return human-readable text - a lying contract for scripts. Commands
    # without JSON support now fail the parse (SystemExit 2) instead.
    _quiet = argparse.ArgumentParser(add_help=False)
    _quiet.add_argument(
        "-q", "--quiet", action="store_true",
        help="Suppress non-essential output (progress, headers, tips). "
             "Errors, SECURITY WARNINGs and conflict messages still print.",
    )
    _common = argparse.ArgumentParser(add_help=False, parents=[_quiet])
    _common.add_argument(
        "--json", action="store_true", dest="json_mode",
        help="Emit machine-readable JSON to stdout instead of formatted tables.",
    )

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    p_status = sub.add_parser(
        "status", help="Show installation status across products",
        parents=[_common],
    )
    p_status.add_argument("skill_name", nargs="?", default=None)

    p_sync = sub.add_parser(
        "sync", help="Sync skill(s) to all products",
        parents=[_quiet],
    )
    p_sync.add_argument("skill_name", nargs="?", default=None)
    p_sync.add_argument(
        "--force", action="store_true",
        help="Overwrite differing real dirs (conflicts)",
    )

    sub.add_parser("list", help="List skills in central repository",
                   parents=[_common])

    p_install = sub.add_parser(
        "install",
        help="Install a skill (path / GitHub URL / skills.sh shorthand)",
        parents=[_quiet],
    )
    p_install.add_argument("--sync", action="store_true",
                          help="Also sync to all products after install")
    p_install.add_argument("--audit", action="store_true",
                          help="Print the full audit report after install")
    p_install.add_argument("--no-audit", action="store_true",
                          help="Skip the default spec + security checks")
    p_install.add_argument(
        "source", nargs="?", default=None,
        help="Local path, GitHub URL, or skills.sh shorthand",
    )

    p_remove = sub.add_parser(
        "remove", help="Remove a skill from all products",
        parents=[_quiet],
    )
    p_remove.add_argument("skill_name")

    p_pack = sub.add_parser(
        "pack", help="Package a skill as .zip for DuMate",
        parents=[_quiet],
    )
    p_pack.add_argument("skill_name")

    p_adopt = sub.add_parser(
        "adopt",
        help="Adopt skills from one platform (or 'all') into the central repo",
        parents=[_quiet],
    )
    p_adopt.add_argument(
        "platform_short",
        help="Short name of source product, or 'all'",
    )
    p_adopt.add_argument("skill_name", nargs="?", default=None)

    p_audit = sub.add_parser(
        "audit", help="Security audit of skill(s) in central repo",
        parents=[_common],
    )
    p_audit.add_argument("skill_name", nargs="?", default=None)

    p_search = sub.add_parser(
        "search", help="Search skills.sh; N installs that result",
        parents=[_common],
    )
    p_search.add_argument(
        "--install", type=int, default=None, dest="install_idx",
        help="Install the Nth result",
    )
    p_search.add_argument("query", nargs="*", help="Search query")

    p_new = sub.add_parser(
        "new", help="Scaffold a new skill in the central repository",
        parents=[_common],
    )
    p_new.add_argument(
        "name",
        help="Skill name (lowercase letters/digits, single hyphens)",
    )
    p_new.add_argument(
        "--target", action="append", default=None, dest="target",
        help="Product short whose frontmatter requirements to prefill; "
             "repeatable. Default: all declaring products (superset)",
    )
    p_new.add_argument(
        "--description", default=None,
        help="Frontmatter description (TODO placeholder if omitted)",
    )
    p_new.add_argument(
        "--description-zh", default=None, dest="description_zh",
        help="Chinese description (written when a target requires it)",
    )
    p_new.add_argument(
        "--version", default="0.1.0",
        help="Value for a required version field (default 0.1.0)",
    )
    p_new.add_argument(
        "--minimal", action="store_true",
        help="Only SKILL.md - no references/ or scripts/ subdirs",
    )

    p_publish = sub.add_parser(
        "publish",
        help="Publish a skill from the central repo to a git repository",
        parents=[_quiet],
    )
    p_publish.add_argument("skill_name", help="Skill in the central repo")
    p_publish.add_argument(
        "--repo", required=True,
        help="Target as owner/name (GitHub), or an explicit git URL",
    )
    p_publish.add_argument(
        "--push", action="store_true",
        help="Actually push. Without it the run is a dry run: gates are "
             "checked and the git plan printed, nothing is written",
    )
    p_publish.add_argument(
        "--root", action="store_true",
        help="Replace the repo ROOT with the skill (single-skill repo, "
             "install as owner/repo). Default: additive <skill>/ subdir "
             "(install as owner/repo@skill)",
    )
    p_publish.add_argument(
        "--force", action="store_true",
        help="Allow --root to replace existing repo content",
    )
    p_publish.add_argument(
        "--https", action="store_true",
        help="Clone/push over HTTPS (credential helper) instead of SSH",
    )
    p_publish.add_argument(
        "--create", action="store_true",
        help="Create the GitHub repo first via the gh CLI",
    )

    p_verify = sub.add_parser(
        "verify",
        help=(
            "Check skills against the agentskills.io spec plus "
            "per-product frontmatter requirements"
        ),
        parents=[_common],
    )
    p_verify.add_argument("skill_name", nargs="?", default=None)

    p_watch = sub.add_parser(
        "watch", help="Watch central repo; auto-sync changes",
        parents=[_common],
    )
    p_watch.add_argument(
        "--interval", type=int, default=3,
        help=(
            "Poll/fallback seconds (native inotify / kqueue / "
            "ReadDirectoryChangesW events wake syncs instantly when available)"
        ),
    )

    p_update = sub.add_parser(
        "update", help="Check/apply updates for tracked skills",
        parents=[_common],
    )
    p_update.add_argument(
        "--check", action="store_true",
        help="Only check for updates, don't apply",
    )
    p_update.add_argument("skill_name", nargs="?", default=None)

    sub.add_parser("products", help="List all supported products",
                   parents=[_common])
    p_drift = sub.add_parser(
        "drift",
        help="Report product-dir skills that diverge from the central repo",
        parents=[_common],
    )
    p_drift.add_argument(
        "product_short", nargs="?", default=None,
        help="Limit the scan to one product short (default: all)",
    )
    sub.add_parser("version", help="Show version", parents=[_quiet])

    return parser


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
                 create=False, push=False, quiet=False):
    """``askill publish <skill> --repo owner/name`` body (v0.15.0 R2)."""
    report = publish_skill(
        name, repo,
        root=root, force=force, https=https, create=create, push=push,
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


def _cmd_verify(skill_name, *, quiet=False, json_mode=False):
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
        reports = check_all_specs()
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
                print(result)
            return
        results = check_all_updates()
        if json_mode:
            print(json.dumps(results, ensure_ascii=False, indent=2))
            return
        if not quiet:
            for r in results:
                if r["status"] == "up-to-date":
                    print(f"  {r['skill']:<28} up-to-date ({r.get('branch', '')})")
                elif r["status"] == "update-available":
                    print(
                        f"  {r['skill']:<28} UPDATE "
                        f"{r.get('local_commit')} -> {r.get('remote_commit')} "
                        f"({r.get('branch', '')})"
                    )
                elif r["status"] == "error":
                    print(f"  {r['skill']:<28} remote unreachable")
                else:
                    print(f"  {r['skill']:<28} {r['status']}")
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


if __name__ == "__main__":
    main()
