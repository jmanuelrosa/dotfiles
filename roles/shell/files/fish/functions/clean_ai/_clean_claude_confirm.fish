function _clean_claude_confirm --description "Prompt before destroying things; pass a word to demand that exact word instead of y/N"
  read -l -P "$argv[1] " reply

  if set -q argv[2]
    test "$reply" = "$argv[2]"; and return 0
  else
    string match -qir '^y(es)?$' -- $reply; and return 0
  end

  _ui warn "Aborted."
  return 1
end
