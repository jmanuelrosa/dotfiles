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
  echo "  add [-b <branch>] [-h/--herdr] [-f/--focus] <dir>"
  echo "                           Create worktree at sibling dir <dir>. Branch defaults"
  echo "                           to <dir>; pass -b/--branch to override (created from"
  echo "                           develop > main > master). Copies env/.vscode/.claude and"
  echo "                           installs deps from lockfile (frozen) if present."
  echo "                           Pass -h/--herdr to also open the worktree as a workspace"
  echo "                           in the current herdr session. Pass -f/--focus to move to"
  echo "                           the new worktree (cd, and focus the herdr workspace);"
  echo "                           without it the worktree is created in the background."
  echo "  list                     List all worktrees"
  echo "  remove [-h/--herdr] [-f/--force] <name>"
  echo "                           Remove a worktree (by branch name or path). Pass -h/--herdr"
  echo "                           to also close its workspace in the current herdr session."
  echo "  prune                    Prune stale worktree metadata"
end

function _wt_in_herdr
  set -q HERDR_ENV; and type -q herdr
end

function _wt_herdr_workspace_id --argument-names abs_path
  herdr worktree list --json 2>/dev/null \
    | jq -r --arg p $abs_path \
      '[.. | objects | select(.path? == $p) | .open_workspace_id] | map(select(. != null)) | first // empty'
end

function _wt_add
  argparse 'b/branch=' 'h/herdr' 'f/focus' -- $argv
  or return 1

  set -l dir $argv[1]
  if test -z "$dir"
    echo "wt add: missing directory name" >&2
    echo "Usage: wt add [-b <branch>] [-h/--herdr] [-f/--focus] <dir>" >&2
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

  if test -d $main_wt/.claude
    echo "→ Copying .claude/"
    cp -R $main_wt/.claude $target/
  end

  set -l prev_dir $PWD
  cd $target

  if test -f pnpm-lock.yaml
    echo "→ pnpm install --frozen-lockfile"
    pnpm install --frozen-lockfile
  else if test -f bun.lock; or test -f bun.lockb
    echo "→ bun install --frozen-lockfile"
    bun install --frozen-lockfile
  else if test -f package-lock.json
    echo "→ npm ci"
    npm ci
  else if test -f yarn.lock
    echo "→ yarn install --frozen-lockfile"
    yarn install --frozen-lockfile
  end

  set -l focus_arg --no-focus
  if set -q _flag_focus
    set focus_arg --focus
  end

  if set -q _flag_herdr
    if _wt_in_herdr
      echo "→ Opening worktree in herdr"
      if not herdr worktree open --path $target --label $branch $focus_arg
        echo "wt: herdr worktree open failed (worktree created regardless)" >&2
      end
    else
      echo "wt: --herdr ignored (not inside a herdr session)" >&2
    end
  end

  if not set -q _flag_focus
    cd $prev_dir
  end
end

function _wt_remove
  argparse 'f/force' 'h/herdr' -- $argv
  or return 1

  set -l target $argv[1]
  if test -z "$target"
    echo "wt remove: missing worktree name or path" >&2
    return 1
  end

  set -l force_args
  if set -q _flag_force
    set force_args --force
  end

  set -l resolved
  if test -d $target
    set resolved (path resolve $target)
  else
    set -l current ""
    for line in (git worktree list --porcelain)
      if string match -q 'worktree *' -- $line
        set current (string replace 'worktree ' '' -- $line)
      else if string match -q "branch refs/heads/$target" -- $line
        set resolved $current
        break
      end
    end
  end

  set -l remove_arg $target
  if test -n "$resolved"
    set remove_arg $resolved
  end

  set -l ws_id
  if set -q _flag_herdr
    if _wt_in_herdr
      if test -n "$resolved"
        set ws_id (_wt_herdr_workspace_id $resolved)
      end
    else
      echo "wt: --herdr ignored (not inside a herdr session)" >&2
    end
  end

  git worktree remove $force_args $remove_arg
  or return $status

  if test -n "$ws_id"
    echo "→ Closing herdr workspace $ws_id"
    if not herdr workspace close $ws_id
      echo "wt: herdr workspace close failed (worktree removed regardless)" >&2
    end
  end
end
