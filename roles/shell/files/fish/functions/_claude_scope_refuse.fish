function _claude_scope_refuse --description "Explain why a project-scoped claude artifact cannot be installed here" --argument-names name
    _ui err "'$name' is project-scoped: it installs into a repo, not user-wide."
    _ui note "cd into a project first. \$HOME is not one, and ~/.claude is reserved for"
    _ui note "artifacts tagged 'global' in the registry (managed by 'make run-role ROLE=ai')."
end
