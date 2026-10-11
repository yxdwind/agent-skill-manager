# Fish completion for ``askill``.
#
# Install:
#   cp completion/askill.fish ~/.config/fish/completions/
#
# Smart-ish: subcommands + per-cmd flags are real; skill / product short
# names are pulled live from the CLI at completion time.

function __askill_skill_names
    command -v askill >/dev/null 2>&1 || return
    askill list --quiet 2>/dev/null | string match -rg '^  (\S+)'
end

function __askill_product_shorts
    command -v askill >/dev/null 2>&1 || return
    askill products --json 2>/dev/null | python -c 'import json,sys; [print(p["short"]) for p in json.load(sys.stdin)]' 2>/dev/null
end

function __askill_global_flags
    echo --quiet -q --json
end

# Top-level subcommand dispatch.
function __askill_needs_command
    set -l cmd (commandline -opc)
    [ (count $cmd) -eq 1 ]
end

function __askill_using_command
    set -l cmd (commandline -opc)
    [ (count $cmd) -ge 2 ]
end

# --- subcommands ---------------------------------------------------------

set -l subcmds \
    status 'Show installation status across products' \
    sync   'Sync skill(s) to all products' \
    list   'List skills in central repository' \
    install 'Install a skill (path / GitHub URL / skills.sh shorthand)' \
    remove 'Remove a skill from all products' \
    pack   'Package a skill as .zip for DuMate' \
    adopt  'Adopt skills from one platform (or all) into the central repo' \
    audit  'Security audit of skill(s) in central repo' \
    search 'Search skills.sh; N installs that result' \
    new    'Scaffold a new skill in the central repository' \n    publish 'Publish a skill from the central repo to a git repository' \n    verify 'Check skills against the agentskills.io spec' \
    watch  'Watch central repo; auto-sync changes' \
    update 'Check/apply updates for tracked skills' \
    products 'List all supported products' \
    version 'Show version'

complete -c askill -n '__askill_needs_command' -a "$subcmds" -f

# --- global flags ---------------------------------------------------------

complete -c askill -l quiet -s q -d 'Suppress non-essential output'
complete -c askill -l json -d 'Emit machine-readable JSON'

# --- per-command flags + positionals ------------------------------------

complete -c askill -n '__askill_using_command && test (commandline -opc)[2] = sync' \
    -l force -d 'Overwrite differing real dirs (conflicts)'

complete -c askill -n '__askill_using_command && test (commandline -opc)[2] = install' \
    -l sync -d 'Also sync to all products after install'
complete -c askill -n '__askill_using_command && test (commandline -opc)[2] = install' \
    -l audit -d 'Print the full audit report after install'
complete -c askill -n '__askill_using_command && test (commandline -opc)[2] = install' \
    -l no-audit -d 'Skip the default spec + security checks'

complete -c askill -n '__askill_using_command && test (commandline -opc)[2] = watch' \
    -l interval -d 'Poll/fallback seconds'

complete -c askill -n '__askill_using_command && test (commandline -opc)[2] = update' \
    -l check -d 'Only check for updates, don'\''t apply'

complete -c askill -n '__askill_using_command && test (commandline -opc)[2] = search' \
    -l install -d 'Install the Nth result'

# Skill-name positionals (single arg).
for cmd in status remove pack verify update
    complete -c askill -n "__askill_using_command && test (commandline -opc)[2] = $cmd" \
        -a "(__askill_skill_names)" -f
end

# adopt: first positional = platform, second = skill.
complete -c askill -n '__askill_using_command && test (commandline -opc)[2] = adopt && test (count (commandline -opc)) -eq 3' \
    -a "all (__askill_product_shorts)"
complete -c askill -n '__askill_using_command && test (commandline -opc)[2] = adopt && test (count (commandline -opc)) -ge 4' \
    -a "(__askill_skill_names)" -f

# install: paths (no enumeration, fish handles ``file`` style).
complete -c askill -n '__askill_using_command && test (commandline -opc)[2] = install' \
    -F