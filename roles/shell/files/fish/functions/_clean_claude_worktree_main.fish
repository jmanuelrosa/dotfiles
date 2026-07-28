function _clean_claude_worktree_main --description "Print the main repo root when a path is a linked git worktree, print nothing otherwise"
  set -l gitdir (command git -C "$argv[1]" rev-parse --git-dir 2>/dev/null)
  set -l common (command git -C "$argv[1]" rev-parse --git-common-dir 2>/dev/null)

  test -n "$gitdir" -a -n "$common"; or return 1
  test "$gitdir" = "$common"; and return 1

  # A linked worktree's --git-dir is <main>/.git/worktrees/<name> while its
  # --git-common-dir is <main>/.git, so the main checkout is the latter's parent.
  path dirname -- (path resolve -- "$common")
end
