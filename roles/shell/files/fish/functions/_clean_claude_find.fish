function _clean_claude_find --description "List .claude directories under a root; remaining args are directory names to skip"
  _clean_ai_find .claude $argv
end
