function _claude_scope_refuse --description "Explain why a project-scoped claude artifact cannot be installed here" --argument-names name
    set -l c_magenta (set_color magenta)
    set -l c_dim (set_color brblack)
    set -l c_reset (set_color normal)
    echo "$c_magenta✗$c_reset '$name' is project-scoped: it installs into a repo, not user-wide."
    echo "  $c_dim""cd into a project first. \$HOME is not one, and ~/.claude is reserved for"
    echo "  artifacts tagged 'global' in the registry (managed by 'make run-role ROLE=ai').$c_reset"
end
