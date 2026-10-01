# clean_pi

Recursively cleans Pi and neutral agent project artifacts, plus Pi sessions selected by their recorded working directory.

```fish
clean_pi [MODE] [ROOT] [--dry-run] [--exclude PATTERN] [--include PATTERN]
```

| Mode | Scope |
|---|---|
| `project` (default) | Project `.pi` and `.agents` directories plus matching sessions |
| `skills` | Project `.pi/skills` and `.agents/skills` |
| `agents` | Project `.pi/agents` and `.agents/agents` |
| `purge` | Project artifacts under `$HOME`, global Pi agent configuration, and `~/.agents/skills` |

`ROOT` defaults to the working directory.
The cleaner honors the configured session directory; sessions stored elsewhere via `--session-dir` are not discovered.
Project cleanup leaves global trust entries unchanged.
Non-purge modes preserve global Pi and neutral agent configuration.

`purge` requires typing `purge` because it removes credentials, packages, settings, and sessions.
Other shared content under `~/.agents` is preserved.
Restore global tooling with `make run-role ROLE=ai` and re-authenticate afterward.
See [shared cleanup helpers](../clean_ai/README.md) for exclusions.
