function _tv_claude_toggle --description "Television action: toggle link for one or more claude skills or agents" --argument-names kind
    set -l names $argv[2..]
    if test (count $names) -eq 0
        echo "_tv_claude_toggle: missing name" >&2
        return 1
    end

    switch $kind
        case skill skills
            for name in $names
                if test -L ".claude/skills/$name"
                    claude-skill remove $name
                else
                    claude-skill add $name
                end
            end
        case agent agents
            for name in $names
                if test -L ".claude/agents/$name.md"
                    claude-agent remove $name
                else
                    claude-agent add $name
                end
            end
        case '*'
            echo "_tv_claude_toggle: kind must be 'skill' or 'agent'" >&2
            return 1
    end
end
