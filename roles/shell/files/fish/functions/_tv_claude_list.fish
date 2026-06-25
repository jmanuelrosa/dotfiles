function _tv_claude_list --description "Television source: list claude skills or agents with groups and link status" --argument-names kind filter
    set -l source
    set -l target
    set -l registry
    set -l ext ""

    switch $kind
        case skill skills
            set source $DOTFILES_DIR/roles/ai/files/claude/skills
            set target .claude/skills
            set registry $DOTFILES_DIR/roles/ai/files/claude/skill-registry.json
        case agent agents
            set source $DOTFILES_DIR/roles/ai/files/claude/agents
            set target .claude/agents
            set registry $DOTFILES_DIR/roles/ai/files/claude/agent-registry.json
            set ext .md
        case '*'
            echo "_tv_claude_list: kind must be 'skill' or 'agent'" >&2
            return 1
    end

    # Derive a repos skill's directory name from upstream_path (basename, or repo name for
    # root skills); local skills keep their own name. Kept in sync with claude-skill.fish.
    set -l jqlib 'def dn($r): (.upstream_path // "") as $p | if ($p == "" or $p == "." or $p == "/") then ($r | split("/")[1]) else ($p | sub("/+$";"") | split("/") | last) end; def allskills: [ (.repos | to_entries[] | .key as $r | .value.skills[] | . + {name: dn($r), repo: $r}), (.local_skills[]? | . + {repo: null}) ];'

    set -l group_map
    if command -q jq; and test -f "$registry"
        switch $kind
            case skill skills
                set group_map (jq -r $jqlib' allskills | .[] | "\(.name)|\(.groups // [] | join(", "))"' $registry)
            case agent agents
                set group_map (jq -r '[.repos[].agents[]?, .local_agents[]?] | .[] | "\(.name)|\(.groups // [] | join(", "))"' $registry)
        end
    end

    set -l lines
    set -l seen

    if test -d "$source"
        if test -z "$ext"
            for entry in $source/*/
                set -l name (basename $entry)
                set -a seen $name
                set -l state available
                test -L "$target/$name$ext"; and set state linked
                set -a lines (_tv_claude_fmt $name $state $group_map)
            end
        else
            for entry in $source/*$ext
                test -f "$entry"; or continue
                set -l name (basename $entry $ext)
                set -a seen $name
                set -l state available
                test -L "$target/$name$ext"; and set state linked
                set -a lines (_tv_claude_fmt $name $state $group_map)
            end
        end
    end

    if command -q jq; and test -f "$registry"
        set -l reg_names
        switch $kind
            case skill skills
                set reg_names (jq -r $jqlib' allskills | map(select(.repo != null)) | .[].name' $registry)
            case agent agents
                set reg_names (jq -r '.repos[].agents[].name' $registry)
        end
        for name in $reg_names
            if not contains -- $name $seen
                set -a lines (_tv_claude_fmt $name "not downloaded" $group_map)
            end
        end
    end

    switch $filter
        case linked
            string match -e -- '[linked]' $lines | sort
        case available
            string match -er -- '\[(?:available|not downloaded)\]' $lines | sort
        case '' all
            printf '%s\n' $lines | sort
        case '*'
            echo "_tv_claude_list: filter must be 'linked', 'available', or empty" >&2
            return 1
    end
end

function _tv_claude_fmt --description "Format one television row: name, registry groups, link status"
    set -l name $argv[1]
    set -l state $argv[2]
    set -l group_map $argv[3..]

    set -l grp ""
    for gm in $group_map
        set -l p (string split -m1 '|' -- $gm)
        if test "$p[1]" = "$name"
            set grp $p[2]
            break
        end
    end

    printf '%-28s  %-46s  [%s]' $name "$grp" $state
end
