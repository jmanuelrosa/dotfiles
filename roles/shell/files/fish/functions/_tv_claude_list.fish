function _tv_claude_list --description "Television source: list claude skills or agents with groups and link status" --argument-names kind filter
    # A formatter, and nothing more. Every fact on a row - the catalogue, which entries
    # are hidden as dependency_only, whether an artifact belongs in ~/.claude or the
    # project, and whether it is linked there - comes from `claude-kit list --json`.
    #
    # This used to derive all of it here in jq, against its own rule for what a project
    # is (the git top level, where claude-kit takes the cwd). In a directory that is not
    # a repo that rule yielded no project at all, so every non-global row rendered
    # [available] however many links were on disk, and Enter then refused because
    # claude-kit could see them.
    if not command -q claude-kit
        _ui err "claude-kit is not on PATH. Run: make run-role ROLE=ai"
        return 1
    end

    set -l types
    switch $kind
        case skill skills
            set types skill
        case agent agents
            # The agent picker carries the seat plugins too: a plugin is the other way to
            # ship an agent, and plugin.json holds its groups. Two calls rather than one,
            # because --type is per call and a name may legally mean one of each.
            set types agent plugin
        case '*'
            _ui err "_tv_claude_list: kind must be 'skill' or 'agent'"
            return 1
    end

    set -l select
    switch $filter
        case linked
            set select 'select(.state == "linked")'
        case available
            # Both remaining states: on disk and installable, or not fetched yet.
            set select 'select(.state != "linked")'
        case noglobal
            # Hides what is installed everywhere already, so browsing to install into one
            # project shows only what that project does not get for free.
            set select 'select(.global | not)'
        case '' all
            set select '.'
        case '*'
            _ui err "_tv_claude_list: filter must be 'linked', 'available', 'noglobal', or empty"
            return 1
    end

    set -l prog '.[] | '$select' | [
        .name,
        (.groups | join(", ")),
        (if .state == "missing" then "not downloaded" else .state end)
    ] | @tsv'

    begin
        for type in $types
            claude-kit list --type $type --json | jq -r $prog
        end
    end | while read -l -d \t name groups state
        _tv_claude_fmt $name "$groups" $state
    end | sort
end

function _tv_claude_fmt --description "Format one television row: name, groups, link status"
    # Fixed-width columns for a picker to lay out and filter, which is why this is a
    # printf and not the shared `_ui` vocabulary: the cable reads the status back with
    # `string match -e '[linked]'`, and these are columns rather than lines for a human.
    printf '%-28s  %-46s  [%s]\n' $argv[1] $argv[2] $argv[3]
end
