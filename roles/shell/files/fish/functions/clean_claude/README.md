# clean_claude

Recursively cleans Claude project artifacts and stored project state.

```fish
clean_claude [MODE] [ROOT] [--dry-run] [--exclude PATTERN] [--include PATTERN]
```

| Mode | Scope |
|---|---|
| `project` (default) | Project `.claude` directories plus stored state for `ROOT` and its descendants |
| `skills` | Project `.claude/skills` directories only |
| `agents` | Project `.claude/agents` directories only |
| `purge` | Project directories under `$HOME`, global Claude configuration, and all stored project state |

`ROOT` defaults to the working directory.
Candidates are previewed before deletion; `--dry-run` also passes through to the Claude state-purge CLI.
Project-state cleanup does not require a remaining `.claude` directory.
Directory exclusions affect artifact deletion, not state scoping.

Linked worktrees are skipped because purging their state can remove the main checkout's configuration; `--worktree-config` explicitly opts in.
Only `purge` can remove `~/.claude`, and it requires typing `purge` because that directory includes credentials and history.
Restore global tooling with `make run-role ROLE=ai` and re-authenticate afterward.
See [shared cleanup helpers](../clean_ai/README.md) for exclusions and [aliases](../../conf.d/aliases/README.md) for the `clean:claude` family.
