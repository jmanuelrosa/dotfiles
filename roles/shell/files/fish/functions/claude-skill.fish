function claude-skill --description "Manage Claude Code skills for the current project"
    set -l skills_source "$DOTFILES_DIR/roles/ai/files/claude/skills"
    set -l skills_target ".claude/skills"
    set -l registry "$DOTFILES_DIR/roles/ai/files/claude/skill-registry.json"

    set -l c_green (set_color green)
    set -l c_yellow (set_color yellow)
    set -l c_red (set_color red)
    set -l c_cyan (set_color cyan)
    set -l c_dim (set_color brblack)
    set -l c_bold (set_color --bold)
    set -l c_reset (set_color normal)

    if test (count $argv) -lt 1
        echo "Usage: claude-skill <list|add|remove|update|outdated> [--group] [name]"
        return 1
    end

    set -l cmd $argv[1]
    set -l use_group false
    set -l name ""

    for arg in $argv[2..]
        if test "$arg" = "--group"
            set use_group true
        else
            set name "$arg"
        end
    end

    if not command -q jq
        echo "$c_red✗$c_reset Error: jq is required. Install with: brew install jq"
        return 1
    end

    if not test -f "$registry"
        echo "$c_red✗$c_reset Error: Registry not found at $registry"
        return 1
    end

    switch $cmd
        case list
            if test "$use_group" = true
                echo $c_bold"Available groups:"$c_reset

                set -l groups (jq -r '
                    [.repos[].skills[].groups[], .local_skills[].groups[]]
                    | unique | .[]
                ' $registry)

                for g in $groups
                    echo "  $c_cyan$g:$c_reset"
                    set -l names (jq -r --arg g "$g" '
                        [
                            (.repos[].skills[] | select(.groups | index($g))),
                            (.local_skills[]    | select(.groups | index($g)))
                        ] | .[] | .name
                    ' $registry | sort -u)
                    for sname in $names
                        if test -L "$skills_target/$sname"
                            echo "    $c_green✓$c_reset $sname $c_green(linked)$c_reset"
                        else if test -d "$skills_source/$sname"
                            echo "    $c_dim·$c_reset $sname"
                        else
                            echo "    $c_dim↓ $sname (not downloaded)$c_reset"
                        end
                    end
                end
            else
                echo $c_bold"Available skills:"$c_reset
                set -l seen_skills

                if test -d "$skills_source"
                    for skill in $skills_source/*/
                        set -l sname (basename $skill)
                        set -a seen_skills $sname
                        if test -L "$skills_target/$sname"
                            echo "  $c_green✓$c_reset $sname $c_green(linked)$c_reset"
                        else
                            echo "  $c_dim·$c_reset $sname"
                        end
                    end
                end

                set -l reg_names (jq -r '.repos[].skills[].name' $registry)
                for sname in $reg_names
                    if not contains -- $sname $seen_skills
                        echo "  $c_dim↓ $sname (not downloaded)$c_reset"
                    end
                end
            end

        case add
            if test -z "$name"
                echo "Usage: claude:skill add [--group] <name>"
                return 1
            end
            if test "$use_group" = true
                set -l group_skills (jq -r --arg g "$name" '
                    [
                        (.repos[].skills[] | select(.groups | index($g))),
                        (.local_skills[]    | select(.groups | index($g)))
                    ] | .[] | .name
                ' $registry | sort -u)

                if test (count $group_skills) -eq 0
                    echo "$c_red✗$c_reset Group '$name' not found. Run 'claude:skill list --group' to see available groups."
                    return 1
                end

                set -l tracked_names (jq -r '.repos[].skills[].name' $registry)

                for sname in $group_skills
                    if not test -d "$skills_source/$sname"
                        if contains -- $sname $tracked_names
                            echo "$c_cyan↓$c_reset Downloading '$sname' from registry..."
                            _claude_skill_update $registry "$DOTFILES_DIR/roles/ai/files/claude" $sname
                        else
                            echo "$c_red✗$c_reset Local skill '$sname' missing on disk; cannot install."
                            continue
                        end
                    end
                end

                mkdir -p $skills_target
                set -l count 0
                for sname in $group_skills
                    if test -d "$skills_source/$sname"
                        ln -sf "$skills_source/$sname" "$skills_target/$sname"
                        set count (math $count + 1)
                    end
                end
                echo "$c_green✓$c_reset Linked $count skills from group '$name' into $skills_target/"
            else
                if not test -d "$skills_source/$name"
                    set -l in_registry (jq -r --arg n "$name" '
                        [.repos[].skills[] | select(.name == $n) | .name] | .[0] // empty
                    ' $registry)
                    if test -n "$in_registry"
                        echo "$c_cyan↓$c_reset Skill '$name' not downloaded. Pulling from registry..."
                        _claude_skill_update $registry "$DOTFILES_DIR/roles/ai/files/claude" $name
                        if not test -d "$skills_source/$name"
                            echo "$c_red✗$c_reset Failed to download '$name'."
                            return 1
                        end
                    else
                        echo "$c_red✗$c_reset Skill '$name' not found. Run 'claude:skill list' to see available skills."
                        return 1
                    end
                end
                mkdir -p $skills_target
                ln -sf "$skills_source/$name" "$skills_target/$name"
                echo "$c_green✓$c_reset Linked '$name' into $skills_target/"
            end

        case remove
            if test -z "$name"
                echo "Usage: claude:skill remove [--group] <name>"
                return 1
            end
            if test "$use_group" = true
                set -l group_skills (jq -r --arg g "$name" '
                    [
                        (.repos[].skills[] | select(.groups | index($g))),
                        (.local_skills[]    | select(.groups | index($g)))
                    ] | .[] | .name
                ' $registry | sort -u)

                if test (count $group_skills) -eq 0
                    echo "$c_red✗$c_reset Group '$name' not found. Run 'claude:skill list --group' to see available groups."
                    return 1
                end

                set -l count 0
                for sname in $group_skills
                    if test -L "$skills_target/$sname"
                        command rm "$skills_target/$sname"
                        set count (math $count + 1)
                    end
                end
                echo "$c_green✓$c_reset Removed $count skills from group '$name'"
            else
                if not test -L "$skills_target/$name"
                    echo "$c_yellow⚠$c_reset Skill '$name' is not linked in this project."
                    return 1
                end
                command rm "$skills_target/$name"
                echo "$c_green✓$c_reset Removed '$name' from $skills_target/"
            end

        case update
            _claude_skill_update $registry "$DOTFILES_DIR/roles/ai/files/claude" "$name" sync

        case outdated
            _claude_skill_update $registry "$DOTFILES_DIR/roles/ai/files/claude" "$name" check

        case '*'
            echo "Usage: claude-skill <list|add|remove|update|outdated> [--group] [name]"
            return 1
    end
end

function _claude_skill_update --description "Sync (or check) skills against upstream GitHub repos"
    set -l registry $argv[1]
    set -l base_dir $argv[2]
    set -l target_skill $argv[3]
    set -l mode $argv[4]
    if test -z "$mode"
        set mode sync
    end

    set -l c_green (set_color green)
    set -l c_yellow (set_color yellow)
    set -l c_red (set_color red)
    set -l c_cyan (set_color cyan)
    set -l c_dim (set_color brblack)
    set -l c_bold (set_color --bold)
    set -l c_reset (set_color normal)

    set -l exclude_args --exclude=.git --exclude=.github --exclude=node_modules

    if not command -q jq
        echo "$c_red✗$c_reset Error: jq is required. Install with: brew install jq"
        return 1
    end

    if not test -f "$registry"
        echo "$c_red✗$c_reset Error: Registry not found at $registry"
        return 1
    end

    set -l repos
    if test -n "$target_skill"
        set repos (jq -r --arg skill "$target_skill" '
            .repos | to_entries[] |
            select(.value.skills[] | .name == $skill) |
            .key
        ' $registry)

        if test -z "$repos"
            set -l is_local (jq -r --arg skill "$target_skill" '
                [.local_skills[]? | select(.name == $skill)] | length
            ' $registry)
            if test "$is_local" != "0"
                echo "$c_yellow⚠$c_reset '$target_skill' is a local skill; no upstream to sync."
                return 0
            end
            echo "$c_red✗$c_reset Skill '$target_skill' not found in registry."
            echo "Tracked skills:"
            jq -r '.repos[].skills[].name' $registry | sort | sed 's/^/  /'
            return 1
        end
    else
        set repos (jq -r '.repos | keys[]' $registry)
    end

    set -l tmpdir (mktemp -d)
    set -l updated 0
    set -l skipped 0
    set -l failed 0
    set -l missing 0
    set -l n_repos (count $repos)

    if test "$mode" = check
        echo $c_bold"Checking $n_repos repo(s) for updates..."$c_reset
    else
        echo $c_bold"Syncing from $n_repos repo(s)..."$c_reset
    end
    echo ""

    for repo in $repos
        set -l branch (jq -r --arg r "$repo" '.repos[$r].branch' $registry)
        set -l clone_dir "$tmpdir/"(string replace "/" "_" $repo)

        set -l skill_entries
        if test -n "$target_skill"
            set skill_entries (jq -r --arg r "$repo" --arg skill "$target_skill" '
                .repos[$r].skills[] | select(.name == $skill) |
                "\(.upstream_path)|\(.name)"
            ' $registry)
        else
            set skill_entries (jq -r --arg r "$repo" '
                .repos[$r].skills[] |
                "\(.upstream_path)|\(.name)"
            ' $registry)
        end

        echo "$c_cyan── $repo ($branch) ──$c_reset"

        mkdir -p "$clone_dir"
        curl -sfL "https://github.com/$repo/archive/$branch.tar.gz" | tar -xz -C "$clone_dir" --strip-components=1
        if test $pipestatus[1] -ne 0 -o $pipestatus[2] -ne 0
            echo "  $c_red✗ FAILED to fetch$c_reset"
            set failed (math $failed + 1)
            continue
        end

        for entry in $skill_entries
            set -l parts (string split "|" $entry)
            set -l upstream_path $parts[1]
            set -l skill_name $parts[2]

            set -l src "$clone_dir/$upstream_path"
            set -l dst "$base_dir/skills/$skill_name"

            if test "$upstream_path" = "."
                set src "$clone_dir"
            end

            if not test -d "$src"
                echo "  $c_red✗$c_reset $skill_name: upstream path '$upstream_path' not found"
                set failed (math $failed + 1)
                continue
            end

            set -l last_synced (jq -r --arg repo "$repo" --arg name "$skill_name" '
                .repos[$repo].skills[] | select(.name == $name) | .updated_at // "never"
            ' $registry | string sub --length 10)

            if not test -d "$dst"
                if test "$mode" = check
                    echo "  $c_dim↓$c_reset $skill_name: $c_dim"not downloaded"$c_reset"
                    set missing (math $missing + 1)
                else
                    mkdir -p (dirname "$dst")
                    rsync -a $exclude_args "$src/" "$dst/"
                    echo "  $c_green✓$c_reset $skill_name: "$c_green"installed (new)"$c_reset
                    set updated (math $updated + 1)
                    _claude_registry_stamp $registry $repo $skill_name skills
                end
                continue
            end

            set -l diff_output (diff -rq $exclude_args "$src" "$dst" 2>/dev/null)
            if test -z "$diff_output"
                echo "  $c_dim·$c_reset $skill_name: "$c_dim"up to date (last synced $last_synced)"$c_reset
                set skipped (math $skipped + 1)
                if test "$mode" = sync
                    _claude_registry_stamp $registry $repo $skill_name skills
                end
                continue
            end

            if test "$mode" = check
                echo "  $c_yellow⟳$c_reset $skill_name: "$c_yellow"behind"$c_reset" $c_dim(last synced $last_synced)$c_reset"
                set updated (math $updated + 1)
            else
                command rm -rf "$dst"
                rsync -a $exclude_args "$src/" "$dst/"
                set updated (math $updated + 1)
                echo "  $c_yellow⟳$c_reset $skill_name: $c_green✓ synced.$c_reset"
                _claude_registry_stamp $registry $repo $skill_name skills
            end
        end

        echo ""
    end

    rm -rf "$tmpdir"

    if test "$mode" = check
        printf '%sDone:%s %s%d%s behind, %s%d%s up-to-date, %s%d%s not downloaded, %s%d%s failed\n' \
            $c_bold $c_reset \
            $c_yellow $updated $c_reset \
            $c_dim $skipped $c_reset \
            $c_dim $missing $c_reset \
            $c_red $failed $c_reset
    else
        printf '%sDone:%s %s%d%s updated, %s%d%s up-to-date, %s%d%s failed\n' \
            $c_bold $c_reset \
            $c_green $updated $c_reset \
            $c_dim $skipped $c_reset \
            $c_red $failed $c_reset
    end
end

function _claude_registry_stamp --description "Record updated_at on a tracked registry entry"
    set -l registry $argv[1]
    set -l repo $argv[2]
    set -l name $argv[3]
    set -l array_key $argv[4]

    set -l now (date -u +%Y-%m-%dT%H:%M:%SZ)
    set -l tmp (mktemp)
    if jq --arg repo "$repo" --arg name "$name" --arg ts "$now" --arg key "$array_key" '
        .repos[$repo][$key] |= map(if .name == $name then .updated_at = $ts else . end)
    ' $registry > $tmp
        mv $tmp $registry
    else
        rm -f $tmp
    end
end
