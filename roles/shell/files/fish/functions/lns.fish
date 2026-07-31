function lns --description "List symlinks under a directory tree, and optionally remove them by what they point at"
  argparse -n lns h/help 'c/contains=' b/broken r/remove n/dry-run y/yes a/all -- $argv
  or return 1

  if set -q _flag_help
    _lns_usage
    return 0
  end

  if test (count $argv) -gt 1
    _lns_usage
    return 1
  end

  set -l root (pwd)
  set -q argv[1]; and set root (path resolve -- $argv[1])

  if not test -d "$root"
    _ui err "Not a directory: "(_ui path "$root")
    return 1
  end
  if not command -q fd
    _ui err "lns needs fd (brew install fd)."
    return 1
  end

  # Borrowed from clean_claude rather than restated: that list is exactly "directories
  # whose contents belong to someone else", which is the question here too, and a second
  # copy of forty names would drift. It follows that CLEAN_CLAUDE_EXCLUDES extends lns.
  set -l fd_args
  if not set -q _flag_all
    for pattern in (_clean_claude_excludes)
      set -a fd_args -E $pattern
    end
  end

  # --type l reports a link and never follows it: no -L, so the walk cannot descend into
  # a target and loop, and no --prune (unlike _clean_claude_find, which needs it to stop
  # a nested .claude doubling up) because a symlink is already a leaf.
  set -l found (command fd --type l --hidden --no-ignore --absolute-path $fd_args . "$root" 2>/dev/null | string trim -r -c / | command sort)

  set -l links
  set -l targets
  for link in $found
    # --broken is a claim about the link rather than about its target, so it is answered
    # by -e alone and an unreadable link can satisfy it. The link exists by construction,
    # so -e failing means it resolves to nothing.
    if set -q _flag_broken
      test -e "$link"; and continue
    end
    # An unreadable link yields no target, so it can never match --contains: a filter is
    # a claim about the target, and an unknown target cannot satisfy one.
    set -l target (_lns_target "$link")
    if set -q _flag_contains
      string match -q "*$_flag_contains*" -- "$target"; or continue
    end
    set -a links "$link"
    set -a targets "$target"
  end

  set -l count (count $links)
  set -l label symlinks
  test $count -eq 1; and set label symlink
  set -q _flag_broken; and set label "broken $label"

  # One descriptor per filter, joined, so the four combinations of --broken and --contains
  # read as sentences without four copies of each heading.
  set -l descr
  set -q _flag_broken; and set -a descr broken
  set -q _flag_contains; and set -a descr "pointing at '$_flag_contains'"
  set -l matching (string join " and " $descr)

  if test $count -eq 0
    if test -n "$matching"
      _ui title "🤷 No symlink under "(_ui path "$root")" is $matching."
      test (count $found) -gt 0; and _ui note (count $found)" found, none matching."
    else
      _ui title "🤷 No symlinks under "(_ui path "$root")"."
    end
    return 0
  end

  if test -n "$matching"
    _ui title "🔎 $count of "(count $found)" symlinks under "(_ui path "$root")", $matching:"
  else
    _ui title "🔎 $count $label under "(_ui path "$root")":"
  end

  for i in (seq $count)
    if test -z "$targets[$i]"
      _ui item (_ui path "$links[$i]")(_ui paint dim " → ")(_ui paint yellow "⚠ unreadable")
      continue
    end
    set -l marker ""
    # The link exists by construction, so -e failing means the target does not.
    test -e "$links[$i]"; or set marker "  "(_ui paint yellow "⚠ broken")
    _ui item (_ui path "$links[$i]")(_ui paint dim " → ")(_ui path "$targets[$i]")"$marker"
  end

  # Named rather than left implicit: a count that quietly omits node_modules reads as
  # "that is all of them".
  set -q _flag_all; or _ui note "Dependency and build trees were skipped; --all includes them."

  if not set -q _flag_remove
    _ui done "$count $label."
    return 0
  end

  if set -q _flag_dry_run
    _ui title "🧪 Dry run: nothing removed."
    return 0
  end

  if not set -q _flag_yes
    _clean_claude_confirm "Remove $count $label? [y/N]"; or return 1
  end

  set -l removed 0
  for link in $links
    # -L rather than -e, so a broken link still goes and a real directory never does.
    test -L "$link"; and command rm "$link" 2>/dev/null; and set removed (math $removed + 1)
  end

  if test $removed -ne $count
    _ui warn "Removed $removed of $count $label; the rest survived (permissions?)."
    return 1
  end

  _ui done "Removed $removed $label. Targets are untouched."
end
