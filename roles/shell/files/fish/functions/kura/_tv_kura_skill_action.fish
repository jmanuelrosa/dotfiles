function _tv_kura_skill_action --description "Television skill actions, expanding category selections" --argument-names action
    set -l names $argv[2..]

    if test "$action" = preview
        if string match -q '@*' -- $names[1]
            kura list --type skill --group (string sub --start 2 -- $names[1])
        else
            bat --color=always --plain --language=markdown "$HOME/.config/kura/catalog/skills/$names[1]/SKILL.md" 2>/dev/null
            or _ui note 'Not downloaded: press Enter to install via kura add --type skill'
        end
        return $status
    end

    set -l categories (string match '@*' -- $names | string sub --start 2)
    if set -q categories[1]
        set -l payload (kura list --type skill --json); or return $status
        set -l members (printf '%s\n' $payload | jq -r --arg action $action --args '
            .[]
            | select(.groups | any(. as $group | $ARGS.positional | index($group)))
            | select($action != "toggle" or .state != "linked")
            | .name' $categories); or return $status
        set names (string match --invert '@*' -- $names) $members
        if not set -q names[1]
            return 0
        end
        set names (printf '%s\n' $names | sort -u)
    end

    switch $action
        case toggle
            _tv_kura_toggle skill $names
        case outdated update
            kura $action --type skill $names
        case edit
            set -l paths
            for name in $names
                set -a paths "$HOME/.config/kura/catalog/skills/$name/SKILL.md"
            end
            $EDITOR $paths
    end
end
