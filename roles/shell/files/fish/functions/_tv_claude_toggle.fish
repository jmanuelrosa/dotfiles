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
            set -l proot (git rev-parse --show-toplevel 2>/dev/null)
            test -n "$proot"; or set proot (pwd)
            set -l plugins_source $DOTFILES_DIR/roles/ai/files/claude/plugins
            for name in $names
                # A seat plugin links as a folder into .claude/skills/; a plain agent as a .md into .claude/agents/.
                if test -f "$plugins_source/$name/.claude-plugin/plugin.json"
                    if test -L "$proot/.claude/skills/$name"
                        claude-agent remove $name
                    else
                        claude-agent add $name
                    end
                else if test -L "$proot/.claude/agents/$name.md"
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
