function _claude_scope_target --description "Print the install dir for a claude artifact: ~/.claude for global-tagged ones, the project otherwise. Empty output means there is no project to install into." --argument-names kind name
    # The `global` tag is the single source of truth for scope, so location follows
    # the artifact rather than the shell's cwd. A global artifact installs ONLY into
    # ~/.claude (which the ai role owns and prunes); everything else installs ONLY
    # into a project. Seat plugins link as a folder into the skills dir.
    set -l leaf skills
    switch $kind
        case agent agents
            set leaf agents
    end

    if _claude_scope_is_global $kind $name
        echo "$HOME/.claude/$leaf"
        return 0
    end

    # Anchor to the repo root (where Claude Code scans and where workspace trust is
    # keyed), not CWD, so "linked" means "linked where the session will look".
    set -l project_root (git rev-parse --show-toplevel 2>/dev/null)
    if test -z "$project_root"; or test "$project_root" = "$HOME"
        return 1
    end
    echo "$project_root/.claude/$leaf"
    return 0
end
