function _clean_claude_purge_state --description "Purge Claude Code project state for a tree, or for every project in purge mode"
  set -l mode $argv[1]
  set -l flag $argv[2]
  set -l root $argv[3]
  set -l worktree_config $argv[4]

  if test "$mode" = purge
    command claude project purge --all $flag
    return $status
  end
  test "$mode" = project; or return 0

  for project in (_clean_claude_state_roots "$root")
    # Passing a worktree path deletes the MAIN repo's ~/.claude.json entry (trust,
    # history, MCP servers), and the CLI cannot purge transcripts without it, so a
    # worktree is skipped unless asked for explicitly.
    set -l main (_clean_claude_worktree_main "$project")
    if test -n "$main"; and test "$worktree_config" != 1
      _ui -i 2 warn (_ui path "$project")" is a linked worktree of "(_ui path "$main")"."
      _ui -i 4 note "Purging it would delete that main repo's config entry, so it is skipped."
      _ui -i 4 note "Run 'clean_claude project --worktree-config' or 'claude project purge "(_ui path "$main")"' to include it."
      continue
    end

    # Never call the CLI without a path: with no argument it blocks on an interactive
    # project picker forever, even with stdin closed.
    test -n "$project"; or continue
    command claude project purge $flag "$project"
  end
end
