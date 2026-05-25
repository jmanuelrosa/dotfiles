# Global Claude instructions

## Git commits

Do not write `Co-Authored-By: Claude …` (or any `🤖 Generated with` line) into commit message bodies, plan files, or HEREDOCs that produce commit messages. Attribution is handled at the Claude Code platform level via the `attribution` setting in `settings.json`; duplicating it in the message body produces the trailer even when attribution is configured to be empty.

This applies to direct `git commit -m` invocations and to any plan or skill that prescribes a commit message template.

## Tools & CLIs

When the work touches one of these domains, prefer the listed CLI over WebFetch, MCP servers, or generic alternatives. Fall back only if the CLI genuinely cannot do the job (and say so).

| Domain                    | CLI       | Notes                                         |
|---------------------------|-----------|-----------------------------------------------|
| Jira (issues, sprints)    | `acli`    | See the `jira` skill for query patterns       |
| GitHub (repos, PRs, CI)   | `gh`      | See the `pr` and `commit` skills              |
| GitLab (repos, MRs, CI)   | `glab`    | Same role as `gh`; see the `pr`/`commit` skills |
| Sentry (errors, releases) | `sentry`  | Use `sentry --help` to discover subcommands   |
| Bruno (API test requests) | `bru-cli` | Use `bru-cli --help` to discover subcommands  |

Rules:
- Reach for the CLI first. Do **not** open a Jira/GitHub/Sentry URL with WebFetch when the CLI can answer.
- Do **not** call an MCP server for these domains if the CLI is installed.
- If a CLI is missing or auth-broken, surface that — don't silently fall back.

## JS package managers

Match the project's lockfile — don't default to `npm`:

| Lockfile           | Use     |
|--------------------|---------|
| `pnpm-lock.yaml`   | `pnpm`  |
| `bun.lockb`        | `bun`   |
| `yarn.lock`        | `yarn`  |
| `package-lock.json` (or none) | `npm` |

Applies to `install`, `add`, `remove`, `run`, and scripts. If a repo has no lockfile but the README specifies a manager, follow the README.

## Don't invoke TUIs

These tools are installed for interactive human use and will hang or look broken when run by Claude. Do **not** invoke them — use the non-interactive equivalent.

| TUI         | Use instead                                         |
|-------------|-----------------------------------------------------|
| `lazygit`   | `git` (or `gh` / `glab` for hosted ops)             |
| `btop`      | `ps`, `top -l 1 -n 20`                              |
| `ctop`      | `docker stats --no-stream`                          |
| `nnn`       | `ls`, `fd`, the Read/Glob/Grep tools                |
| `pgcli` (interactive REPL) | `psql -c "..."` for one-shot SQL     |
| `lazydocker`| `docker ps`, `docker inspect`, `docker logs`        |
