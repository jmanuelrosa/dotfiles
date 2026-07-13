# Global Claude instructions

- Never write `Co-Authored-By` or `🤖 Generated with` lines anywhere: commit messages, plan files, HEREDOCs. Attribution is handled by the `attribution` setting in `settings.json`.

## Tools & CLIs

CLI-first for these domains, never WebFetch or MCP for them. If a CLI is missing or auth-broken, say so; don't silently fall back.

| Domain | CLI |
|---|---|
| Jira | `acli` |
| GitHub | `gh` |
| GitLab | `glab` |
| Sentry | `sentry` |
| Bruno API tests | `bru-cli` |
| Library/framework/SDK docs | `bunx ctx7` |

- IMPORTANT: for any library/framework/SDK/API question, fetch current docs BEFORE answering (training data is stale): `bunx ctx7 library <name> "<q>"`, then `bunx ctx7 docs <id> "<q>"` (free anonymous tier; `npx -y ctx7` if bun is missing). Never the Context7 MCP server or WebFetch for this.
- glab has multiple authenticated hosts: inside a repo it auto-selects; repo-agnostic `glab api` calls must iterate every host (recipes live in the `pr` and `weekly-recap` skills).
- JS package manager: match the lockfile (`pnpm-lock.yaml`→pnpm, `bun.lockb`→bun, `yarn.lock`→yarn, `package-lock.json` or none→npm). No lockfile but the README names one → follow the README.

## Code standards

- Complete code only: no TODOs, placeholders, or stubs.
- Default to zero comments; prefer explicit names. A comment must earn its place by explaining a non-obvious WHY (hidden constraint, workaround, surprising behavior), never WHAT. Same bar for JSDoc.
- Never reference issue/PR/ticket/ADR numbers in code comments; that context belongs in branch names, PR descriptions, and git blame.
- When writing an ADR, match the shape and numbering of the existing ADRs in the repo's `docs/adr/` over any skill's own ADR format; only a repo with no ADRs yet falls back to the skill's format. Never edit an accepted ADR; supersede it with a new one.
- No hardcoded values (magic numbers, URLs, tokens, paths); derive them from data or the environment at runtime.
- Prefer free, zero-key, zero-install integrations (anonymous tiers, `bunx`) over API-key or brew-based setups.
- Never use em or en dashes (`—`, `–`) in anything you write: chat, code, comments, docs, commits, PR text. Use a regular hyphen, comma, colon, or parentheses instead.
- Never hard-wrap prose or Markdown to a fixed column width. Write one sentence per line (semantic line breaks) and let the editor soft-wrap; don't insert manual newlines mid-sentence to hit a width. Applies to chat, docs, skills, agents, commit and PR bodies. Don't reflow existing prose that uses a different wrap just to apply this; match the file you're editing.
- For code, wrap to the project's `.editorconfig` `max_line_length`. If it's unset, follow the formatter config (Prettier `printWidth`, Black `line-length`, gofmt, etc.); only then fall back to the language default. Don't default to 80 when the config says otherwise.

## Git & sandbox

- Commits and pushes go through `/commit` and `/pr`; a hook enforces this, and `/pr` carries the only working push path.
- Branch names follow `<type>/<slug>` or `<type>/<TICKET>-<slug>` using the Conventional Branch set (`feature`, `fix`, `chore`, `docs`, `refactor`, `test`, `perf`, `ci`, `build`, `style`, `revert`); create with `git switch -c`, never `git checkout -b`. If an existing branch doesn't follow this convention, don't derive commit types or PR titles from its name: stop and ask the user (rename it, or pass an explicit value like `/pr --title`).
- Only force-push, branch deletion, and lockfile writes are genuinely denied: hand the user the exact command instead of retrying.
- `acli` runs outside the sandbox. Run it before declaring it blocked; a real auth error means the user runs `acli auth login`, never a guess that the sandbox forbids it.
