# Claude Code mechanics

The settings, hooks, plan mode and sandbox behavior that no other agent has.
The tooling, code standards and git conventions are agent-neutral and live in `AGENTS.md`, which is what this machine's `~/.claude/CLAUDE.md` points at.

- Attribution is handled by the `attribution` setting in `settings.json`, which is why no `Co-Authored-By` or `🤖 Generated with` line is ever written by hand.
- Claude Code, the Agent SDK and the Anthropic API belong to the `claude-api` skill and the `claude-code-guide` agent, not to ctx7.
- Skills are invoked as `/<name>`, so the `commit` skill is `/commit`. The read-only search subagent is `Explore`, and a fresh session is `/clear`.
- Pass `effort: low` when spawning `Explore` for a search; locating code does not need deep reasoning, and the cheaper run is the point of delegating it.
- `em-dash-gate.sh` is the hook that refuses em and en dashes in written files.

## Plan mode

- Plan mode writes through the `plansDirectory` setting in `settings.json`, which points at the repo's `docs/plans/`.
- Approved plans are date-prefixed to `YYYY-MM-DD-<slug>.md` by the `plan-date-stamp.sh` hook on `ExitPlanMode`, and they are committed. Don't rename one by hand, and don't write the date into the plan's own body: the filename carries it.

## Git & sandbox

- A hook enforces the `/commit` and `/pr` route, and `/pr` carries the only working push path.
- Only force-push, branch deletion, and lockfile writes are genuinely denied: hand the user the exact command instead of retrying.
- `sandbox.excludedCommands` exempts a command only when it is the **leading token** of the whole call: `git`, `gh`, `glab`, `pgcli`, `acli`, `sentry`, `bru`, `ntn`, `wrangler`, `cf`, ctx7, the cloud CLIs, and the `commit`/`pr` `apply.py` scripts. `cd x && …`, a pipe, a redirect, `$(…)` or `xargs` confines the entire call again, so run the CLI as its own call and post-process its output in a second one. A credential or network failure from a chained call is the call's shape, not a broken sandbox config.
- Run `acli` as a standalone call before declaring it blocked. A real auth error means the user runs `acli jira auth login --web` in their own terminal, never a guess that the sandbox forbids it. A chained acli call is sandboxed, where its token refresh cannot write `~/.config/acli`, and from then on every call returns `unauthorized`; the `jira` skill's Auth check section has the detail.
