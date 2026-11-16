"""Command definitions for the distribution family (P2-12)."""

from __future__ import annotations


def add_status(sub, *, quiet, common) -> None:
    """Register ``status`` (flags unchanged from the monolithic parser)."""
    p_status = sub.add_parser(
        "status", help="Show installation status across products",
        parents=[common],
    )
    p_status.add_argument("skill_name", nargs="?", default=None)


def add_sync(sub, *, quiet, common) -> None:
    """Register ``sync`` (flags unchanged from the monolithic parser)."""
    p_sync = sub.add_parser(
        "sync", help="Sync skill(s) to all products",
        parents=[quiet],
    )
    p_sync.add_argument("skill_name", nargs="?", default=None)
    p_sync.add_argument(
        "--force", action="store_true",
        help="Overwrite differing real dirs (conflicts)",
    )
    p_sync.add_argument(
        "--only", nargs="+", default=None, metavar="SHORT",
        help="Sync only these products (short names from `askill products`, e.g. autoclaw2 kimi)",
    )
    p_sync.add_argument(
        "--gc", action="store_true",
        help="Remove product-side links whose target is gone (stale links); "
            "no syncing happens in this mode",
    )


def add_list(sub, *, quiet, common) -> None:
    """Register ``list`` (flags unchanged from the monolithic parser)."""
    sub.add_parser("list", help="List skills in central repository",
                   parents=[common])


def add_install(sub, *, quiet, common) -> None:
    """Register ``install`` (flags unchanged from the monolithic parser)."""
    p_install = sub.add_parser(
        "install",
        help="Install a skill (path / GitHub URL / skills.sh shorthand)",
        parents=[quiet],
    )
    p_install.add_argument("--sync", action="store_true",
                          help="Also sync to all products after install")
    p_install.add_argument(
        "--only", nargs="+", default=None, metavar="SHORT",
        help="With --sync: distribute only to these products (short names)",
    )
    p_install.add_argument("--audit", action="store_true",
                          help="Print the full audit report after install")
    p_install.add_argument("--no-audit", action="store_true",
                          help="Skip the default spec + security checks")
    p_install.add_argument(
        "source", nargs="?", default=None,
        help="Local path, .zip/.skill archive, GitHub URL, or skills.sh shorthand",
    )
    p_install.add_argument(
        "--manifest", default=None,
        help="Align the central repo to a manifest instead of installing <source>",
    )


def add_bundle(sub, *, quiet, common) -> None:
    """Register ``bundle`` (flags unchanged from the monolithic parser)."""
    p_bundle = sub.add_parser(
        "bundle", help="Export askill-manifest.json for team / multi-machine sync",
        parents=[quiet],
    )
    p_bundle.add_argument(
        "--output", default=None,
        help="Manifest path (default: alongside the central repo)",
    )
    p_bundle.add_argument(
        "--external-only", action="store_true",
        help="Export only git-sourced skills (skip locally authored ones)",
    )


def add_get(sub, *, quiet, common) -> None:
    """Register ``get`` (flags unchanged from the monolithic parser)."""
    p_get = sub.add_parser(
        "get", help="Preview a skill without installing (stdout / temp dir)",
        parents=[quiet],
    )
    p_get.add_argument(
        "source",
        help="owner/repo@skill, owner/repo, GitHub URL, or local skill dir",
    )
    p_get.add_argument(
        "--dir", action="store_true",
        help="Copy the full skill folder to a temp path instead of printing SKILL.md",
    )
    p_get.add_argument(
        "--list", action="store_true",
        help="List skills available in the repo instead of printing",
    )


def add_remove(sub, *, quiet, common) -> None:
    """Register ``remove`` (flags unchanged from the monolithic parser)."""
    p_remove = sub.add_parser(
        "remove", help="Remove a skill from all products",
        parents=[quiet],
    )
    p_remove.add_argument("skill_name")


def add_pack(sub, *, quiet, common) -> None:
    """Register ``pack`` (flags unchanged from the monolithic parser)."""
    p_pack = sub.add_parser(
        "pack", help="Package a skill as .zip for DuMate",
        parents=[quiet],
    )
    p_pack.add_argument("skill_name")


def add_adopt(sub, *, quiet, common) -> None:
    """Register ``adopt`` (flags unchanged from the monolithic parser)."""
    p_adopt = sub.add_parser(
        "adopt",
        help="Adopt skills from one platform (or 'all') into the central repo",
        parents=[quiet],
    )
    p_adopt.add_argument(
        "platform_short",
        help="Short name of source product, or 'all'",
    )
    p_adopt.add_argument("skill_name", nargs="?", default=None)


def add_products(sub, *, quiet, common) -> None:
    """Register ``products`` (flags unchanged from the monolithic parser)."""
    p_products = sub.add_parser("products", help="List all supported products",
                                parents=[common])
    p_products.add_argument(
        "--paths", action="store_true",
        help="Export full cross-platform path declarations as JSON "
             "(implies --json; for upstream agents.md contributions)",
    )


def add_drift(sub, *, quiet, common) -> None:
    """Register ``drift`` (flags unchanged from the monolithic parser)."""
    p_drift = sub.add_parser(
        "drift",
        help="Report product-dir skills that diverge from the central repo",
        parents=[common],
    )
    p_drift.add_argument(
        "product_short", nargs="?", default=None,
        help="Limit the scan to one product short (default: all)",
    )

