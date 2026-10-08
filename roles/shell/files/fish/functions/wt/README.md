# wt

Git worktree workflow helper with optional Herdr workspace integration.

```fish
wt add [-b <branch>] [-h/--herdr] [-f/--focus] <dir>
wt list
wt remove [-h/--herdr] [-f/--force] <name>
wt prune
```

`add` creates a sibling worktree and defaults its branch to the directory name.
It copies root and nested `.env*` files from the main checkout, preserving their relative paths and skipping `.git/`, `node_modules/`, `.venv/`, `venv/`, and `vendor/` directories.
It also merges `.vscode/`, `.claude/`, and `.agents/` into the new checkout, carrying over project-local skills and preserving their symlinks.
It excludes `.claude/worktrees/` from both copies so existing nested worktrees are not duplicated.
It grants Pi sandbox access to the repository's shared Git metadata, runs `kura converge --quiet` when `.claude/` or `.agents/` is present, and installs dependencies from the available lockfile in frozen mode.
`--herdr` also opens a Herdr workspace; `--focus` changes to the new worktree and focuses that workspace when enabled.

`remove` accepts a branch name or path; `--herdr` also closes its workspace.
`--force` permits Git to remove a dirty worktree, so inspect local changes first.
Run `wt --help` for the full argument descriptions.
