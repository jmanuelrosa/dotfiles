function _clean_claude_tracked --description "True when a path is committed to the git repo that contains it"
  command git -C (path dirname -- $argv[1]) ls-files --error-unmatch -- (path basename -- $argv[1]) >/dev/null 2>&1
end
