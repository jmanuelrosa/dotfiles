function claude-agent --description "Manage Claude Code agents for the current project"
    set -l agents_source "$DOTFILES_DIR/roles/ai/files/claude/agents"
    set -l agents_target ".claude/agents"
    set -l registry "$DOTFILES_DIR/roles/ai/files/claude/agent-registry.json"

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
        echo "Usage: claude-agent <list|add|remove|update|outdated> [--group] [name]..."
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

    switch $cmd
        case list
            if test "$use_group" = true
                echo $c_bold"Available groups:"$c_reset

                set -l groups (jq -r '
                    [.repos[].agents[].groups[]?, .local_agents[]?.groups[]?]
                    | unique | .[]
                ' $registry)

                for g in $groups
                    echo "  $c_cyan$g:$c_reset"
                    set -l names (jq -r --arg g "$g" '
                        [
                            (.repos[].agents[] | select(.groups | index($g))),
                            (.local_agents[]    | select(.groups | index($g)))
                        ] | .[] | .name
                    ' $registry | sort -u)
                    for aname in $names
                        set -l deps (_claude_agent_direct_deps $registry $aname)
                        set -l dep_suffix ""
                        test -n "$deps"; and set dep_suffix " $c_dim(needs: $deps)$c_reset"
                        if test -L "$agents_target/$aname.md"
                            echo "    $c_green✓$c_reset $aname $c_green(linked)$c_reset$dep_suffix"
                        else if test -f "$agents_source/$aname.md"
                            echo "    $c_dim·$c_reset $aname$dep_suffix"
                        else
                            echo "    $c_dim↓ $aname (not downloaded)$c_reset$dep_suffix"
                        end
                    end
                end
            else
                echo $c_bold"Available agents:"$c_reset
                set -l seen

                if test -d "$agents_source"
                    for agent in $agents_source/*.md
                        if not test -f "$agent"
                            continue
                        end
                        set -l aname (basename $agent .md)
                        set -a seen $aname
                        set -l deps (_claude_agent_direct_deps $registry $aname)
                        set -l dep_suffix ""
                        test -n "$deps"; and set dep_suffix " $c_dim(needs: $deps)$c_reset"
                        if test -L "$agents_target/$aname.md"
                            echo "  $c_green✓$c_reset $aname $c_green(linked)$c_reset$dep_suffix"
                        else
                            echo "  $c_dim·$c_reset $aname$dep_suffix"
                        end
                    end
                end

                set -l reg_names (jq -r '.repos[].agents[].name' $registry)
                for aname in $reg_names
                    if not contains -- $aname $seen
                        set -l deps (_claude_agent_direct_deps $registry $aname)
                        set -l dep_suffix ""
                        test -n "$deps"; and set dep_suffix " $c_dim(needs: $deps)$c_reset"
                        echo "  $c_dim↓ $aname (not downloaded)$c_reset$dep_suffix"
                    end
                end
            end

        case add
            if test (count $names) -eq 0
                echo "Usage: claude-agent add [--group] <name>..."
                return 1
            end
            if test "$use_group" = true
                for name in $names
                    set -l group_agents (jq -r --arg g "$name" '
                        [
                            (.repos[].agents[] | select(.groups | index($g))),
                            (.local_agents[]    | select(.groups | index($g)))
                        ] | .[] | .name
                    ' $registry | sort -u)

                    if test (count $group_agents) -eq 0
                        echo "$c_magenta✗$c_reset Group '$name' not found. Run 'claude-agent list --group' to see available groups."
                        continue
                    end

                    set -l tracked_names (jq -r '.repos[].agents[].name' $registry)

                    for aname in $group_agents
                        if not test -f "$agents_source/$aname.md"
                            if contains -- $aname $tracked_names
                                echo "$c_cyan↓$c_reset Downloading '$aname' from registry..."
                                _claude_agent_update $registry "$agents_source" $aname
                            else
                                echo "$c_magenta✗$c_reset Local agent '$aname' missing on disk; cannot install."
                                continue
                            end
                        end
                    end

                    mkdir -p $agents_target
                    set -l count 0
                    for aname in $group_agents
                        if test -f "$agents_source/$aname.md"
                            ln -sfn "$agents_source/$aname.md" "$agents_target/$aname.md"
                            set count (math $count + 1)
                            _claude_agent_install_skill_deps $registry $aname
                        end
                    end
                    echo "$c_green✓$c_reset Linked $count agents from group '$name' into $agents_target/"
                end
            else
                for name in $names
                    if not test -f "$agents_source/$name.md"
                        set -l in_registry (jq -r --arg n "$name" '
                            [.repos[].agents[] | select(.name == $n) | .name] | .[0] // empty
                        ' $registry)
                        set -l in_local (jq -r --arg n "$name" '
                            [.local_agents[]? | select(.name == $n) | .name] | .[0] // empty
                        ' $registry)
                        if test -n "$in_local"
                            echo "$c_magenta✗$c_reset Local agent '$name' missing on disk; cannot install."
                            continue
                        else if test -n "$in_registry"
                            echo "$c_cyan↓$c_reset Agent '$name' not downloaded. Pulling from registry..."
                            _claude_agent_update $registry "$agents_source" $name
                            if not test -f "$agents_source/$name.md"
                                echo "$c_magenta✗$c_reset Failed to download '$name'."
                                continue
                            end
                        else
                            echo "$c_magenta✗$c_reset Agent '$name' not found. Run 'claude-agent list' to see available agents."
                            continue
                        end
                    end
                    mkdir -p $agents_target
                    ln -sfn "$agents_source/$name.md" "$agents_target/$name.md"
                    echo "$c_green✓$c_reset Linked '$name' into $agents_target/"
                    _claude_agent_install_skill_deps $registry $name
                end
            end

        case remove
            if test (count $names) -eq 0
                echo "Usage: claude-agent remove [--group] <name>..."
                return 1
            end
            if test "$use_group" = true
                for name in $names
                    set -l group_agents (jq -r --arg g "$name" '
                        [
                            (.repos[].agents[] | select(.groups | index($g))),
                            (.local_agents[]    | select(.groups | index($g)))
                        ] | .[] | .name
                    ' $registry | sort -u)

                    if test (count $group_agents) -eq 0
                        echo "$c_magenta✗$c_reset Group '$name' not found. Run 'claude-agent list --group' to see available groups."
                        continue
                    end

                    set -l count 0
                    for aname in $group_agents
                        if test -L "$agents_target/$aname.md"
                            command rm "$agents_target/$aname.md"
                            set count (math $count + 1)
                        end
                    end
                    echo "$c_green✓$c_reset Removed $count agents from group '$name'"
                end
            else
                for name in $names
                    if not test -L "$agents_target/$name.md"
                        echo "$c_yellow⚠$c_reset Agent '$name' is not linked in this project."
                        continue
                    end
                    command rm "$agents_target/$name.md"
                    echo "$c_green✓$c_reset Removed '$name' from $agents_target/"
                end
            end

        case update
            if test (count $names) -eq 0
                _claude_agent_update $registry "$agents_source" "" sync
            else
                for name in $names
                    _claude_agent_update $registry "$agents_source" "$name" sync
                end
            end

        case outdated
            if test (count $names) -eq 0
                _claude_agent_update $registry "$agents_source" "" check
            else
                for name in $names
                    _claude_agent_update $registry "$agents_source" "$name" check
                end
            end

        case '*'
            echo "Usage: claude-agent <list|add|remove|update|outdated> [--group] [name]..."
            return 1
    end
end

function _claude_agent_update --description "Sync (or check) agents against upstream GitHub repos"
    set -l registry $argv[1]
    set -l agents_dir $argv[2]
    set -l target_agent $argv[3]
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

    if not command -q jq
        echo "$c_magenta✗$c_reset Error: jq is required. Install with: brew install jq"
        return 1
    end

    if not test -f "$registry"
        echo "$c_magenta✗$c_reset Error: Registry not found at $registry"
        return 1
    end

    set -l repos
    if test -n "$target_agent"
        set repos (jq -r --arg agent "$target_agent" '
            .repos | to_entries[] |
            select(.value.agents[] | .name == $agent) |
            .key
        ' $registry)

        if test -z "$repos"
            set -l is_local (jq -r --arg agent "$target_agent" '
                [.local_agents[]? | select(.name == $agent)] | length
            ' $registry)
            if test "$is_local" != "0"
                echo "$c_yellow⚠$c_reset '$target_agent' is a local agent; no upstream to sync."
                return 0
            end
            echo "$c_magenta✗$c_reset Agent '$target_agent' not found in registry."
            echo "Tracked agents:"
            jq -r '.repos[].agents[].name' $registry | sort | sed 's/^/  /'
            return 1
        end
    else
        set repos (jq -r '.repos | keys[]' $registry)
    end

    if test (count $repos) -eq 0
        echo "$c_dim·$c_reset No repos in registry. Nothing to update."
        return 0
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

        set -l agent_entries
        if test -n "$target_agent"
            set agent_entries (jq -r --arg r "$repo" --arg agent "$target_agent" '
                .repos[$r].agents[] | select(.name == $agent) |
                "\(.upstream_path)|\(.name)"
            ' $registry)
        else
            set agent_entries (jq -r --arg r "$repo" '
                .repos[$r].agents[] |
                "\(.upstream_path)|\(.name)"
            ' $registry)
        end

        echo "$c_cyan── $repo ($branch) ──$c_reset"

        mkdir -p "$clone_dir"
        curl -sfL "https://github.com/$repo/archive/$branch.tar.gz" | tar -xz -C "$clone_dir" --strip-components=1
        if test $pipestatus[1] -ne 0 -o $pipestatus[2] -ne 0
            echo "  $c_magenta✗ FAILED to fetch$c_reset"
            set failed (math $failed + 1)
            continue
        end

        for entry in $agent_entries
            set -l parts (string split "|" $entry)
            set -l upstream_path $parts[1]
            set -l name $parts[2]

            set -l src "$clone_dir/$upstream_path"
            set -l dst "$agents_dir/$name.md"

            if not test -f "$src"
                echo "  $c_magenta✗$c_reset $name: upstream path '$upstream_path' not found"
                set failed (math $failed + 1)
                continue
            end

            set -l last_synced (jq -r --arg repo "$repo" --arg name "$name" '
                .repos[$repo].agents[] | select(.name == $name) | .updated_at // "never"
            ' $registry | string sub --length 10)

            if not test -f "$dst"
                if test "$mode" = check
                    echo "  $c_yellow↓$c_reset $name: "$c_yellow"not downloaded"$c_reset
                    set missing (math $missing + 1)
                else
                    mkdir -p (dirname "$dst")
                    cp "$src" "$dst"
                    echo "  $c_blue✓$c_reset $name: "$c_blue"installed (new)"$c_reset
                    set updated (math $updated + 1)
                    _claude_registry_stamp $registry $repo $name agents
                end
                continue
            end

            diff -u "$dst" "$src" >/dev/null 2>&1
            if test $status -eq 0
                echo "  $c_green✓$c_reset $name: "$c_green"up to date"$c_reset" $c_dim(last synced $last_synced)$c_reset"
                set skipped (math $skipped + 1)
                if test "$mode" = sync
                    _claude_registry_stamp $registry $repo $name agents
                end
                continue
            end

            if test "$mode" = check
                echo "  $c_red⟳$c_reset $name: "$c_red"behind"$c_reset" $c_dim(last synced $last_synced)$c_reset"
                set updated (math $updated + 1)
            else
                echo "  $c_blue⟳$c_reset $name: "$c_blue"updated"$c_reset
                cp "$src" "$dst"
                set updated (math $updated + 1)
                _claude_registry_stamp $registry $repo $name agents
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

function _claude_agent_direct_deps --description "Print an agent's declared skill dependency names, comma-joined"
    set -l registry $argv[1]
    set -l name $argv[2]
    jq -r --arg n "$name" '
        [ (.repos[]?.agents[]?, .local_agents[]?) | select(.name == $n) | .dependencies // [] | .[] ] | unique | join(", ")
    ' $registry
end

function _claude_agent_skill_deps --description "Print an agent's declared skill dependency names, one per line"
    set -l registry $argv[1]
    set -l name $argv[2]
    jq -r --arg n "$name" '
        [ (.repos[]?.agents[]?, .local_agents[]?) | select(.name == $n) | .dependencies // [] | .[] ] | unique | .[]
    ' $registry
end

# Reuses claude-skill's internal helpers instead of `claude-skill add` so a
# dependency_only skill (e.g. domain-modeling) installs without tripping the
# direct-add refusal — resolution paths are meant to bypass it.
function _claude_agent_install_skill_deps --description "Install the skills an agent declares as dependencies into .claude/skills"
    set -l agent_registry $argv[1]
    set -l agent_name $argv[2]

    set -l deps (_claude_agent_skill_deps $agent_registry $agent_name)
    test (count $deps) -eq 0; and return 0

    if not functions -q _claude_skill_ensure_linked
        source (dirname (status --current-filename))/claude-skill.fish
    end

    set -l base_dir "$DOTFILES_DIR/roles/ai/files/claude"
    set -l skills_source "$base_dir/skills"
    set -l skills_target ".claude/skills"
    set -l skill_registry "$base_dir/skill-registry.json"

    for d in $deps
        for sub in (_claude_skill_deps $skill_registry $d)
            _claude_skill_ensure_linked $skills_source $skills_target $skill_registry $base_dir $sub "required by $d"
        end
        _claude_skill_ensure_linked $skills_source $skills_target $skill_registry $base_dir $d "required by agent $agent_name"
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
