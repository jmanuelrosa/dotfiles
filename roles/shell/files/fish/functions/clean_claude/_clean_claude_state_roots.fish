function _clean_claude_state_roots --description "Paths to hand 'claude project purge': the tree root plus every ~/.claude.json project at or below it"
  set -l root (path resolve -- "$argv[1]")

  # The root alone covers transcripts, file-history and history.jsonl for the whole
  # tree, because the CLI prefix-matches those at path-segment boundaries. Config
  # entries in ~/.claude.json are matched exactly, so each one needs its own call or
  # a subproject keeps its trust and MCP servers.
  set -l roots "$argv[1]"

  set -l config "$HOME/.claude.json"
  if command -q jq; and test -f "$config"
    for key in (command jq -r '.projects // {} | keys[]' "$config" 2>/dev/null)
      set -l resolved (path resolve -- "$key")
      test "$resolved" = "$root"; or string match -q "$root/*" -- "$resolved"; or continue
      # The stored key is what the CLI compares against, so pass it through verbatim.
      contains -- "$key" $roots; or set -a roots "$key"
    end
  end

  printf '%s\n' $roots
end
