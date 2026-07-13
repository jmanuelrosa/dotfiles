function clean_claude --description "Clean project Claude Code artifacts: skills/agents keep dotfiles symlinks, all wipes .claude"
  set -l mode $argv[1]
  test -z "$mode"; and set mode all

  if not contains -- $mode skills agents all
    echo "Usage: clean_claude [skills|agents|all]"
    return 1
  end

  # all: remove the whole .claude, including the dotfiles symlinks
  if test "$mode" = all
    if not test -e .claude -o -L .claude
      echo "🤷 No .claude in "(pwd)
      return 0
    end
    echo "🔥 About to remove the ENTIRE .claude (including dotfiles symlinks) in "(pwd)
    read -l -P "   Continue? [y/N] " reply
    if not string match -qir '^y(es)?$' -- $reply
      echo "🚫 Aborted."
      return 1
    end
    command rm -rf .claude
    echo "✨ .claude removed."
    return 0
  end

  # skills / agents: remove everything that is NOT a dotfiles-managed symlink
  set -l target ".claude/$mode"
  if not test -d "$target"
    echo "🤷 No $target in "(pwd)
    return 0
  end

  set -l doomed
  for entry in $target/*
    test -e "$entry" -o -L "$entry"; or continue
    if test -L "$entry"; and string match -q "$DOTFILES_DIR/*" -- (readlink "$entry")
      continue
    end
    set -a doomed "$entry"
  end

  if test (count $doomed) -eq 0
    echo "✨ No non-dotfiles $mode to remove in $target."
    return 0
  end

  echo "🧹 Non-dotfiles $mode in $target:"
  for entry in $doomed
    echo "   • "(path basename "$entry")
  end
  read -l -P "Remove "(count $doomed)" non-dotfiles $mode? [y/N] " reply
  if not string match -qir '^y(es)?$' -- $reply
    echo "🚫 Aborted."
    return 1
  end

  for entry in $doomed
    command rm -rf "$entry"
  end
  echo "✨ Removed "(count $doomed)" $mode; kept dotfiles symlinks."
end
