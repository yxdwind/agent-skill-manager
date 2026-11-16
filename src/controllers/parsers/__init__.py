"""argparse command tree for ``askill`` (split out of the CLI in P2-12).

Every subcommand lives in one of three command-family modules; this package
assembles them **in the original registration order** so ``--help`` output and
every flag/positional stay byte-compatible with the monolithic parser. The
CLI keeps ``_build_parser()`` as its single entry point for introspection.
"""

from __future__ import annotations

import argparse

from . import authoring, distribution, operations

__all__ = ["build_parser"]


def build_parser(product_count: int) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="askill",
        description=(
            "Agent Skill Manager - Cross-platform skill management for "
            f"{product_count} domestic AI agent products."
        ),
        exit_on_error=False,   # raise ArgumentError instead of sys.exit (Py3.9+)
    )
    # Global ``--version`` (v0.18.0): coexist with the ``version``
    # subcommand so users get the version whether they type ``askill
    # --version`` or ``askill version``. It uses a distinct dest
    # (``show_version``) so it never collides with ``new --version`` (the
    # frontmatter "version" field, which shares the ``--version`` flag name
    # on a different parser and a different dest).
    parser.add_argument(
        "--version", action="store_true", dest="show_version",
        help="Show the askill version and exit",
    )
    # ``-q/--quiet`` is universal; ``--json`` only exists on subcommands
    # that actually emit JSON (status/list/products/audit/search/verify/
    # update). Attaching it everywhere made ``askill sync --json`` silently
    # return human-readable text - a lying contract for scripts. Commands
    # without JSON support now fail the parse (SystemExit 2) instead.
    quiet = argparse.ArgumentParser(add_help=False)
    quiet.add_argument(
        "-q", "--quiet", action="store_true",
        help="Suppress non-essential output (progress, headers, tips). "
             "Errors, SECURITY WARNINGs and conflict messages still print.",
    )
    common = argparse.ArgumentParser(add_help=False, parents=[quiet])
    common.add_argument(
        "--json", action="store_true", dest="json_mode",
        help="Emit machine-readable JSON to stdout instead of formatted tables.",
    )

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    distribution.add_status(sub, quiet=quiet, common=common)
    distribution.add_sync(sub, quiet=quiet, common=common)
    distribution.add_list(sub, quiet=quiet, common=common)
    distribution.add_install(sub, quiet=quiet, common=common)
    distribution.add_bundle(sub, quiet=quiet, common=common)
    distribution.add_get(sub, quiet=quiet, common=common)
    operations.add_doctor(sub, quiet=quiet, common=common)
    operations.add_rollback(sub, quiet=quiet, common=common)
    distribution.add_remove(sub, quiet=quiet, common=common)
    distribution.add_pack(sub, quiet=quiet, common=common)
    distribution.add_adopt(sub, quiet=quiet, common=common)
    operations.add_audit(sub, quiet=quiet, common=common)
    authoring.add_search(sub, quiet=quiet, common=common)
    authoring.add_new(sub, quiet=quiet, common=common)
    authoring.add_publish(sub, quiet=quiet, common=common)
    authoring.add_verify(sub, quiet=quiet, common=common)
    operations.add_watch(sub, quiet=quiet, common=common)
    operations.add_update(sub, quiet=quiet, common=common)
    distribution.add_products(sub, quiet=quiet, common=common)
    distribution.add_drift(sub, quiet=quiet, common=common)
    operations.add_version(sub, quiet=quiet, common=common)
    return parser
