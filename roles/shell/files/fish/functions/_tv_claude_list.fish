function _tv_claude_list --description "Television source: list claude skills or agents with link status" --argument-names kind
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

    set -l seen

    if test -d "$source"
        if test -z "$ext"
            for entry in $source/*/
                set -l name (basename $entry)
                set -a seen $name
                if test -L "$target/$name$ext"
                    printf '%-30s  [linked]\n' $name
                else
                    printf '%-30s  [available]\n' $name
                end
            end
        else
            for entry in $source/*$ext
                test -f "$entry"; or continue
                set -l name (basename $entry $ext)
                set -a seen $name
                if test -L "$target/$name$ext"
                    printf '%-30s  [linked]\n' $name
                else
                    printf '%-30s  [available]\n' $name
                end
            end
        end
    end

    if command -q jq; and test -f "$registry"
        set -l reg_names
        switch $kind
            case skill skills
                set reg_names (jq -r '.repos[].skills[].name' $registry)
            case agent agents
                set reg_names (jq -r '.repos[].agents[].name' $registry)
        end
        for name in $reg_names
            if not contains -- $name $seen
                printf '%-30s  [not downloaded]\n' $name
            end
        end
    end
end
