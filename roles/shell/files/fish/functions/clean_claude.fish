function clean_claude --description "Remove Claude Code artifacts under a directory tree: skills, agents, whole .claude projects, or everything on the machine"
  argparse -n clean_claude h/help n/dry-run w/worktree-config 'e/exclude=+' 'i/include=+' -- $argv
  or return 1

  if set -q _flag_help
    _clean_claude_usage
    return 0
  end

  set -l mode project
  set -q argv[1]; and set mode $argv[1]

  if not contains -- $mode project skills agents purge; or test (count $argv) -gt 2
    _clean_claude_usage
    return 1
  end

  set -l root (pwd)
  test $mode = purge; and set root $HOME
  set -q argv[2]; and set root (path resolve -- $argv[2])

  if not test -d "$root"
    _ui err "Not a directory: "(_ui path "$root")
    return 1
  end
  if not command -q fd
    _ui err "clean_claude needs fd (brew install fd)."
    return 1
  end
  if contains -- $mode project purge; and not command -q claude
    _ui err "clean_claude $mode needs the claude CLI to purge project state."
    return 1
  end
  # jq only reads ~/.claude.json to find subprojects' config entries; without it the
  # tree's transcripts still go, so this is a warning rather than a hard stop.
  if test $mode = project; and not command -q jq
    _ui warn "jq is missing, so subprojects' ~/.claude.json entries will be left in place."
  end

  set -l excludes (_clean_claude_excludes $_flag_exclude)
  if set -q _flag_include[1]
    set -l kept
    for name in $excludes
      contains -- $name $_flag_include; or set -a kept $name
    end
    set excludes $kept
  end

  # ~/.claude carries credentials, session history, plugins and the symlinks the ai
  # role owns, so it is off limits to every mode but purge. That is what keeps a
  # `cd ~; clean_claude skills` from quietly dismantling the global setup.
  set -l global_hit
  set -l projects_found
  for dir in (_clean_claude_find "$root" $excludes)
    if test "$dir" = "$HOME/.claude"
      set global_hit "$dir"
    else
      set -a projects_found "$dir"
    end
  end

  if test $mode = purge
    test -d "$HOME/.claude" -o -L "$HOME/.claude"; and set global_hit "$HOME/.claude"
  else if set -q global_hit[1]
    _ui -i 0 note "Skipping "(_ui path "$global_hit")" (global config). Use 'clean_claude purge' for that."
    set -e global_hit
  end

  set -l label .claude
  set -l targets
  switch $mode
    case skills agents
      set label ".claude/$mode"
      for dir in $projects_found
        test -d "$dir/$mode" -o -L "$dir/$mode"; and set -a targets "$dir/$mode"
      end
    case project purge
      set targets $projects_found $global_hit
  end

  # project mode still has work with no directory to delete: state for this project
  # lives under ~/.claude/projects and outlives its .claude.
  if test (count $targets) -eq 0; and test $mode != project
    _ui done "No $label under "(_ui path "$root")" outside dependency trees."
    return 0
  end

  if test (count $targets) -gt 0
    _ui title "🔎 "(count $targets)" $label under "(_ui path "$root")":"
    for target in $targets
      set -l note ""
      _clean_claude_tracked "$target"; and set note "  "(_ui paint yellow "⚠ git-tracked")
      test "$target" = "$HOME/.claude"; and set note "  "(_ui paint yellow "⚠ global config")
      _ui item (_ui path "$target")"$note"
    end
  else
    _ui title "🤷 No $label under "(_ui path "$root")"."
  end

  # Scoped by the state stores rather than by the .claude directories above: a project
  # keeps transcripts and a ~/.claude.json entry long after its .claude is gone.
  if test $mode = project
    _ui title "📁 Purging Claude state under "(_ui path "$root")": transcripts, tasks and file history for the whole tree, plus the ~/.claude.json entry of each project at or below it."
  else if test $mode = purge
    _ui title "📁 Purging Claude state for EVERY project on this machine."
  end

  set -l worktree_config 0
  set -q _flag_worktree_config; and set worktree_config 1

  if set -q _flag_dry_run
    _clean_claude_purge_state $mode --dry-run "$root" $worktree_config
    _ui title "🧪 Dry run: nothing removed."
    return 0
  end

  if test $mode = purge
    _ui warn (_ui path "$HOME/.claude")" goes with it: credentials, session history, plugins"
    _ui note "and the skills/agents symlinks the ai role owns. Getting back means"
    _ui note "'make run-role ROLE=ai' plus re-authenticating."
    _clean_claude_confirm "   Type 'purge' to continue, anything else to abort:" purge; or return 1
  else
    set -l prompt "Remove "(count $targets)" $label?"
    if test $mode = project
      if test (count $targets) -eq 0
        set prompt "Purge Claude state under "(_ui path "$root")"?"
      else
        set prompt "Remove "(count $targets)" $label and purge Claude state under "(_ui path "$root")"?"
      end
    end
    _clean_claude_confirm "$prompt [y/N]"; or return 1
  end

  # State first: it lives inside ~/.claude/projects, which purge mode is about to delete.
  _clean_claude_purge_state $mode --yes "$root" $worktree_config

  set -l removed 0
  for target in $targets
    command rm -rf "$target"; and set removed (math $removed + 1)
  end

  if test $removed -ne (count $targets)
    _ui warn "Removed $removed of "(count $targets)" $label; the rest survived (permissions?)."
    return 1
  end

  switch $mode
    case skills agents
      _ui done "Removed $removed $label. Restore what you need with 'claude-kit add <name> --type skill|agent|plugin'."
    case project
      if test $removed -eq 0
        _ui done "Purged Claude state under "(_ui path "$root")"; there was no $label to remove."
      else
        _ui done "Removed $removed $label and purged Claude state under "(_ui path "$root")"."
      end
    case purge
      _ui done "Removed $removed $label and purged all project state. Run 'make run-role ROLE=ai' to rebuild the managed links."
  end
end
