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

- A hook enforces the `/commit`, `/pr` and `/ship` route, and `/pr` and `/ship` carry the only working push path. `/ship` is model-invocable, so the hook opens it only once a human turn follows its invocation.
- Force-push, branch deletion, a push to the default branch, and lockfile writes remain denied even inside `/pr`.
- Every command remains sandboxed, including approved skill scripts and standalone CLIs: `sandbox.excludedCommands` is empty and `allowUnsandboxedCommands` is false.
- Skill approval does not grant access to blocked credentials, protected Git metadata, or disallowed network destinations. Report the actual failure and let the user run the approved operation from their own terminal; do not add exclusions, widen credential access, or retry through another command shape.
- Authentication and token refresh belong in the user's terminal. A standalone or chained `acli` call has the same sandbox restrictions.
