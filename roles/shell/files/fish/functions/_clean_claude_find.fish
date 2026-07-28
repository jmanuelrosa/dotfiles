function _clean_claude_find --description "List .claude directories under a root; remaining args are directory names to skip"
  set -l root $argv[1]

  set -l fd_args
  for pattern in $argv[2..-1]
    set -a fd_args -E $pattern
  end

  # --prune stops the walk at each hit, so a .claude nested inside another never
  # doubles up. --type l catches a symlinked .claude, which rm then unlinks rather
  # than following into its target.
  command fd --type d --type l --hidden --no-ignore --absolute-path --prune \
    $fd_args '^\.claude$' "$root" 2>/dev/null | string trim -r -c / | command sort
end
