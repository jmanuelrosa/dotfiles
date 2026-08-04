function _tv_claude_toggle --description "Television action: toggle link for one or more claude skills or agents" --argument-names kind
    set -l names $argv[2..]
    if test (count $names) -eq 0
        _ui err "_tv_claude_toggle: missing name"
        return 1
    end
    if not command -q claude-kit
        _ui err "claude-kit is not on PATH. Run: make run-role ROLE=ai"
        return 1
    end

    switch $kind
        case skill skills
            _tv_claude_toggle_type skill $names
        case agent agents
            # The agent picker lists agents and seat plugins together, so a selection may
            # hold both and each needs its own --type. Which a name is comes from
            # claude-kit's own plugin listing rather than from probing for a manifest
            # under files/claude/plugins/: that probe is how catalog.py decides what a
            # plugin is, and a second copy of it here is the class of bug this whole
            # function stopped having.
            set -l known (claude-kit list --type plugin --json | jq -r '.[].name')
            set -l agents
            set -l plugins
            for name in $names
                if contains -- $name $known
                    set -a plugins $name
                else
                    set -a agents $name
                end
            end
            set -l rc 0
            test (count $agents) -gt 0; and begin
                _tv_claude_toggle_type agent $agents; or set rc $status
            end
            test (count $plugins) -gt 0; and begin
                _tv_claude_toggle_type plugin $plugins; or set rc $status
            end
            return $rc
        case '*'
            _ui err "_tv_claude_toggle: kind must be 'skill' or 'agent'"
            return 1
    end
end

function _tv_claude_toggle_type --description "Add or remove every named artifact of one type, in the scope claude-kit reports for it" --argument-names type
    set -l names $argv[2..]

    # claude-kit is the authority on both questions this action has to answer: whether an
    # artifact is currently linked, and whether it belongs in ~/.claude. Reading them off
    # its own listing, rather than re-deriving either here, is what keeps the row the
    # picker rendered and the command it runs from disagreeing. Enter can carry a Tab
    # multi-select, so the listing is fetched once for the whole selection.
    set -l payload (claude-kit list --type $type --json)

    set -l rc 0
    for name in $names
        # --arg rather than interpolating into a pattern: this is an exact string
        # comparison, and a name is never a regex or a glob.
        set -l row (printf '%s\n' $payload \
            | jq -r --arg n $name '.[] | select(.name == $n) | [.state, (.global | tostring)] | @tsv' \
            | string split \t)

        # A name the listing does not carry: run the add anyway, so the refusal the user
        # reads is the one claude-kit prints for the same command typed by hand.
        set -l action add
        set -l want_global
        if test (count $row) -eq 2
            test "$row[1]" = linked; and set action remove
            test "$row[2]" = true; and set want_global --global
        end

        claude-kit $action $name --type $type $want_global; or set rc $status
    end
    return $rc
end
