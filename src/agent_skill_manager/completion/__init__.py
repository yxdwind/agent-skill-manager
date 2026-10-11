"""Shell-completion scripts for askill (v0.18.0).

This subpackage bundles the bash / zsh / fish completion scripts so they
ship inside the PyPI wheel.  ``pip`` users can locate them at the installed
package path::

    import agent_skill_manager, os
    completion_dir = os.path.join(
        os.path.dirname(agent_skill_manager.__file__), "completion"
    )

Git-clone users find the same scripts at the repo-root ``completion/`` dir.
