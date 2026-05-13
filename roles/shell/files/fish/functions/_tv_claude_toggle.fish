function _tv_claude_toggle --description "Television action: toggle link for a claude skill or agent" --argument-names kind name
    if test -z "$name"
        echo "_tv_claude_toggle: missing name" >&2
        return 1
    end

    switch $kind
        case skill skills
            if test -L ".claude/skills/$name"
                claude-skill remove $name
            else
                claude-skill add $name
            end
        case agent agents
            if test -L ".claude/agents/$name.md"
                claude-agent remove $name
            else
                claude-agent add $name
            end
        case '*'
            echo "_tv_claude_toggle: kind must be 'skill' or 'agent'" >&2
            return 1
    end
end
