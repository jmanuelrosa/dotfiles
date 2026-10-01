function clean_pi --description "Remove Pi project directories and sessions, or explicitly purge global Pi configuration"
  argparse -n clean_pi h/help n/dry-run w/worktree-config 'e/exclude=+' 'i/include=+' -- $argv
  or return 1

  if set -q _flag_help
    _clean_pi_usage
    return 0
  end

  set -l mode project
  set -q argv[1]; and set mode $argv[1]
  if not contains -- $mode project skills agents purge; or test (count $argv) -gt 2
    _clean_pi_usage
    return 1
  end

  set -l root (pwd)
  test $mode = purge; and set root $HOME
  set -q argv[2]; and set root (path resolve -- "$argv[2]")
  if not test -d "$root"
    _ui err "Not a directory: "(_ui path "$root")
    return 1
  end
  if not command -q fd
    _ui err "clean_pi needs fd (brew install fd)."
    return 1
  end
  if test $mode = project; and not command -q jq
    _ui err "clean_pi project needs jq to select sessions by their recorded working directory."
    return 1
  end

  set -l excludes (_clean_claude_excludes $_flag_exclude)
  if set -q _flag_include[1]
    set -l kept
    for name in $excludes
      contains -- $name $_flag_include; or set -a kept $name
    end
    set excludes $kept
  end

  set -l agent_dir "$HOME/.pi/agent"
  set -q PI_CODING_AGENT_DIR[1]; and set agent_dir (path resolve -- "$PI_CODING_AGENT_DIR")
  set -l global_pi "$HOME/.pi"
  set -l global_agents "$HOME/.agents"
  set -l project_dirs
  set -l global_dirs
  for name in .pi .agents
    for dir in (_clean_ai_find $name "$root" $excludes)
      if test "$dir" = "$global_pi"; or test "$dir" = "$global_agents"; or test "$dir/agent" = "$agent_dir"
        set -a global_dirs "$dir"
      else
        set -a project_dirs "$dir"
      end
    end
  end
  if test $mode = purge
    set global_dirs
    for dir in "$agent_dir" "$global_agents"
      test -d "$dir" -o -L "$dir"; and set -a global_dirs "$dir"
    end
  else
    for dir in $global_dirs
      _ui -i 0 note "Skipping "(_ui path "$dir")" (global config). Use 'clean_pi purge' for that."
    end
  end

  set -l targets
  switch $mode
    case skills agents
      for dir in $project_dirs
        set -l child "$dir/$mode"
        test -d "$child" -o -L "$child"; and set -a targets "$child"
      end
    case project purge
      set targets $project_dirs
      if test $mode = purge
        for dir in $global_dirs
          if test "$dir" = "$global_agents"
            test -d "$dir/skills" -o -L "$dir/skills"; and set -a targets "$dir/skills"
          else
            set -a targets "$dir"
          end
        end
      end
  end

  set -l sessions
  set -l session_dir "$agent_dir/sessions"
  if test $mode = project
    if set -q PI_CODING_AGENT_SESSION_DIR[1]
      set session_dir (path resolve -- "$PI_CODING_AGENT_SESSION_DIR")
    else
      for settings in "$agent_dir/settings.json" "$root/.pi/settings.json"
        if test -f "$settings"
          set -l configured (command jq -r '.sessionDir // empty' "$settings" 2>/dev/null)
          if test -n "$configured"
            set configured (string replace -r '^~/' "$HOME/" -- "$configured")
            if string match -q '/*' -- "$configured"
              set session_dir (path resolve -- "$configured")
            else
              set session_dir (path resolve -- "$root/$configured")
            end
          end
        end
      end
    end
    set sessions (_clean_pi_sessions "$root" "$session_dir" | command sort)
  end

  set -l label 'Pi project directories'
  contains -- $mode skills agents; and set label "Pi $mode directories"
  test $mode = purge; and set label 'Pi directories'
  if test (count $targets) -eq 0; and test (count $sessions) -eq 0
    _ui done "No $label or sessions under "(_ui path "$root")" outside dependency trees."
    return 0
  end

  _ui title "🔎 "(count $targets)" $label under "(_ui path "$root")":"
  for target in $targets
    set -l note ''
    _clean_claude_tracked "$target"; and set note "  "(_ui paint yellow '⚠ git-tracked')
    if test "$target" = "$agent_dir"; or test "$target" = "$global_agents/skills"
      set note "  "(_ui paint yellow '⚠ global config')
    end
    _ui item (_ui path "$target")"$note"
  end
  if test $mode = project
    _ui title "📁 "(count $sessions)" Pi sessions in "(_ui path "$session_dir")" for the tree:"
    for file in $sessions
      _ui item (_ui path "$file")
    end
  end

  if set -q _flag_dry_run
    _ui title "🧪 Dry run: nothing removed."
    return 0
  end

  if test $mode = purge
    _ui warn "Purging "(_ui path "$agent_dir")" removes Pi credentials, sessions, packages and settings."
    _ui note "Only "(_ui path "$global_agents/skills")" is removed from the shared global .agents directory."
    _clean_claude_confirm "   Type 'purge' to continue, anything else to abort:" purge; or return 1
  else
    _clean_claude_confirm "Remove "(count $targets)" $label and "(count $sessions)" Pi sessions? [y/N]"; or return 1
  end

  set -l removed 0
  for target in $sessions $targets
    command rm -rf -- "$target"; and set removed (math $removed + 1)
  end
  set -l total (math (count $sessions) + (count $targets))
  if test $removed -ne $total
    _ui warn "Removed $removed of $total paths; the rest survived (permissions?)."
    return 1
  end
  _ui done "Removed $removed Pi paths."
end
