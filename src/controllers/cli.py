"""CLI entry point for agent-skill-manager."""

import argparse
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


def _print_products():
    """Print all supported products and their paths."""
    print(f"\n{'='*60}")
    print(f"Supported Products ({len(PRODUCTS)})")
    print(f"{'='*60}")
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


def _print_list():
    """List all skills in the central repository."""
    skills = list_skills()
    if not skills:
        if not CENTRAL_DIR.exists():
            print(f"Central repository not found: {CENTRAL_DIR}")
        else:
            print(f"No skills found in {CENTRAL_DIR}")
        print_onboarding()
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


def _print_status(skill_name=None):
    """Print installation status of skills across all products.

    Column widths adapt to fit the terminal:
    - skill name column: longest name in current results (cap 30, floor 10)
    - product cell:      12 chars; shrinks to 6 (truncated with ellipsis) when
                         the full table would overflow the terminal
    - score column:      dropped first when the table gets too wide; the audit
                         verdict is the least actionable info once packed in
    """
    results = get_status(skill_name)
    if not results:
        if skill_name:
            print(f"Skill not found: {skill_name}")
        else:
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
        if show_score:
            skill_dir = CENTRAL_DIR / sn
            if skill_dir.exists():
                report = analyze_skill_dir(skill_dir)
                row += _cell(f"{report['score']}/{report['grade']} {verdict_icon[report['verdict']]}", score_w)
            else:
                row += _cell("n/a", score_w)
        print(row)
    print(f"  --  {FOOTER}")
    print()


def _print_sync(skill_name=None, force=False):
    """Sync skills and print results."""
    sync_skill(skill_name, verbose=True, force=force)


def _print_install(source, sync=False, audit=False, no_audit=False):
    """Install a skill and print results."""
    install_skill(source, sync=sync, audit=audit, no_audit=no_audit, verbose=True)


def _print_remove(skill_name):
    """Remove a skill and print results."""
    remove_skill(skill_name, verbose=True)


def _print_pack(skill_name):
    """Pack a skill and print results."""
    pack_skill(skill_name, verbose=True)


def _print_adopt(platform_short, skill_name=None):
    """Adopt skills from one platform to all others."""
    adopt_from_platform(platform_short, skill_name, verbose=True)


def _print_audit(skill_name=None):
    """Audit one or all skills and print reports."""
    if skill_name:
        audit_skill(skill_name, verbose=True)
    else:
        audit_all(verbose=True)



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
    askill products                  List all supported products
    askill version                   Show version
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
    except SystemExit:
        # argparse emitted --help / error and called sys.exit; it has
        # already written the message. Just stop cleanly.
        return
    except argparse.ArgumentError as e:
        # Per-subcommand validation failure. For ``install`` with no
        # <source> we keep the project's existing usage block instead of
        # argparse's default error so users get the skills.sh shorthand
        # examples they expect.
        if argv and argv[0] == "install":
            print(_INSTALL_HELP)
        else:
            print(f"Error: {e}")
        return

    cmd = args.command
    if cmd is None:
        print(USAGE)
        return

    if cmd == "status":
        _print_status(args.skill_name)
    elif cmd == "sync":
        _print_sync(args.skill_name, force=args.force)
    elif cmd == "list":
        _print_list()
    elif cmd == "install":
        _print_install(
            args.source, sync=args.sync, audit=args.audit, no_audit=args.no_audit,
        )
    elif cmd == "remove":
        _print_remove(args.skill_name)
    elif cmd == "pack":
        _print_pack(skill_name=args.skill_name)
    elif cmd == "adopt":
        _print_adopt(args.platform_short.lower(), args.skill_name)
    elif cmd == "audit":
        _print_audit(args.skill_name)
    elif cmd == "search":
        _cmd_search(args.query, args.install_idx)
    elif cmd == "verify":
        _cmd_verify(args.skill_name)
    elif cmd == "watch":
        from ..services.watch import watch_loop
        watch_loop(interval=args.interval)
    elif cmd == "update":
        _cmd_update(args.skill_name, args.check)
    elif cmd == "products":
        _print_products()
    elif cmd == "version":
        from .. import __version__
        print(f"agent-skill-manager v{__version__}")
    else:
        print(f"Unknown command: {cmd}")
        print(USAGE)


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
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    p_status = sub.add_parser(
        "status", help="Show installation status across products",
    )
    p_status.add_argument("skill_name", nargs="?", default=None)

    p_sync = sub.add_parser(
        "sync", help="Sync skill(s) to all products",
    )
    p_sync.add_argument("skill_name", nargs="?", default=None)
    p_sync.add_argument(
        "--force", action="store_true",
        help="Overwrite differing real dirs (conflicts)",
    )

    sub.add_parser("list", help="List skills in central repository")

    p_install = sub.add_parser(
        "install",
        help="Install a skill (path / GitHub URL / skills.sh shorthand)",
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
    )
    p_remove.add_argument("skill_name")

    p_pack = sub.add_parser(
        "pack", help="Package a skill as .zip for DuMate",
    )
    p_pack.add_argument("skill_name")

    p_adopt = sub.add_parser(
        "adopt",
        help="Adopt skills from one platform (or 'all') into the central repo",
    )
    p_adopt.add_argument(
        "platform_short",
        help="Short name of source product, or 'all'",
    )
    p_adopt.add_argument("skill_name", nargs="?", default=None)

    p_audit = sub.add_parser(
        "audit", help="Security audit of skill(s) in central repo",
    )
    p_audit.add_argument("skill_name", nargs="?", default=None)

    p_search = sub.add_parser(
        "search", help="Search skills.sh; N installs that result",
    )
    p_search.add_argument(
        "--install", type=int, default=None, dest="install_idx",
        help="Install the Nth result",
    )
    p_search.add_argument("query", nargs="*", help="Search query")

    p_verify = sub.add_parser(
        "verify",
        help=(
            "Check skills against the agentskills.io spec plus "
            "per-product frontmatter requirements"
        ),
    )
    p_verify.add_argument("skill_name", nargs="?", default=None)

    p_watch = sub.add_parser(
        "watch", help="Watch central repo; auto-sync changes",
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
    )
    p_update.add_argument(
        "--check", action="store_true",
        help="Only check for updates, don't apply",
    )
    p_update.add_argument("skill_name", nargs="?", default=None)

    sub.add_parser("products", help="List all supported products")
    sub.add_parser("version", help="Show version")

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


