function _claude_scope_global_skills --description "Print the effective global skill names: those tagged 'global' plus one level of dependencies declared by global skills and global agents"
    # Mirrors GLOBAL_CLAUDE_SKILLS_EFFECTIVE in roles/ai/tasks/main.yml, which is what
    # the ai role actually symlinks into ~/.claude/skills. Tag membership alone is not
    # enough: grilling, jira, domain-modeling, documentation-and-adrs and
    # planning-and-task-breakdown reach ~/.claude only as declared dependencies.
    # Keep the two in sync; the role is the authority.
    set -l base "$DOTFILES_DIR/roles/ai/files/claude"

    set -l agent_deps (jq -c '
        [ (.repos[]?.agents[]?), (.local_agents[]?) ]
        | map(select(((.groups // []) | index("global")) != null))
        | map(.dependencies // []) | flatten | unique
    ' "$base/agent-registry.json" 2>/dev/null)
    test -n "$agent_deps"; or set agent_deps '[]'

    set -l prog (_claude_skill_jqlib)'
        allskills as $all
        | ([ $all[] | select(((.groups // []) | index("global")) != null) | .name ] + $ad | unique) as $seed
        | ($seed + [ $all[] | select(.name | IN($seed[])) | .dependencies // [] | .[] ] | unique)
        | .[]'
    jq -r --argjson ad "$agent_deps" $prog "$base/skill-registry.json" 2>/dev/null
end
