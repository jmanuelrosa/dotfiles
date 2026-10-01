function _clean_pi_sessions --description "List Pi session files whose recorded working directory is inside a tree"
  set -l root $argv[1]
  set -l session_dir $argv[2]
  test -d "$session_dir"; or return 0

  for file in (command fd --type f --hidden --no-ignore --absolute-path --extension jsonl . "$session_dir" 2>/dev/null)
    set -l cwd (command head -n 1 "$file" | command jq -er 'select(.type == "session") | .cwd | strings' 2>/dev/null)
    test -n "$cwd"; or continue
    set -l resolved (path resolve -- "$cwd" 2>/dev/null)
    if test "$root" = /; or string match -q --regex '^'(string escape --style=regex -- "$root")'(/|$)' -- "$resolved"
      echo "$file"
    end
  end
end
