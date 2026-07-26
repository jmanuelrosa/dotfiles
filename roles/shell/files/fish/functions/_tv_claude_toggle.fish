function _tv_claude_toggle --description "Television action: toggle link for one or more claude skills or agents" --argument-names kind
    set -l names $argv[2..]
    if test (count $names) -eq 0
        echo "_tv_claude_toggle: missing name" >&2
        return 1
    end

    # Ask _claude_scope_target where each artifact lives rather than assuming the cwd,
    # so the toggle reads the same location claude-skill/claude-agent will write to.
    switch $kind
        case skill skills
            for name in $names
                set -l target (_claude_scope_target skill $name)
                if test -n "$target"; and test -L "$target/$name"
                    claude-skill remove $name
                else
                    claude-skill add $name
                end
            end
        case agent agents
            set -l plugins_source $DOTFILES_DIR/roles/ai/files/claude/plugins
            for name in $names
                # A seat plugin links as a folder into the skills dir; a plain agent as a .md into the agents dir.
                if test -f "$plugins_source/$name/.claude-plugin/plugin.json"
                    set -l ptarget (_claude_scope_target plugin $name)
                    if test -n "$ptarget"; and test -L "$ptarget/$name"
                        claude-agent remove $name
                    else
                        claude-agent add $name
                    end
                    continue
                end
                set -l atarget (_claude_scope_target agent $name)
                if test -n "$atarget"; and test -L "$atarget/$name.md"
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
