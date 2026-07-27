function _clean_claude_pretty --description "Shorten a path for display by collapsing \$HOME to ~"
  string replace -r '^'(string escape --style=regex -- $HOME)'(/|$)' '~$1' -- $argv[1]
end
