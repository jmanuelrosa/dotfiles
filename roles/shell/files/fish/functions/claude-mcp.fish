function claude-mcp --description "Manage Claude Code MCP servers for the current project"
    set -l mcp_source "$DOTFILES_DIR/roles/ai/files/claude/mcp-servers"
    set -l mcp_target ".mcp.json"

    if not command -q jq
        echo "Error: jq is required. Install it with: brew install jq"
        return 1
    end

    if test (count $argv) -lt 1
        echo "Usage: claude:mcp <list|add|remove> [server-name]"
        return 1
    end

    set -l cmd $argv[1]
    set -l name $argv[2]

    switch $cmd
        case list
            echo "Available MCP servers:"
            for server in $mcp_source/*.json
                set -l sname (basename $server .json)
                if test -f $mcp_target; and jq -e ".mcpServers.\"$sname\"" $mcp_target >/dev/null 2>&1
                    echo "  $sname (installed)"
                else
                    echo "  $sname"
                end
            end

        case add
            if test -z "$name"
                echo "Usage: claude:mcp add <server-name>"
                return 1
            end
            if not test -f "$mcp_source/$name.json"
                echo "Server '$name' not found. Run 'claude:mcp list' to see available servers."
                return 1
            end

            set -l config (cat "$mcp_source/$name.json")

            if test -f $mcp_target
                set -l tmp (mktemp)
                jq --arg name "$name" --argjson config "$config" \
                    '.mcpServers[$name] = $config' $mcp_target >$tmp
                and mv $tmp $mcp_target
            else
                jq -n --arg name "$name" --argjson config "$config" \
                    '{mcpServers: {($name): $config}}' >$mcp_target
            end
            echo "Added '$name' to $mcp_target"

        case remove
            if test -z "$name"
                echo "Usage: claude:mcp remove <server-name>"
                return 1
            end
            if not test -f $mcp_target
                echo "No .mcp.json found in this project."
                return 1
            end
            if not jq -e ".mcpServers.\"$name\"" $mcp_target >/dev/null 2>&1
                echo "Server '$name' is not installed in this project."
                return 1
            end

            set -l tmp (mktemp)
            jq --arg name "$name" 'del(.mcpServers[$name])' $mcp_target >$tmp
            and mv $tmp $mcp_target

            # Clean up if mcpServers is now empty
            if test (jq '.mcpServers | length' $mcp_target) -eq 0
                rm $mcp_target
                echo "Removed '$name' and deleted empty $mcp_target"
            else
                echo "Removed '$name' from $mcp_target"
            end

        case '*'
            echo "Usage: claude:mcp <list|add|remove> [server-name]"
            return 1
    end
end
