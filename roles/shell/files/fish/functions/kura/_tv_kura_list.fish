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
        (if .state == "missing" then "not downloaded" else .state end),
        (if .global or .installed == "global" then "global"
         elif (.reason // "" | startswith("dep-of:")) then "via " + (.reason | ltrimstr("dep-of:"))
         elif .installed == "project" then "project"
         else "" end)
    ]'

    if test "$filter" = categories
        set prog '[.[] | . as $skill | .groups[] | {group: ., state: $skill.state}]
            | group_by(.group) | .[] | [
                ("@" + .[0].group),
                ("skills: \(length)"),
                ("\([.[] | select(.state == "linked")] | length)/\(length) linked"),
                ""
            ]'
    end

    set -l layout '['$prog']
        | (map(.[0] | length) | max) as $name_width
        | (map("[" + .[2] + "]" | length) | max) as $state_width
        | (map(.[3] | length) | max) as $scope_width
        | .[] | . + [$name_width, $state_width, $scope_width] | @tsv'
    kura list --type $type --json | jq -r $layout | while read -l -d \t name groups state scope name_width state_width scope_width
        _tv_kura_fmt $name "$groups" $state "$scope" $name_width $state_width $scope_width
    end | sort
end

function _tv_kura_fmt --description "Format one television row: name, link status, scope, groups" --argument-names name groups state scope name_width state_width scope_width
    set -l status_cell (printf '%-*s' $state_width "[$state]")
    set -l scope_cell (printf '%-*s' $scope_width "$scope")
    if _ui color-enabled
        set -l colour cyan
        switch $state
            case linked
                set colour green
            case 'not downloaded'
                set colour yellow
        end
        set status_cell (_ui paint $colour "$status_cell")
        if test "$scope" = global
            set scope_cell (_ui paint magenta "$scope_cell")
        end
        set groups (_ui paint dim "$groups")
    end
    if test "$scope_width" -eq 0
        printf '%-*s  %s  %s\n' $name_width $name "$status_cell" "$groups"
    else
        printf '%-*s  %s  %s  %s\n' $name_width $name "$status_cell" "$scope_cell" "$groups"
    end
end
