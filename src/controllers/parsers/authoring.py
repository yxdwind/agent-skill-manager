"""Command definitions for the authoring family (P2-12)."""

from __future__ import annotations


def add_search(sub, *, quiet, common) -> None:
    """Register ``search`` (flags unchanged from the monolithic parser)."""
    p_search = sub.add_parser(
        "search", help="Search skills.sh; N installs that result",
        parents=[common],
    )
    p_search.add_argument(
        "--install", type=int, default=None, dest="install_idx",
        help="Install the Nth result",
    )
    p_search.add_argument("query", nargs="*", help="Search query")


def add_new(sub, *, quiet, common) -> None:
    """Register ``new`` (flags unchanged from the monolithic parser)."""
    p_new = sub.add_parser(
        "new", help="Scaffold a new skill in the central repository",
        parents=[common],
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


def add_publish(sub, *, quiet, common) -> None:
    """Register ``publish`` (flags unchanged from the monolithic parser)."""
    p_publish = sub.add_parser(
        "publish",
        help="Publish a skill from the central repo to a git repository",
        parents=[quiet],
    )
    p_publish.add_argument("skill_name", help="Skill in the central repo")
    p_publish.add_argument(
        "--repo", required=True,
        help="Target as owner/name (GitHub), or an explicit git URL",
    )
    p_publish.add_argument(
        "--target", action="append", default=None, dest="target",
        help="Limit the frontmatter gate to these product shorts (repeatable); "
             "default checks every declaring product",
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


def add_verify(sub, *, quiet, common) -> None:
    """Register ``verify`` (flags unchanged from the monolithic parser)."""
    p_verify = sub.add_parser(
        "verify",
        help=(
            "Check skills against the agentskills.io spec plus "
            "per-product frontmatter requirements"
        ),
        parents=[common],
    )
    p_verify.add_argument(
        "--format", choices=("table", "github"), default="table",
        help="Output format: human table or GitHub Actions annotations",
    )
    p_verify.add_argument("skill_name", nargs="?", default=None)

