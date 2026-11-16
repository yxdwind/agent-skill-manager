"""Command definitions for the operations family (P2-12)."""

from __future__ import annotations


def add_doctor(sub, *, quiet, common) -> None:
    """Register ``doctor`` (flags unchanged from the monolithic parser)."""
    p_doctor = sub.add_parser(
        "doctor", help="Environment & repository health diagnostics",
        parents=[common],
    )
    p_doctor.add_argument(
        "--fix", action="store_true",
        help="Print a repair plan (dry-run by default; nothing is changed)",
    )
    p_doctor.add_argument(
        "--apply", action="store_true",
        help="With --fix: execute the automatic repairs (sync / sync --gc)",
    )


def add_rollback(sub, *, quiet, common) -> None:
    """Register ``rollback`` (flags unchanged from the monolithic parser)."""
    p_rollback = sub.add_parser(
        "rollback", help="Restore the pre-update snapshot of a skill",
        parents=[common],
    )
    p_rollback.add_argument("skill_name", nargs="?", default=None)
    p_rollback.add_argument(
        "--list", action="store_true",
        help="List skills that have a rollback snapshot",
    )


def add_audit(sub, *, quiet, common) -> None:
    """Register ``audit`` (flags unchanged from the monolithic parser)."""
    p_audit = sub.add_parser(
        "audit", help="Security audit of skill(s) in central repo",
        parents=[common],
    )
    p_audit.add_argument("skill_name", nargs="?", default=None)
    p_audit.add_argument(
        "--residency", action="store_true",
        help="Attention-budget report (context cost of every description) "
            "instead of the security scan",
    )
    p_audit.add_argument(
        "--overlap", action="store_true",
        help="Deterministic description-overlap report (lexical Jaccard)",
    )
    p_audit.add_argument(
        "--format", choices=("table", "github"), default="table",
        help="Output format: human table or GitHub Actions annotations",
    )
    p_audit.add_argument(
        "--fail-on", default=None, metavar="GRADES",
        help="Comma-separated audit grades that fail the run (e.g. D,F)",
    )


def add_watch(sub, *, quiet, common) -> None:
    """Register ``watch`` (flags unchanged from the monolithic parser)."""
    p_watch = sub.add_parser(
        "watch", help="Watch central repo; auto-sync changes",
        parents=[common],
    )
    p_watch.add_argument(
        "--interval", type=int, default=3,
        help=(
            "Poll/fallback seconds (native inotify / kqueue / "
            "ReadDirectoryChangesW events wake syncs instantly when available)"
        ),
    )


def add_update(sub, *, quiet, common) -> None:
    """Register ``update`` (flags unchanged from the monolithic parser)."""
    p_update = sub.add_parser(
        "update", help="Check/apply updates for tracked skills",
        parents=[common],
    )
    p_update.add_argument(
        "--check", action="store_true",
        help="Only check for updates, don't apply",
    )
    p_update.add_argument("skill_name", nargs="?", default=None)


def add_version(sub, *, quiet, common) -> None:
    """Register ``version`` (flags unchanged from the monolithic parser)."""
    sub.add_parser("version", help="Show version", parents=[quiet])

