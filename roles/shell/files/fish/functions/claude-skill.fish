function claude-skill --description "Manage Claude Code skills for the current project"
    set -l base_dir "$DOTFILES_DIR/roles/ai/files/claude"
    set -l skills_source "$base_dir/skills"
    set -l skills_target ".claude/skills"
    set -l registry "$base_dir/skill-registry.json"

    set -l c_green (set_color green)
    set -l c_yellow (set_color yellow)
    set -l c_red (set_color red)
    set -l c_blue (set_color blue)
    set -l c_magenta (set_color magenta)
    set -l c_cyan (set_color cyan)
    set -l c_dim (set_color brblack)
    set -l c_bold (set_color --bold)
    set -l c_reset (set_color normal)

    if test (count $argv) -lt 1
        echo "Usage: claude-skill <list|add|remove|update|outdated> [--group] [name]..."
        return 1
    end

    set -l cmd $argv[1]
    set -l use_group false
    set -l names

    for arg in $argv[2..]
        if test "$arg" = "--group"
            set use_group true
        else
            set -a names "$arg"
        end
    end

    if not command -q jq
        echo "$c_magenta✗$c_reset Error: jq is required. Install with: brew install jq"
        return 1
    end

    if not test -f "$registry"
        echo "$c_magenta✗$c_reset Error: Registry not found at $registry"
        return 1
    end

    if contains -- $cmd add update
        _claude_skill_check_collisions $registry; or return 1
    end

    switch $cmd
        case list
            if test "$use_group" = true
                echo $c_bold"Available groups:"$c_reset

                set -l prog (_claude_skill_jqlib)' [ visibleskills[] | .groups[]? ] | unique | .[]'
                set -l groups (jq -r $prog $registry)

                for g in $groups
                    echo "  $c_cyan$g:$c_reset"
                    set -l prog (_claude_skill_jqlib)' visibleskills | map(select(.groups | index($g))) | .[].name'
                    set -l names (jq -r --arg g "$g" $prog $registry | sort -u)
                    for sname in $names
                        set -l deps (_claude_skill_direct_deps $registry $sname)
                        set -l dep_suffix ""
                        test -n "$deps"; and set dep_suffix " $c_dim(needs: $deps)$c_reset"
                        if test -L "$skills_target/$sname"
                            echo "    $c_green✓$c_reset $sname $c_green(linked)$c_reset$dep_suffix"
                        else if test -d "$skills_source/$sname"
                            echo "    $c_dim·$c_reset $sname$dep_suffix"
                        else
                            echo "    $c_dim↓ $sname (not downloaded)$c_reset$dep_suffix"
                        end
                    end
                end
            else
                echo $c_bold"Available skills:"$c_reset
                set -l seen_skills

                if test -d "$skills_source"
                    for skill in $skills_source/*/
                        set -l sname (basename $skill)
                        if _claude_skill_is_hidden $registry $sname
                            continue
                        end
                        set -a seen_skills $sname
                        set -l deps (_claude_skill_direct_deps $registry $sname)
                        set -l dep_suffix ""
                        test -n "$deps"; and set dep_suffix " $c_dim(needs: $deps)$c_reset"
                        set -l grp (_claude_skill_groups $registry $sname)
                        set -l grp_suffix ""
                        test -n "$grp"; and set grp_suffix " $c_cyan""[$grp]""$c_reset"
                        if test -L "$skills_target/$sname"
                            echo "  $c_green✓$c_reset $sname $c_green(linked)$c_reset$grp_suffix$dep_suffix"
                        else
                            echo "  $c_dim·$c_reset $sname$grp_suffix$dep_suffix"
                        end
                    end
                end

                set -l prog (_claude_skill_jqlib)' visibleskills | map(select(.repo != null)) | .[].name'
                set -l reg_names (jq -r $prog $registry)
                for sname in $reg_names
                    if not contains -- $sname $seen_skills
                        set -l deps (_claude_skill_direct_deps $registry $sname)
                        set -l dep_suffix ""
                        test -n "$deps"; and set dep_suffix " $c_dim(needs: $deps)$c_reset"
                        set -l grp (_claude_skill_groups $registry $sname)
                        set -l grp_suffix ""
                        test -n "$grp"; and set grp_suffix " $c_cyan""[$grp]""$c_reset"
                        echo "  $c_dim↓ $sname (not downloaded)$c_reset$grp_suffix$dep_suffix"
                    end
                end
            end

        case add
            if test (count $names) -eq 0
                echo "Usage: claude-skill add [--group] <name>..."
                return 1
            end
            if test "$use_group" = true
                for name in $names
                    set -l prog (_claude_skill_jqlib)' visibleskills | map(select(.groups | index($g))) | .[].name'
                    set -l group_skills (jq -r --arg g "$name" $prog $registry | sort -u)

                    if test (count $group_skills) -eq 0
                        echo "$c_magenta✗$c_reset Group '$name' not found. Run 'claude-skill list --group' to see available groups."
                        continue
                    end

                    set -l want $group_skills
                    for sname in $group_skills
                        for d in (_claude_skill_deps $registry $sname)
                            if not contains -- $d $want
                                set -a want $d
                            end
                        end
                    end

                    set -l count 0
                    for sname in $want
                        set -l label ""
                        if not contains -- $sname $group_skills
                            set label "required by group '$name'"
                        end
                        if _claude_skill_ensure_linked $skills_source $skills_target $registry $base_dir $sname $label
                            set count (math $count + 1)
                        end
                    end
                    echo "$c_green✓$c_reset Linked $count skills for group '$name' into $skills_target/"
                end
            else
                for name in $names
                    if _claude_skill_is_hidden $registry $name
                        echo "$c_magenta✗$c_reset '$name' is a dependency-only skill (installed automatically with the skill that requires it). Add the parent skill instead."
                        continue
                    end
                    for d in (_claude_skill_deps $registry $name)
                        _claude_skill_ensure_linked $skills_source $skills_target $registry $base_dir $d "required by $name"
                    end
                    _claude_skill_ensure_linked $skills_source $skills_target $registry $base_dir $name
                end
            end

        case remove
            if test (count $names) -eq 0
                echo "Usage: claude-skill remove [--group] <name>..."
                return 1
            end
            if test "$use_group" = true
                for name in $names
                    set -l prog (_claude_skill_jqlib)' visibleskills | map(select(.groups | index($g))) | .[].name'
                    set -l group_skills (jq -r --arg g "$name" $prog $registry | sort -u)

                    if test (count $group_skills) -eq 0
                        echo "$c_magenta✗$c_reset Group '$name' not found. Run 'claude-skill list --group' to see available groups."
                        continue
                    end

                    set -l count 0
                    for sname in $group_skills
                        if test -L "$skills_target/$sname"
                            command rm "$skills_target/$sname"
                            set count (math $count + 1)
                        end
                    end
                    echo "$c_green✓$c_reset Removed $count skills from group '$name'"
                end
            else
                for name in $names
                    if not test -L "$skills_target/$name"
                        echo "$c_yellow⚠$c_reset Skill '$name' is not linked in this project."
                        continue
                    end
                    command rm "$skills_target/$name"
                    echo "$c_green✓$c_reset Removed '$name' from $skills_target/"
                end
            end

        case update
            if test (count $names) -eq 0
                _claude_skill_update $registry "$DOTFILES_DIR/roles/ai/files/claude" "" sync
            else
                for name in $names
                    _claude_skill_update $registry "$DOTFILES_DIR/roles/ai/files/claude" "$name" sync
                end
            end

        case outdated
            if test (count $names) -eq 0
                _claude_skill_update $registry "$DOTFILES_DIR/roles/ai/files/claude" "" check
            else
                for name in $names
                    _claude_skill_update $registry "$DOTFILES_DIR/roles/ai/files/claude" "$name" check
                end
            end

        case '*'
            echo "Usage: claude-skill <list|add|remove|update|outdated> [--group] [name]..."
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
    set -l c_blue (set_color blue)
    set -l c_magenta (set_color magenta)
    set -l c_cyan (set_color cyan)
    set -l c_dim (set_color brblack)
    set -l c_bold (set_color --bold)
    set -l c_reset (set_color normal)

    set -l exclude_args --exclude=.git --exclude=.github --exclude=node_modules

    if not command -q jq
        echo "$c_magenta✗$c_reset Error: jq is required. Install with: brew install jq"
        return 1
    end

    if not test -f "$registry"
        echo "$c_magenta✗$c_reset Error: Registry not found at $registry"
        return 1
    end

    set -l repos
    if test -n "$target_skill"
        set -l prog (_claude_skill_jqlib)' .repos | to_entries[] | .key as $r | select(any(.value.skills[]; dn($r) == $skill)) | $r'
        set repos (jq -r --arg skill "$target_skill" $prog $registry)

        if test -z "$repos"
            set -l is_local (jq -r --arg skill "$target_skill" '
                [.local_skills[]? | select(.name == $skill)] | length
            ' $registry)
            if test "$is_local" != "0"
                echo "$c_yellow⚠$c_reset '$target_skill' is a local skill; no upstream to sync."
                return 0
            end
            echo "$c_magenta✗$c_reset Skill '$target_skill' not found in registry."
            echo "Tracked skills:"
            set -l prog (_claude_skill_jqlib)' allskills | map(select(.repo != null)) | .[].name'
            jq -r $prog $registry | sort | sed 's/^/  /'
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
            set -l prog (_claude_skill_jqlib)' .repos[$r].skills[] | select(dn($r) == $skill) | "\(.upstream_path)|\(dn($r))"'
            set skill_entries (jq -r --arg r "$repo" --arg skill "$target_skill" $prog $registry)
        else
            set -l prog (_claude_skill_jqlib)' .repos[$r].skills[] | "\(.upstream_path)|\(dn($r))"'
            set skill_entries (jq -r --arg r "$repo" $prog $registry)
        end

        echo "$c_cyan── $repo ($branch) ──$c_reset"

        mkdir -p "$clone_dir"
        curl -sfL "https://github.com/$repo/archive/$branch.tar.gz" | tar -xz -C "$clone_dir" --strip-components=1
        if test $pipestatus[1] -ne 0 -o $pipestatus[2] -ne 0
            echo "  $c_magenta✗ FAILED to fetch$c_reset"
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
                echo "  $c_magenta✗$c_reset $skill_name: upstream path '$upstream_path' not found"
                set failed (math $failed + 1)
                continue
            end

            set -l last_synced (jq -r --arg repo "$repo" --arg up "$upstream_path" '
                .repos[$repo].skills[] | select(.upstream_path == $up) | .updated_at // "never"
            ' $registry | string sub --length 10)

            if not test -d "$dst"
                if test "$mode" = check
                    echo "  $c_yellow↓$c_reset $skill_name: "$c_yellow"not downloaded"$c_reset
                    set missing (math $missing + 1)
                else
                    mkdir -p (dirname "$dst")
                    rsync -a $exclude_args "$src/" "$dst/"
                    echo "  $c_blue✓$c_reset $skill_name: "$c_blue"installed (new)"$c_reset
                    set updated (math $updated + 1)
                    _claude_skill_stamp $registry $repo $upstream_path skills
                end
                continue
            end

            set -l diff_output (diff -rq $exclude_args "$src" "$dst" 2>/dev/null)
            if test -z "$diff_output"
                echo "  $c_green✓$c_reset $skill_name: "$c_green"up to date"$c_reset" $c_dim(last synced $last_synced)$c_reset"
                set skipped (math $skipped + 1)
                if test "$mode" = sync
                    _claude_skill_stamp $registry $repo $upstream_path skills
                end
                continue
            end

            if test "$mode" = check
                echo "  $c_red⟳$c_reset $skill_name: "$c_red"behind"$c_reset" $c_dim(last synced $last_synced)$c_reset"
                set updated (math $updated + 1)
            else
                command rm -rf "$dst"
                rsync -a $exclude_args "$src/" "$dst/"
                set updated (math $updated + 1)
                echo "  $c_blue⟳$c_reset $skill_name: $c_blue✓ synced.$c_reset"
                _claude_skill_stamp $registry $repo $upstream_path skills
            end
        end

        echo ""
    end

    rm -rf "$tmpdir"

    if test "$mode" = check
        printf '%sDone:%s %s%d%s behind, %s%d%s up-to-date, %s%d%s not downloaded, %s%d%s failed\n' \
            $c_bold $c_reset \
            $c_red $updated $c_reset \
            $c_green $skipped $c_reset \
            $c_yellow $missing $c_reset \
            $c_magenta $failed $c_reset
    else
        printf '%sDone:%s %s%d%s updated, %s%d%s up-to-date, %s%d%s failed\n' \
            $c_bold $c_reset \
            $c_blue $updated $c_reset \
            $c_green $skipped $c_reset \
            $c_magenta $failed $c_reset
    end
end

function _claude_skill_jqlib --description "jq prelude: dn() derives a repos skill's directory name from upstream_path; allskills augments every entry with it (local skills keep their own name); visibleskills drops dependency_only entries for browsing"
    echo 'def dn($r): (.upstream_path // "") as $p | if ($p == "" or $p == "." or $p == "/") then ($r | split("/")[1]) else ($p | sub("/+$";"") | split("/") | last) end; def allskills: [ (.repos | to_entries[] | .key as $r | .value.skills[] | . + {name: dn($r), repo: $r}), (.local_skills[]? | . + {repo: null}) ]; def visibleskills: allskills | map(select((.dependency_only // false) | not));'
end

function _claude_skill_check_collisions --description "Fail if two skills resolve to the same directory name"
    set -l registry $argv[1]
    set -l prog (_claude_skill_jqlib)' [allskills | .[].name] | group_by(.) | map(select(length > 1) | .[0]) | .[]'
    set -l dups (jq -r $prog $registry)
    if test -n "$dups"
        echo (set_color magenta)"✗ Skill name collision(s) detected:"(set_color normal)
        for d in $dups
            echo "  $d"
        end
        echo "  Two skills derive to the same directory name (basename of upstream_path, or repo name for root skills)."
        echo "  Resolve in $registry before continuing."
        return 1
    end
    return 0
end

function _claude_skill_stamp --description "Record updated_at on a tracked skill entry (matched by upstream_path)"
    set -l registry $argv[1]
    set -l repo $argv[2]
    set -l up $argv[3]
    set -l array_key $argv[4]

    set -l now (date -u +%Y-%m-%dT%H:%M:%SZ)
    set -l tmp (mktemp)
    if jq --arg repo "$repo" --arg up "$up" --arg ts "$now" --arg key "$array_key" '
        .repos[$repo][$key] |= map(if .upstream_path == $up then .updated_at = $ts else . end)
    ' $registry > $tmp
        mv $tmp $registry
    else
        rm -f $tmp
    end
end

function _claude_skill_is_hidden --description "Exit 0 if the named skill is marked dependency_only in the registry"
    set -l registry $argv[1]
    set -l name $argv[2]
    set -l prog (_claude_skill_jqlib)' [ allskills | .[] | select(.name == $n and (.dependency_only // false)) ] | length'
    test (jq -r --arg n "$name" $prog $registry) != 0
end

function _claude_skill_direct_deps --description "Print a skill's directly declared dependency names, comma-joined"
    set -l registry $argv[1]
    set -l name $argv[2]
    set -l prog (_claude_skill_jqlib)' [ allskills | .[] | select(.name == $n) | .dependencies // [] | .[] ] | unique | join(", ")'
    jq -r --arg n "$name" $prog $registry
end

function _claude_skill_groups --description "Print a skill's registry groups, comma-joined"
    set -l registry $argv[1]
    set -l name $argv[2]
    set -l prog (_claude_skill_jqlib)' [ allskills | .[] | select(.name == $n) | .groups // [] | .[] ] | unique | join(", ")'
    jq -r --arg n "$name" $prog $registry
end

function _claude_skill_deps --description "Print the transitive dependency skill names for a given skill"
    set -l registry $argv[1]
    set -l root $argv[2]

    set -l result
    set -l queue $root
    set -l visited $root

    while test (count $queue) -gt 0
        set -l current $queue[1]
        set -e queue[1]

        set -l prog (_claude_skill_jqlib)' [ allskills | .[] | select(.name == $n) | .dependencies // [] | .[] ] | unique | .[]'
        set -l deps (jq -r --arg n "$current" $prog $registry)

        for d in $deps
            if not contains -- $d $visited
                set -a visited $d
                set -a result $d
                set -a queue $d
            end
        end
    end

    for r in $result
        echo $r
    end
end

function _claude_skill_ensure_linked --description "Ensure a skill is on disk (download if tracked) and symlinked into the project"
    set -l skills_source $argv[1]
    set -l skills_target $argv[2]
    set -l registry $argv[3]
    set -l base_dir $argv[4]
    set -l name $argv[5]
    set -l label $argv[6]

    set -l c_green (set_color green)
    set -l c_magenta (set_color magenta)
    set -l c_cyan (set_color cyan)
    set -l c_dim (set_color brblack)
    set -l c_reset (set_color normal)

    if not test -d "$skills_source/$name"
        set -l prog (_claude_skill_jqlib)' [ allskills | .[] | select(.repo != null and .name == $n) | .name ] | .[0] // empty'
        set -l in_registry (jq -r --arg n "$name" $prog $registry)
        if test -n "$in_registry"
            echo "$c_cyan↓$c_reset Skill '$name' not downloaded. Pulling from registry..."
            _claude_skill_update $registry $base_dir $name
            if not test -d "$skills_source/$name"
                echo "$c_magenta✗$c_reset Failed to download '$name'."
                return 1
            end
        else
            echo "$c_magenta✗$c_reset Skill '$name' not found. Run 'claude-skill list' to see available skills."
            return 1
        end
    end

    mkdir -p $skills_target
    ln -sfn "$skills_source/$name" "$skills_target/$name"
    if test -n "$label"
        echo "$c_green✓$c_reset Linked '$name' $c_dim($label)$c_reset into $skills_target/"
    else
        echo "$c_green✓$c_reset Linked '$name' into $skills_target/"
    end
    return 0
end
