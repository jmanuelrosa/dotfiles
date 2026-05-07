function wt --description "Git worktree workflow helper: add, list, remove, prune"
  set -l sub $argv[1]
  set -l rest $argv[2..-1]

  switch $sub
    case add a
      _wt_add $rest
    case list ls l
      git worktree list
    case remove rm r
      _wt_remove $rest
    case prune p
      git worktree prune $rest
    case '' help -h --help
      _wt_help
    case '*'
      echo "wt: unknown subcommand '$sub'" >&2
      _wt_help >&2
      return 1
  end
end

function _wt_help
  echo "Usage: wt <subcommand> [args...]"
  echo ""
  echo "Subcommands:"
  echo "  add [-b <branch>] <dir>  Create worktree at sibling dir <dir>. Branch defaults"
  echo "                           to <dir>; pass -b/--branch to override (created from"
  echo "                           develop > main > master). Copies env/.vscode, installs"
  echo "                           deps if a lockfile is present, and cds into it."
  echo "  list                     List all worktrees"
  echo "  remove <name>            Remove a worktree (by branch name or path)"
  echo "  prune                    Prune stale worktree metadata"
end

function _wt_add
  argparse 'b/branch=' -- $argv
  or return 1

  set -l dir $argv[1]
  if test -z "$dir"
    echo "wt add: missing directory name" >&2
    echo "Usage: wt add [-b <branch>] <dir>" >&2
    return 1
  end

  if not git rev-parse --git-dir >/dev/null 2>&1
    echo "wt: not inside a git repository" >&2
    return 1
  end

  set -l branch $_flag_branch
  if test -z "$branch"
    set branch $dir
  end

  set -l main_wt (git worktree list --porcelain | head -n 1 | string replace 'worktree ' '')
  set -l parent_dir (dirname $main_wt)
  set -l target "$parent_dir/$dir"

  if test -e $target
    echo "wt add: target already exists: $target" >&2
    return 1
  end

  set -l base (git -C $main_wt symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | string replace -r '^origin/' '')
  if test -z "$base"
    for candidate in develop main master
      if git -C $main_wt show-ref --verify --quiet refs/heads/$candidate
        set base $candidate
        break
      end
    end
  end
  if test -z "$base"
    set base HEAD
  end

  if git show-ref --verify --quiet refs/heads/$branch
    echo "→ Checking out existing branch '$branch' into $dir/"
    git worktree add $target $branch; or return 1
  else if git show-ref --verify --quiet refs/remotes/origin/$branch
    echo "→ Creating local branch '$branch' tracking origin/$branch into $dir/"
    git worktree add -b $branch $target origin/$branch; or return 1
  else
    echo "→ Creating new branch '$branch' from '$base' into $dir/"
    git worktree add -b $branch $target $base; or return 1
  end

  for envfile in (command find $main_wt -maxdepth 1 -type f -name '.env*' 2>/dev/null)
    echo "→ Copying "(basename $envfile)
    cp $envfile $target/
  end

  if test -d $main_wt/.vscode
    echo "→ Copying .vscode/"
    cp -R $main_wt/.vscode $target/
  end

  cd $target

  if test -f pnpm-lock.yaml
    echo "→ pnpm install"
    pnpm install
  else if test -f bun.lock; or test -f bun.lockb
    echo "→ bun install"
    bun install
  else if test -f package-lock.json
    echo "→ npm install"
    npm install
  else if test -f yarn.lock
    echo "→ yarn install"
    yarn install
  end
end

function _wt_remove --argument-names target
  if test -z "$target"
    echo "wt remove: missing worktree name or path" >&2
    return 1
  end

  if test -d $target
    git worktree remove $target
    return $status
  end

  set -l found ""
  set -l current ""
  for line in (git worktree list --porcelain)
    if string match -q 'worktree *' -- $line
      set current (string replace 'worktree ' '' -- $line)
    else if string match -q "branch refs/heads/$target" -- $line
      set found $current
      break
    end
  end

  if test -n "$found"
    git worktree remove $found
  else
    git worktree remove $target
  end
end
