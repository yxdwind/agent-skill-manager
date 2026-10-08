"""First-run welcome banner (P3 growth loop).

Printed once per machine, on the first successful non-quiet/non-json
invocation of any askill command. One line, no nagging: version, the
project URL, and the single most useful next command.

The marker lives in the central repo dir (``~/.agents/skills/``) next to
the other askill bookkeeping files, so removing the central repo resets
the welcome naturally.
"""
from __future__ import annotations

from pathlib import Path

from ..config.products import CENTRAL_DIR

WELCOME_FILE = ".askill-welcome"


def maybe_print_welcome(quiet: bool = False, json_mode: bool = False,
                        central: Path | None = None) -> bool:
    """Print the one-time welcome line. Returns True if it was printed.

    Silent in quiet/json modes and for scripted calls that redirect
    stdout is *not* detected (by design: one extra line on a real first
    run is acceptable; complexity is not).

    Failure-tolerant by contract: any filesystem error (read-only home,
    exotic permissions) suppresses the banner forever rather than
    breaking a real command - welcome text must never outrank the work.
    """
    if quiet or json_mode:
        return False
    try:
        base = Path(central) if central is not None else CENTRAL_DIR
        marker = base / WELCOME_FILE
        if marker.exists():
            return False
        from .. import __version__
        print(
            f"agent-skill-manager v{__version__} - one repo, synced to "
            "15 domestic AI agent products. "
            "Start with: askill status   (github.com/yxdwind/agent-skill-manager)"
        )
        base.mkdir(parents=True, exist_ok=True)
        marker.write_text("", encoding="utf-8")
        return True
    except OSError:
        return False
