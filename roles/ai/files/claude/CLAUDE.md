# Global Claude instructions

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
- Three things take precedence. The domain CLIs above are for *doing* (fetch the ticket, list the PRs) while ctx7 is for *how it works*, so "list my open PRs" is `gh` and "what does `gh pr list --search` accept" is a docs question. For a CLI installed on this machine, `cmd --help` / `man` beats ctx7 on flags and syntax. Claude Code, the Agent SDK and the Anthropic API belong to the `claude-api` skill and the `claude-code-guide` agent, not to ctx7.
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
- Planning documents go in the repo's `docs/plans/`, matching the `plansDirectory` setting that plan mode writes through, except where a skill names its own path. Approved plans are date-stamped by the `plan-date-stamp.sh` hook and committed, so don't rename one by hand or write the date into the body.

## Git & sandbox

- Commits and pushes go through `/commit` and `/pr`; a hook enforces this, and `/pr` carries the only working push path.
- Branch names follow `<type>/<slug>` or `<type>/<TICKET>-<slug>` using the Conventional Branch set (`feature`, `fix`, `chore`, `docs`, `refactor`, `test`, `perf`, `ci`, `build`, `style`, `revert`); create with `git switch -c`, never `git checkout -b`. `<TICKET>` is a Jira key (`PROJ-123`) or a GitHub issue (`gh-456`); `s-task <ref>` scaffolds either from the issue itself, auto-detecting the provider. If an existing branch doesn't follow this convention, don't derive commit types or PR titles from its name: stop and ask the user.
- Only force-push, branch deletion, and lockfile writes are genuinely denied: hand the user the exact command instead of retrying.
- `acli` runs outside the sandbox, so run it before declaring it blocked. Its session can lapse mid-run and stay lapsed, so keep it off the critical path of anything already half-done; the `jira` skill's Auth check section has the detail.
