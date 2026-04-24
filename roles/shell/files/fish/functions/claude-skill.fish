function claude-skill --description "Manage Claude Code skills for the current project"
    set -l skills_source "$DOTFILES_DIR/roles/ai/files/claude/skills"
    set -l groups_source "$DOTFILES_DIR/roles/ai/files/claude/skill-groups"
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
        echo "Usage: claude:skill <list|add|remove|update> [--group] [name]"
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

    switch $cmd
        case list
            if test "$use_group" = true
                echo $c_bold"Available groups:"$c_reset
                set -l seen_groups

                if test -d "$groups_source"
                    for group in $groups_source/*/
                        set -l gname (basename $group)
                        set -a seen_groups $gname
                        echo "  $c_cyan$gname:$c_reset"

                        set -l seen_skills
                        for skill in $group/*/
                            set -l sname (basename $skill)
                            set -a seen_skills $sname
                            if test -L "$skills_target/$sname"
                                echo "    $c_green✓$c_reset $sname $c_green(linked)$c_reset"
                            else
                                echo "    $c_dim·$c_reset $sname"
                            end
                        end

                        if command -q jq; and test -f "$registry"
                            set -l reg_names (jq -r --arg g "$gname" '
                                .repos[].skills[] |
                                select(.local_path | startswith("skill-groups/" + $g + "/")) |
                                .name
                            ' $registry)
                            for sname in $reg_names
                                if not contains -- $sname $seen_skills
                                    echo "    $c_dim↓ $sname (not downloaded)$c_reset"
                                end
                            end
                        end
                    end
                end

                if command -q jq; and test -f "$registry"
                    set -l reg_groups (jq -r '
                        .repos[].skills[] |
                        select(.local_path | startswith("skill-groups/")) |
                        .local_path | split("/")[1]
                    ' $registry | sort -u)
                    for g in $reg_groups
                        if not contains -- $g $seen_groups
                            echo "  $c_cyan$g:$c_reset"
                            set -l reg_names (jq -r --arg g "$g" '
                                .repos[].skills[] |
                                select(.local_path | startswith("skill-groups/" + $g + "/")) |
                                .name
                            ' $registry)
                            for sname in $reg_names
                                echo "    $c_dim↓ $sname (not downloaded)$c_reset"
                            end
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

                if command -q jq; and test -f "$registry"
                    set -l reg_names (jq -r '
                        .repos[].skills[] |
                        select((.local_path | startswith("skills/")) and ((.local_path | split("/") | length) == 2)) |
                        .name
                    ' $registry)
                    for sname in $reg_names
                        if not contains -- $sname $seen_skills
                            echo "  $c_dim↓ $sname (not downloaded)$c_reset"
                        end
                    end
                end
            end

        case add
            if test -z "$name"
                echo "Usage: claude:skill add [--group] <name>"
                return 1
            end
            if test "$use_group" = true
                set -l group_dir "$groups_source/$name"

                set -l reg_skill_names
                if command -q jq; and test -f "$registry"
                    set reg_skill_names (jq -r --arg g "$name" '
                        .repos[].skills[] |
                        select(.local_path | startswith("skill-groups/" + $g + "/")) |
                        .name
                    ' $registry)
                end

                if not test -d "$group_dir"; and test (count $reg_skill_names) -eq 0
                    echo "$c_red✗$c_reset Group '$name' not found. Run 'claude:skill list --group' to see available groups."
                    return 1
                end

                for sname in $reg_skill_names
                    if not test -d "$group_dir/$sname"
                        echo "$c_cyan↓$c_reset Downloading '$sname' from registry..."
                        _claude_skill_update $registry "$DOTFILES_DIR/roles/ai/files/claude" $sname
                    end
                end

                if not test -d "$group_dir"
                    echo "$c_red✗$c_reset Group '$name' not available after download. Check registry and retry."
                    return 1
                end

                mkdir -p $skills_target
                set -l count 0
                for skill in $group_dir/*/
                    set -l sname (basename $skill)
                    ln -sf "$group_dir/$sname" "$skills_target/$sname"
                    set count (math $count + 1)
                end
                echo "$c_green✓$c_reset Linked $count skills from group '$name' into $skills_target/"
            else
                if not test -d "$skills_source/$name"
                    set -l match_flat
                    set -l match_group
                    if command -q jq; and test -f "$registry"
                        set match_flat (jq -r --arg n "$name" '
                            .repos[].skills[] |
                            select(.name == $n and ((.local_path | startswith("skills/")) and ((.local_path | split("/") | length) == 2))) |
                            .name
                        ' $registry)
                        set match_group (jq -r --arg n "$name" '
                            .repos[].skills[] |
                            select(.name == $n and (.local_path | startswith("skill-groups/"))) |
                            .local_path | split("/")[1]
                        ' $registry)
                    end

                    if test -n "$match_flat"
                        echo "$c_cyan↓$c_reset Skill '$name' not downloaded. Pulling from registry..."
                        _claude_skill_update $registry "$DOTFILES_DIR/roles/ai/files/claude" $name
                        if not test -d "$skills_source/$name"
                            echo "$c_red✗$c_reset Failed to download '$name'."
                            return 1
                        end
                    else if test -n "$match_group"
                        echo "$c_yellow⚠$c_reset Skill '$name' is a grouped skill. Try: claude:skill add --group $match_group"
                        return 1
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
                if not test -d "$groups_source/$name"
                    echo "$c_red✗$c_reset Group '$name' not found. Run 'claude:skill list --group' to see available groups."
                    return 1
                end
                set -l count 0
                for skill in $groups_source/$name/*/
                    set -l sname (basename $skill)
                    if test -L "$skills_target/$sname"
                        rm "$skills_target/$sname"
                        set count (math $count + 1)
                    end
                end
                echo "$c_green✓$c_reset Removed $count skills from group '$name'"
            else
                if not test -L "$skills_target/$name"
                    echo "$c_yellow⚠$c_reset Skill '$name' is not linked in this project."
                    return 1
                end
                rm "$skills_target/$name"
                echo "$c_green✓$c_reset Removed '$name' from $skills_target/"
            end

        case update
            _claude_skill_update $registry "$DOTFILES_DIR/roles/ai/files/claude" $name

        case '*'
            echo "Usage: claude:skill <list|add|remove|update> [--group] [name]"
            return 1
    end
end

function _claude_skill_update --description "Sync skills from upstream GitHub repos"
    set -l registry $argv[1]
    set -l base_dir $argv[2]
    set -l target_skill $argv[3]

    set -l c_green (set_color green)
    set -l c_yellow (set_color yellow)
    set -l c_red (set_color red)
    set -l c_cyan (set_color cyan)
    set -l c_dim (set_color brblack)
    set -l c_bold (set_color --bold)
    set -l c_reset (set_color normal)

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
    set -l n_repos (count $repos)

    echo $c_bold"Syncing from $n_repos repo(s)..."$c_reset
    echo ""

    for repo in $repos
        set -l branch (jq -r --arg r "$repo" '.repos[$r].branch' $registry)
        set -l clone_dir "$tmpdir/"(string replace "/" "_" $repo)

        set -l skill_entries
        if test -n "$target_skill"
            set skill_entries (jq -r --arg r "$repo" --arg skill "$target_skill" '
                .repos[$r].skills[] | select(.name == $skill) |
                "\(.upstream_path)|\(.local_path)|\(.name)"
            ' $registry)
        else
            set skill_entries (jq -r --arg r "$repo" '
                .repos[$r].skills[] |
                "\(.upstream_path)|\(.local_path)|\(.name)"
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
            set -l local_path $parts[2]
            set -l skill_name $parts[3]

            set -l src "$clone_dir/$upstream_path"
            set -l dst "$base_dir/$local_path"

            if test "$upstream_path" = "."
                set src "$clone_dir"
            end

            if not test -d "$src"
                echo "  $c_red✗$c_reset $skill_name: upstream path '$upstream_path' not found"
                set failed (math $failed + 1)
                continue
            end

            if not test -d "$dst"
                mkdir -p (dirname "$dst")
                rsync -a --exclude='.git' "$src/" "$dst/"
                echo "  $c_green✓$c_reset $skill_name: "$c_green"installed (new)"$c_reset
                set updated (math $updated + 1)
                continue
            end

            set -l diff_output (diff -rq --exclude='.git' "$src" "$dst" 2>/dev/null)
            if test -z "$diff_output"
                echo "  $c_dim·$c_reset $skill_name: "$c_dim"up to date"$c_reset
                set skipped (math $skipped + 1)
                continue
            end

            echo "  $c_yellow⟳$c_reset $skill_name:"
            for line in $diff_output
                if string match -q "Only in $src*" $line
                    set -l file (echo $line | string replace -r "Only in .+: " "")
                    echo "    $c_green+$c_reset $file $c_dim(new upstream)$c_reset"
                else if string match -q "Only in $dst*" $line
                    set -l file (echo $line | string replace -r "Only in .+: " "")
                    echo "    $c_dim~ $file (local only, kept)$c_reset"
                else if string match -q "Files * differ" $line
                    set -l file (echo $line | string replace -r "Files .+/(.+) and .+ differ" '$1')
                    echo "    $c_yellow*$c_reset $file $c_dim(changed)$c_reset"
                end
            end

            rsync -a --exclude='.git' "$src/" "$dst/"
            set updated (math $updated + 1)
            echo "    $c_green✓ synced.$c_reset"
        end

        echo ""
    end

    rm -rf "$tmpdir"

    printf '%sDone:%s %s%d%s updated, %s%d%s up-to-date, %s%d%s failed\n' \
        $c_bold $c_reset \
        $c_green $updated $c_reset \
        $c_dim $skipped $c_reset \
        $c_red $failed $c_reset
end
