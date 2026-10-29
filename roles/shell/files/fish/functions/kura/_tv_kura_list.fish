function _tv_kura_list --description "Television source: list catalog skills, agents, or bundles with groups and link status" --argument-names kind filter
    # A formatter, and nothing more. Every fact on a row - the catalogue, which entries
    # are hidden as dependency_only, whether an artifact belongs in ~/.claude or the
    # project, and whether it is linked there - comes from `kura list --json`.
    #
    # This used to derive all of it here in jq, against its own rule for what a project
    # is (the git top level, where kura takes the cwd). In a directory that is not
    # a repo that rule yielded no project at all, so every non-global row rendered
    # [available] however many links were on disk, and Enter then refused because
    # kura could see them.
    if not command -q kura
        _ui err "kura is not on PATH. Run: make run-role ROLE=ai"
        return 1
    end

    set -l type (string replace -r 's$' '' -- $kind)
    if not contains -- $type skill agent bundle
        _ui err "_tv_kura_list: kind must be 'skill', 'agent', or 'bundle'"
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
        case '' all categories
            set select '.'
        case '*'
            _ui err "_tv_kura_list: filter must be 'linked', 'available', 'noglobal', 'categories', or empty"
            return 1
    end

    set -l prog '.[] | '$select' | [
        .name,
        (.groups | join(", ")),
        (if .state == "missing" then "not downloaded" else .state end)
    ]'

    if test "$filter" = categories
        set prog '[.[] | . as $skill | .groups[] | {group: ., state: $skill.state}]
            | group_by(.group) | .[] | [
                ("@" + .[0].group),
                ("skills: \(length)"),
                ("\([.[] | select(.state == "linked")] | length)/\(length) linked")
            ]'
    end

    set -l layout '['$prog']
        | (map(.[0] | length) | max) as $name_width
        | (map("[" + .[2] + "]" | length) | max) as $state_width
        | .[] | . + [$name_width, $state_width] | @tsv'
    kura list --type $type --json | jq -r $layout | while read -l -d \t name groups state name_width state_width
        _tv_kura_fmt $name "$groups" $state $name_width $state_width
    end | sort
end

function _tv_kura_fmt --description "Format one television row: name, groups, link status"
    set -l state (printf '%-*s' $argv[5] "[$argv[3]]")
    set -l groups $argv[2]
    if _ui color-enabled
        set -l colour cyan
        switch $argv[3]
            case linked
                set colour green
            case 'not downloaded'
                set colour yellow
        end
        set state (_ui paint $colour "$state")
        set groups (_ui paint dim "$groups")
    end
    printf '%-*s  %s  %s\n' $argv[4] $argv[1] "$state" "$groups"
end
