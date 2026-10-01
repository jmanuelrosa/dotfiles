function _tv_kura_toggle --description "Television action: toggle links for catalog skills" --argument-names kind
    set -l names $argv[2..]
    if test (count $names) -eq 0
        _ui err "_tv_kura_toggle: missing name"
        return 1
    end
    if not command -q kura
        _ui err "kura is not on PATH. Run: make run-role ROLE=ai"
        return 1
    end

    if not contains -- $kind skill skills
        _ui err "_tv_kura_toggle: kind must be 'skill'"
        return 1
    end
    _tv_kura_toggle_type skill $names
end

function _tv_kura_toggle_type --description "Add or remove every named artifact of one type, in the scope kura reports for it" --argument-names type
    set -l names $argv[2..]

    # kura is the authority on both questions this action has to answer: whether an
    # artifact is currently linked, and whether it belongs in ~/.claude. Reading them off
    # its own listing, rather than re-deriving either here, is what keeps the row the
    # picker rendered and the command it runs from disagreeing. Enter can carry a Tab
    # multi-select, so the listing is fetched once for the whole selection.
    set -l payload (kura list --type $type --json)

    set -l rc 0
    for name in $names
        # --arg rather than interpolating into a pattern: this is an exact string
        # comparison, and a name is never a regex or a glob.
        set -l row (printf '%s\n' $payload \
            | jq -r --arg n $name '.[] | select(.name == $n) | [.state, (.global | tostring)] | @tsv' \
            | string split \t)

        # A name the listing does not carry: run the add anyway, so the refusal the user
        # reads is the one kura prints for the same command typed by hand.
        set -l action add
        set -l want_global
        if test (count $row) -eq 2
            test "$row[1]" = linked; and set action remove
            test "$row[2]" = true; and set want_global --global
        end

        kura $action $name --type $type $want_global; or set rc $status
    end
    return $rc
end
