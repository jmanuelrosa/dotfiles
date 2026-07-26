function _claude_scope_is_global --description "Exit 0 if a claude skill, agent, or plugin carries the 'global' scope tag" --argument-names kind name
    set -l base "$DOTFILES_DIR/roles/ai/files/claude"

    switch $kind
        case agent agents
            test (jq -r --arg n "$name" '
                [ (.repos[]?.agents[]?), (.local_agents[]?) ]
                | map(select(.name == $n and (((.groups // []) | index("global")) != null)))
                | length
            ' "$base/agent-registry.json" 2>/dev/null) != 0

        case plugin plugins
            set -l manifest "$base/plugins/$name/.claude-plugin/plugin.json"
            test -f "$manifest"; or return 1
            test (jq -r '[(.groups // [])[] | select(. == "global")] | length' "$manifest" 2>/dev/null) != 0

        case skill skills
            # Membership in the effective set, not just the tag: the ai role also links
            # one level of dependencies declared by global skills and agents.
            contains -- $name (_claude_scope_global_skills)

        case '*'
            echo "_claude_scope_is_global: kind must be 'skill', 'agent', or 'plugin'" >&2
            return 2
    end
end
