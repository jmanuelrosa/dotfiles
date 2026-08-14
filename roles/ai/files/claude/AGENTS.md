# Global instructions

The agent-neutral core: tooling, code standards, and git.
This file is the canonical one and every agent reads it under the name it expects, so it names skills rather than the slash-command spelling any one agent gives them (`commit` reads as `/commit` in Claude Code and `/skill:commit` in Pi).
Claude-only mechanics (settings, hooks, plan mode, sandbox) live in `rules/claude.md`.

## Tools & CLIs

CLI-first for these domains, never WebFetch or MCP for them.
If a CLI is missing or auth-broken, say so; don't silently fall back.

| Domain | CLI |
|---|---|
| Jira | `acli` |
| GitHub | `gh` |
| GitLab | `glab` |
| Sentry | `sentry` |
| Bruno API tests | `bru-cli` |
| Notion | `ntn` |
| Library / framework / SDK / API / CLI / cloud service docs | `bunx ctx7` |

- IMPORTANT: any question about a library, framework, SDK, API, CLI tool, or cloud service is a docs question. Training data is stale, so fetch current docs BEFORE answering: `bunx ctx7 library <name> "<q>"`, then `bunx ctx7 docs <id> "<q>"` (free anonymous tier; `npx -y ctx7` if bun is missing). Pick the id by benchmark score among high-reputation results, preferring a `/websites/...` vendor docs site over a bare repo, since the repo usually carries a fraction of the snippets. Never the Context7 MCP server, and never WebFetch as the first move. If ctx7 returns no usable match, say so, then fall back to WebSearch/WebFetch.
- Three things take precedence. The domain CLIs above are for *doing* (fetch the ticket, list the PRs) while ctx7 is for *how it works*, so "list my open PRs" is `gh` and "what does `gh pr list --search` accept" is a docs question. For a CLI installed on this machine, `cmd --help` / `man` beats ctx7 on flags and syntax. Claude Code, the Agent SDK and the Anthropic API belong to the `claude-api` skill, not to ctx7.
- `glab` has multiple authenticated hosts: inside a repo it auto-selects; repo-agnostic `glab api` calls must iterate every host (recipes live in the `pr` skill and the `weekly-recap` script).
- JS package manager: match the lockfile. No lockfile but the README names one, follow the README.

## Code standards

- Default to zero comments; prefer explicit names. A comment must earn its place by explaining a non-obvious WHY, never WHAT. Same bar for JSDoc.
- Never reference issue/PR/ticket/ADR numbers in code comments; that context belongs in branch names, PR descriptions, and git blame.
- No hardcoded values (magic numbers, URLs, tokens, paths); derive them from data or the environment at runtime.
- Never use em or en dashes in chat. Use a regular hyphen, comma, colon, or parentheses. (`em-dash-gate.sh` catches them in files; conversation is the surface no hook sees.)
- Never hard-wrap prose or Markdown to a fixed column width. Write one sentence per line (semantic line breaks) and let the editor soft-wrap. Applies to chat, docs, skills, agents, commit and PR bodies. Match the file you are editing rather than reflowing existing prose to a different wrap.
- Match the length of a written document to what the task needs: cover the substance, and do not pad with filler sections, redundant summaries, or boilerplate.
- Prefer free, zero-key, zero-install integrations (anonymous tiers, `bunx`) over API-key or brew-based setups.
- ADRs match the shape and numbering of the repo's existing `docs/adr/`, over any skill's own format. Never edit an accepted ADR; supersede it with a new one.
- Planning documents go in the repo's `docs/plans/`, except where a skill names its own path.

## Git

- Commits and pushes go through the `commit` and `pr` skills, never a raw `git commit` or `git push`.
- Branch names follow `<type>/<slug>` or `<type>/<TICKET>-<slug>` using the Conventional Branch set (`feature`, `fix`, `chore`, `docs`, `refactor`, `test`, `perf`, `ci`, `build`, `style`, `revert`); create with `git switch -c`, never `git checkout -b`. `<TICKET>` is a Jira key (`PROJ-123`) or a GitHub issue (`gh-456`); `s-task <ref>` scaffolds either from the issue itself, auto-detecting the provider. If an existing branch doesn't follow this convention, don't derive commit types or PR titles from its name: stop and ask the user.
