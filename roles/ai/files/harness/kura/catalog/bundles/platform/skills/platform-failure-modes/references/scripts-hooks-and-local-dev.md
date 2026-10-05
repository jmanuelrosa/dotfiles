# Scripts, hooks, and local dev

When to read: the brief or diff touches shell scripts, pre-commit hooks, task runners, developer setup, or local-CI parity.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Shell without strictness.** A script without strict error handling marches past failures and reports only the last command's status; CI shows green over a half-executed script.
  Check: strict mode (`set -euo pipefail` or the shell's equivalent) at the top of every script, never assumed from the runner (CI shells routinely omit pipefail even when docs imply otherwise); multi-command pipeline steps live in scripts, not inline YAML strings.
- **Non-idempotent setup.** A bootstrap script that fails on rerun with already-exists errors trains people to stop running it.
  Check: every setup script converges: running it twice is safe and ends in the same state.
- **Hidden machine assumptions.** Absolute paths, assumed tool versions, and GNU-versus-BSD flag differences make a script work only on its author's machine.
  Check: tool versions come from the project's version pinning; paths are derived, not hardcoded; nothing depends on ambient host state (pre-installed tools, unpinned network fetches, remote scripts piped into a shell); the script runs on the platforms the team and CI actually use.
- **Hook slower than patience.** A pre-commit hook that takes tens of seconds gets bypassed with `--no-verify`, and then it protects nothing.
  Check: hooks run fast and only on the staged diff; anything slower moves to CI, where it cannot be skipped.
- **Hook-CI mismatch.** Hooks enforcing what CI does not, or the same linter at different versions, produce pass-locally-fail-in-CI and its reverse.
  Check: hooks and CI call the same script entry points at the same pinned versions; everything a hook enforces is also enforced in CI, because hooks are a courtesy and CI is the gate.
- **Second hook manager.** Adding a new hooks framework beside the existing one splits configuration and doubles the maintenance surface.
  Check: extend the hook manager the project already has.
- **Destructive convenience.** A clean or reset script that removes paths built from unset variables or user input will one day delete the wrong thing.
  Check: destructive operations guard their targets: unset variables fail, paths are validated, and anything not derived is confirmed.
- **Interactive steps in automation.** Prompts, TTY assumptions, and confirmation dialogs hang forever in a non-interactive runner.
  Check: scripts detect non-interactive execution and behave; CI invocations pass the non-interactive flags explicitly.

## Escalation triggers (`needs-decision`)

- A hook or script change that makes an existing gate optional or bypassable (also an ask-first boundary in the agent).
- Anything that requires developers to install new global tooling on their machines.

## What good looks like

- Every check runs identically through one script entry point: locally, in hooks, and in CI.
- Setup is one command, idempotent, and fast enough that nobody routes around it.
- Scripts fail loudly, early, and with the failing command visible.
