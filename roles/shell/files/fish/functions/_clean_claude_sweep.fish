function _clean_claude_sweep --description "Machine-wide .claude sweep: every project copy, skipping vendored dependency trees"
  set -l root $HOME
  set -l dry 0
  set -l extra_excludes
  set -l positional

  set -l i 1
  while test $i -le (count $argv)
    set -l arg $argv[$i]
    switch $arg
      case -n --dry-run
        set dry 1
      case -e --exclude
        set i (math $i + 1)
        if test $i -gt (count $argv)
          echo "❌ --exclude needs a pattern."
          return 1
        end
        set -a extra_excludes $argv[$i]
      case '-*'
        echo "❌ Unknown flag: $arg"
        return 1
      case '*'
        set -a positional $arg
    end
    set i (math $i + 1)
  end

  if test (count $positional) -gt 1
    echo "Usage: clean_claude sweep [root] [--dry-run] [--exclude PATTERN]"
    return 1
  end
  test (count $positional) -eq 1; and set root (path resolve -- $positional[1])

  if not test -d "$root"
    echo "❌ Not a directory: $root"
    return 1
  end
  if not command -q fd
    echo "❌ clean_claude sweep needs fd (brew install fd)."
    return 1
  end

  # Vendored, cached and app-owned trees: a .claude in here belongs to a package or
  # an application, not to a project of yours. Extend per-invocation with --exclude,
  # or permanently by setting CLEAN_CLAUDE_EXCLUDES.
  set -l excludes node_modules bower_components vendor Pods Carthage DerivedData \
    .bun .npm .yarn .pnpm-store .pub-cache .cargo .rustup .m2 .gradle .swiftpm .build \
    .venv venv site-packages .tox .stack-work .terraform .nvm .rbenv .pyenv \
    .cache .local Library .Trash .git
  set -a excludes $CLEAN_CLAUDE_EXCLUDES $extra_excludes

  set -l fd_args
  for pattern in $excludes
    set -a fd_args -E $pattern
  end

  # --prune stops the walk at each hit, so a nested .claude never doubles up.
  set -l found (command fd --type d --hidden --no-ignore --absolute-path --prune \
    $fd_args '^\.claude$' "$root" 2>/dev/null | string trim -r -c / | command sort)

  if test (count $found) -eq 0
    echo "✨ No .claude directories under "(_clean_claude_pretty "$root")" (outside dependency trees)."
    return 0
  end

  set -l global_hit
  set -l projects
  for dir in $found
    if test "$dir" = "$HOME/.claude"
      set global_hit "$dir"
    else
      set -a projects "$dir"
    end
  end

  echo "🔎 "(count $found)" .claude under "(_clean_claude_pretty "$root")":"
  for dir in $projects
    set -l note ""
    if command git -C (path dirname "$dir") ls-files --error-unmatch .claude >/dev/null 2>&1
      set note "  ⚠️  git-tracked"
    end
    echo "   • "(_clean_claude_pretty "$dir")"$note"
  end
  if set -q global_hit[1]
    echo "   • "(_clean_claude_pretty "$global_hit")"  ⚠️  global config"
  end

  if test $dry -eq 1
    echo "🧪 Dry run — nothing removed."
    return 0
  end

  set -l removed 0

  if test (count $projects) -gt 0
    read -l -P "Remove "(count $projects)" project .claude? [y/N] " reply
    if string match -qir '^y(es)?$' -- $reply
      for dir in $projects
        command rm -rf "$dir"; and set removed (math $removed + 1)
      end
    else
      echo "🚫 Projects kept."
    end
  end

  # The global one holds credentials, session history and the dotfiles-managed
  # skills/agents symlinks, so it gets its own gate rather than riding the y/N above.
  if set -q global_hit[1]
    echo "⚠️  "(_clean_claude_pretty "$global_hit")" is the global config: credentials, session history, plugins,"
    echo "   and the skills/agents symlinks the ai role owns. Restoring it means"
    echo "   'make run-role ROLE=ai' plus re-authenticating."
    read -l -P "   Type 'global' to remove it too, anything else to keep it: " reply
    if test "$reply" = global
      command rm -rf "$global_hit"; and set removed (math $removed + 1)
      echo "🔥 Global .claude removed — run 'make run-role ROLE=ai' to restore the managed links."
    else
      echo "🚫 Global .claude kept."
    end
  end

  if test $removed -eq 0
    echo "🚫 Nothing removed."
    return 1
  end
  echo "✨ Removed $removed .claude "(test $removed -eq 1; and echo directory; or echo directories)"."
end
