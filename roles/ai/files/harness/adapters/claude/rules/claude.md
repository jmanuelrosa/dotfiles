# Claude Code mechanics

The settings, hooks, plan mode and sandbox behavior that no other agent has.
The tooling, code standards and git conventions are agent-neutral and live in `AGENTS.md`, which is what this machine's `~/.claude/CLAUDE.md` points at.

- Attribution is handled by the `attribution` setting in `settings.json`, which is why no `Co-Authored-By` or `🤖 Generated with` line is ever written by hand.
- Claude Code, the Agent SDK and the Anthropic API belong to the `claude-api` skill and the `claude-code-guide` agent, not to ctx7.

## Plan mode

- Plan mode writes through the `plansDirectory` setting in `settings.json`, which points at the repo's `docs/plans/`.
- Approved plans are date-prefixed to `YYYY-MM-DD-<slug>.md` by the `plan-date-stamp.sh` hook on `ExitPlanMode`, and they are committed. Don't rename one by hand, and don't write the date into the plan's own body: the filename carries it.

## Git & sandbox

- A hook enforces the `/commit` and `/pr` route, and `/pr` carries the only working push path.
- Only force-push, branch deletion, and lockfile writes are genuinely denied: hand the user the exact command instead of retrying.
- `acli` runs outside the sandbox. Run it before declaring it blocked. A real auth error means the user runs `acli jira auth login --web` in their own terminal, never a guess that the sandbox forbids it. But note that a session *can* lapse mid-run and stay lapsed: acli's token refresh writes `~/.config/acli`, which is denied, so once that write fails every later call returns `unauthorized`. Keep acli off the critical path of anything already half-done; the `jira` skill's Auth check section has the detail.