def _cmd_search(query_parts, install_idx):
    """``askill search`` body; extracted from main() so it stays readable."""
    from ..services.registry import RegistryError, search_skills
    if not query_parts:
        print("Usage: askill search <query> [--install N]")
        print("  e.g. askill search pdf --install 1")
        return
    query = " ".join(query_parts)
    try:
        results = search_skills(query)
    except RegistryError as e:
        print(f"skills.sh registry unavailable: {e}")
        return
    if not results:
        print(f"No skills found for {query!r} on skills.sh.")
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
        return
    if install_idx < 1 or install_idx > len(results):
        print(f"Invalid --install index: pick 1-{len(results)}")
        return
    pick = results[install_idx - 1]
    print(f"Installing result #{install_idx}: {pick['source']}@{pick['skill_id']}")
    install_skill(f"{pick['source']}@{pick['skill_id']}", verbose=True)
    print("\nRun 'askill sync' to distribute, or 'askill watch' to auto-sync.")


def _cmd_verify(skill_name):
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
            print(f"Skill not found in central repo: {skill_name}")
            return
        target_dir = skill_dir
        reports = [check_spec(skill_dir)]
    else:
        reports = check_all_specs()
    if not reports:
        print("No skills found in central repository.")
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

    if target_dir is not None:
        product_issues = [(target_dir.name, product_frontmatter_issues(target_dir))]
    else:
        product_issues = [
            (d.name, product_frontmatter_issues(d)) for d in list_skills()
        ]
    flagged = [(sn, iss) for sn, iss in product_issues if iss]
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


def _cmd_update(skill_name, check_only):
    """``askill update [skill-name] [--check]`` body."""
    from ..services.sources import (
        check_all_updates,
        check_update,
        update_skill,
    )
    if check_only:
        if skill_name:
            print(check_update(skill_name))
        else:
            for r in check_all_updates():
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
        print("No tracked skills (install via GitHub URL to enable tracking).")
        return
    pending = [r["skill"] for r in results if r["status"] == "update-available"]
    if not pending:
        print("All tracked skills are up to date.")
        return
    print(f"Updating {len(pending)} skill(s): {', '.join(pending)}")
    for name in pending:
        update_skill(name, verbose=True)


if __name__ == "__main__":
    main()
