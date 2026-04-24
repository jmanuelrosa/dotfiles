function claude-agent --description "Manage Claude Code agents for the current project"
    set -l agents_source "$DOTFILES_DIR/roles/ai/files/claude/agents"
    set -l agents_target ".claude/agents"
    set -l registry "$DOTFILES_DIR/roles/ai/files/claude/agent-registry.json"

    set -l c_green (set_color green)
    set -l c_yellow (set_color yellow)
    set -l c_red (set_color red)
    set -l c_cyan (set_color cyan)
    set -l c_dim (set_color brblack)
    set -l c_bold (set_color --bold)
    set -l c_reset (set_color normal)

    if test (count $argv) -lt 1
        echo "Usage: claude:agent <list|add|remove|update> [name]"
        return 1
    end

    set -l cmd $argv[1]
    set -l name $argv[2]

    switch $cmd
        case list
            echo $c_bold"Available agents:"$c_reset
            set -l seen

            if test -d "$agents_source"
                for agent in $agents_source/*.md
                    if not test -f "$agent"
                        continue
                    end
                    set -l aname (basename $agent .md)
                    set -a seen $aname
                    if test -L "$agents_target/$aname.md"
                        echo "  $c_green✓$c_reset $aname $c_green(linked)$c_reset"
                    else
                        echo "  $c_dim·$c_reset $aname"
                    end
                end
            end

            if command -q jq; and test -f "$registry"
                set -l reg_names (jq -r '.repos[].agents[].name' $registry)
                for aname in $reg_names
                    if not contains -- $aname $seen
                        echo "  $c_dim↓ $aname (not downloaded)$c_reset"
                    end
                end
            end

        case add
            if test -z "$name"
                echo "Usage: claude:agent add <name>"
                return 1
            end
            if not test -f "$agents_source/$name.md"
                set -l in_registry false
                if command -q jq; and test -f "$registry"
                    set -l match (jq -r --arg n "$name" '
                        .repos[].agents[] | select(.name == $n) | .name
                    ' $registry)
                    if test -n "$match"
                        set in_registry true
                    end
                end

                if test "$in_registry" = false
                    echo "$c_red✗$c_reset Agent '$name' not found. Run 'claude:agent list' to see available agents."
                    return 1
                end

                echo "$c_cyan↓$c_reset Agent '$name' not downloaded. Pulling from registry..."
                _claude_agent_update $registry "$agents_source" $name

                if not test -f "$agents_source/$name.md"
                    echo "$c_red✗$c_reset Failed to download '$name'."
                    return 1
                end
            end
            mkdir -p $agents_target
            ln -sf "$agents_source/$name.md" "$agents_target/$name.md"
            echo "$c_green✓$c_reset Linked '$name' into $agents_target/"

        case remove
            if test -z "$name"
                echo "Usage: claude:agent remove <name>"
                return 1
            end
            if not test -L "$agents_target/$name.md"
                echo "$c_yellow⚠$c_reset Agent '$name' is not linked in this project."
                return 1
            end
            rm "$agents_target/$name.md"
            echo "$c_green✓$c_reset Removed '$name' from $agents_target/"

        case update
            _claude_agent_update $registry "$DOTFILES_DIR/roles/ai/files/claude/agents" $name

        case '*'
            echo "Usage: claude:agent <list|add|remove|update> [name]"
            return 1
    end
end

function _claude_agent_update --description "Sync agents from upstream GitHub repos"
    set -l registry $argv[1]
    set -l agents_dir $argv[2]
    set -l target_agent $argv[3]

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
    if test -n "$target_agent"
        set repos (jq -r --arg agent "$target_agent" '
            .repos | to_entries[] |
            select(.value.agents[] | .name == $agent) |
            .key
        ' $registry)

        if test -z "$repos"
            echo "$c_red✗$c_reset Agent '$target_agent' not found in registry."
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
    set -l n_repos (count $repos)

    echo $c_bold"Syncing from $n_repos repo(s)..."$c_reset
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
            echo "  $c_red✗ FAILED to fetch$c_reset"
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
                echo "  $c_red✗$c_reset $name: upstream path '$upstream_path' not found"
                set failed (math $failed + 1)
                continue
            end

            if not test -f "$dst"
                mkdir -p (dirname "$dst")
                cp "$src" "$dst"
                echo "  $c_green✓$c_reset $name: "$c_green"installed (new)"$c_reset
                set updated (math $updated + 1)
                continue
            end

            diff -u "$dst" "$src" >/dev/null 2>&1
            if test $status -eq 0
                echo "  $c_dim·$c_reset $name: "$c_dim"up to date"$c_reset
                set skipped (math $skipped + 1)
                continue
            end

            echo "  $c_yellow⟳$c_reset $name: "$c_yellow"updated"$c_reset
            cp "$src" "$dst"
            set updated (math $updated + 1)
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
