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
| Library/framework/SDK docs | `bunx ctx7` | Context7; see "Latest docs via ctx7" below |

Rules:
- Reach for the CLI first. Do **not** open a Jira/GitHub/Sentry URL with WebFetch when the CLI can answer.
- Do **not** call an MCP server for these domains if the CLI is installed.
- If a CLI is missing or auth-broken, surface that — don't silently fall back.

**Multiple GitLab accounts.** `glab` may be configured with more than one host (a personal `gitlab.com` and a work alias). **Inside a repo**, glab auto-selects the host and token from the git remote — repo-scoped commands (`glab mr create`, `glab repo view`) need no `--hostname`. **Repo-agnostic** calls (`glab api …`) hit only the default host, so they miss the other account; enumerate every authenticated host and pass `--hostname` per host:

```sh
for H in $(glab auth status 2>&1 | grep -E '^[^[:space:]]'); do glab api --hostname "$H" …; done
```

**Latest docs via `ctx7`.** Whenever the user asks about a library, framework, SDK, API, CLI tool, or cloud service — including well-known ones (React, Next.js, Prisma, Tailwind, Django), since training data may not reflect recent changes — fetch current docs with the Context7 CLI before answering:

```sh
bunx ctx7 library <name> "<question>"      # resolve the Context7 library ID
bunx ctx7 docs <libraryId> "<question>"    # fetch docs; skip the resolve step if an ID like /vercel/next.js is already known
```

Run it through `bunx` (or `npx -y ctx7` if bun is unavailable) — the CLI is not installed globally. It uses Context7's free anonymous tier; no API key is configured. Do **not** use the Context7 MCP server or WebFetch for library docs.

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

## Code standards

- Complete code only - no TODOs, no placeholders, no incomplete implementations
- Default to writing no comments. Prefer readable, explicit code (well-named variables, functions, and types) over commentary. A comment is justified only when it explains a non-obvious WHY: hidden constraint, subtle invariant, workaround for a known bug, or surprising behavior a future reader would otherwise misread. Comments that restate WHAT the code does are forbidden, including multiline narrative blocks. JSDoc/docstring format (`/** */`) is allowed only when its content is WHY — the format alone does not earn an exemption.
- Never reference issue, PR, ticket, or ADR numbers in code comments (no `owner/repo#535`, `PR #561`, `(#545)`, `Fixes #123`, `JIRA-1234`, `ADR-0042`, etc.). They rot as soon as trackers move or decisions are superseded. The branch name, PR description, the ADR document itself, and git blame are the right places for that context. Comments should describe the WHY in self-contained prose.

## Approach discipline

- Verify before you propose. Inspect the actual harness, config file, or env var in question — don't diagnose from memory or assumption and then walk it back after testing.
- Simplest thing that fits the evidence first. Before writing a new script or artifact, check whether a single query, an existing CLI flag, or a one-line config change already does the job.
- No hardcoded URLs, tokens, or paths. Resolve them at runtime from the environment (env vars, CLI output, on-disk config) — never bake in a literal.
- When a shell command misbehaves, look at what the harness actually sent (quoting, `!` escaping, heredocs) before blaming the source.

## Sandbox and auth reality

- Don't preemptively claim a command or auth step is blocked. Run it first; hand off only if the tool returns a real error, and show that error. What runs outside the sandbox is recorded in `sandbox.excludedCommands` — check it, don't memorize it.
- Normal commits/pushes go through `/commit` and `/pr` (the hook enforces this; `/pr` carries the only working push path here). Only force-push, branch deletion, and lockfile writes are genuinely denied — for those, hand the user the exact command.
- `acli` (Jira auth) sits in `excludedCommands` and has repeatedly been wrongly declared "sandbox-blocked." Run the acli command first; only if it returns a real write/auth error is there a problem, and the fix is the user re-authenticating interactively with `acli auth login` — never a guess that the sandbox forbids it.
