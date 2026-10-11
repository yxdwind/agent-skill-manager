# Bash completion for ``askill``.
#
# Install:
#   source /path/to/completion/askill.bash
#   (or drop into ~/.bash_completion.d/askill)
#
# Smart-ish completion: the subcommand list is hard-coded (argparse's
# subparsers don't introspect cleanly at runtime), but every per-subcommand
# flag is real - so ``askill sync --<TAB>`` only suggests ``--force``,
# ``askill install --<TAB>`` only suggests ``--sync --audit --no-audit``,
# and so on. Skill / product names are pulled from the live CLI.

_askill_global_flags="--quiet -q --json"
_askill_subcommands="status sync list install new publish remove pack adopt audit search verify watch update products version help"

# Pull the live list of installed skill names and product short names from the
# CLI itself - this is the zero-dep equivalent of argcomplete's lazy
# introspection. Cached for the lifetime of one shell session.
_askill_skill_names=""
_askill_product_shorts=""

_askill_refresh_dynamic() {
    _askill_skill_names="$("$(command -v askill || echo true)" list --quiet 2>/dev/null \
        | awk '/^  / {print $1}' | tr '\n' ' ')"
    _askill_product_shorts="$("$(command -v askill || echo true)" products --json 2>/dev/null \
        | python -c 'import json,sys; [print(p["short"]) for p in json.load(sys.stdin)]' 2>/dev/null \
        | tr '\n' ' ')"
}

_askill_complete() {
    local cur prev words cword
    if declare -F _init_completion >/dev/null 2>&1; then
        _init_completion || return
    else
        # Bash <4.2 fallback
        COMPREPLY=()
        cur="${COMP_WORDS[COMP_CWORD]}"
        prev="${COMP_WORDS[COMP_CWORD-1]}"
        words=("${COMP_WORDS[@]}")
        cword=$COMP_CWORD
    fi

    local cmd=""
    if [[ $cword -ge 2 ]]; then
        cmd="${words[1]}"
    fi

    # Global flag completion at any depth.
    if [[ $cur == --* || $cur == -* ]]; then
        local flags="$_askill_global_flags"
        case "$cmd" in
            sync)         flags="$flags --force" ;;
            install)      flags="$flags --sync --audit --no-audit" ;;
            watch)        flags="$flags --interval" ;;
            update)       flags="$flags --check" ;;
            search)       flags="$flags --install" ;;
        esac
        COMPREPLY=( $(compgen -W "$flags" -- "$cur") )
        return 0
    fi

    if [[ $cword -eq 1 ]]; then
        COMPREPLY=( $(compgen -W "$_askill_subcommands" -- "$cur") )
        return 0
    fi

    # Positional completion per command.
    case "$cmd" in
        status|remove|pack|verify|update)
            if [[ $cword -eq 2 ]]; then
                [[ -z $_askill_skill_names ]] && _askill_refresh_dynamic
                COMPREPLY=( $(compgen -W "$_askill_skill_names" -- "$cur") )
                return 0
            fi
            ;;
        adopt)
            if [[ $cword -eq 2 ]]; then
                [[ -z $_askill_product_shorts ]] && _askill_refresh_dynamic
                COMPREPLY=( $(compgen -W "all $_askill_product_shorts" -- "$cur") )
                return 0
            fi
            if [[ $cword -eq 3 ]]; then
                [[ -z $_askill_skill_names ]] && _askill_refresh_dynamic
                COMPREPLY=( $(compgen -W "$_askill_skill_names" -- "$cur") )
                return 0
            fi
            ;;
        install)
            if [[ $cword -ge 2 && "$prev" != "--install" ]]; then
                # Local paths + shorthand - can't reasonably enumerate.
                COMPREPLY=()
                return 0
            fi
            ;;
        search)
            # Query words; no completion list.
            COMPREPLY=()
            return 0
            ;;
    esac

    COMPREPLY=()
}

complete -F _askill_complete askill