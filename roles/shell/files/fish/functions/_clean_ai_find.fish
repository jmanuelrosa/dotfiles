function _clean_ai_find --description "List named project directories under a root without entering matches or dependency trees"
  set -l name $argv[1]
  set -l root $argv[2]

  set -l fd_args
  for pattern in $argv[3..-1]
    set -a fd_args -E $pattern
  end

  set -l pattern '^'(string escape --style=regex -- "$name")'$'
  command fd --type d --type l --hidden --no-ignore --absolute-path --prune \
    $fd_args "$pattern" "$root" 2>/dev/null | string trim -r -c / | command sort
end
