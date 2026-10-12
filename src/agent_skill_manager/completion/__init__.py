"""Shell-completion scripts for askill (bundled since v0.18.1).

This subpackage bundles the bash / zsh / fish completion scripts so they
ship inside the PyPI wheel. ``pip`` users can locate them at the installed
package path::

    import agent_skill_manager
    from agent_skill_manager.completion import COMPLETION_DIR

    # or, equivalently:
    import os
    completion_dir = os.path.join(
        os.path.dirname(agent_skill_manager.__file__), "completion"
    )

Git-clone users find the same scripts at the repo-root ``completion/`` dir.
"""

from __future__ import annotations

from pathlib import Path

COMPLETION_DIR = Path(__file__).parent

__all__ = ["COMPLETION_DIR"]
