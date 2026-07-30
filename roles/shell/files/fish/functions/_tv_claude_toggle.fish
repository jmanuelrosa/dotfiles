function _tv_claude_toggle --description "Television action: toggle link for one or more claude skills or agents" --argument-names kind
    set -l names $argv[2..]
    if test (count $names) -eq 0
        _ui err "_tv_claude_toggle: missing name"
        return 1
    end

    set -l rc 0
    switch $kind
        case skill skills
            for name in $names
                _tv_claude_toggle_one skill $name ""; or set rc $status
            end
        case agent agents
            set -l plugins_source $DOTFILES_DIR/roles/ai/files/claude/plugins
            for name in $names
                # A seat plugin links as a folder into the skills dir; a plain agent as a .md into the agents dir.
                if test -f "$plugins_source/$name/.claude-plugin/plugin.json"
                    _tv_claude_toggle_one plugin $name ""; or set rc $status
                else
                    _tv_claude_toggle_one agent $name .md; or set rc $status
                end
            end
        case '*'
            _ui err "_tv_claude_toggle: kind must be 'skill' or 'agent'"
            return 1
    end
    return $rc
end

function _tv_claude_toggle_one --description "Add or remove one artifact through claude-kit, in the scope its tag dictates" --argument-names type name ext
    if not command -q claude-kit
        _ui err "claude-kit is not on PATH. Run: make run-role ROLE=ai"
        return 1
    end

    # _claude_scope_target stays the authority on *where*, and the toggle runs
    # claude-kit from there. The two disagree on what a project is: claude-kit
    # anchors at the cwd, this anchors at the repo root, which is where a Claude
    # session scans. Television is launched from anywhere in a checkout, so
    # without the pushd below Enter would link into a subdirectory the session
    # never reads, and the row _tv_claude_list renders would stay [available].
    set -l target (_claude_scope_target $type $name)

    set -l action add
    if test -n "$target"; and test -L "$target/$name$ext"
        set action remove
    end

    # A global artifact lands in ~/.claude wherever it is invoked from, and
    # claude-kit requires --global as confirmation of exactly that.
    if _claude_scope_is_global $type $name
        claude-kit $action $name --type $type --global
        return $status
    end

    # Nowhere to install into: run it anyway so the refusal the user reads is the
    # one claude-kit prints for the same command typed by hand.
    if test -z "$target"
        claude-kit $action $name --type $type
        return $status
    end

    pushd (path dirname (path dirname $target))
    claude-kit $action $name --type $type
    set -l rc $status
    popd
    return $rc
end
