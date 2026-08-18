# Continuing the pi/Claude parity handoff: review PR #71

## Context

The prior session's handoff (`/tmp/handoff-dotfiles-pi-settings-2026-08-18.md`) described `feature/pi-settings` as fully committed but unpushed, with `make lint`/`make syntax` still needing to be run by hand, and suggested a `/code-review` pass before `/pr`.

Direct verification this session found the handoff is stale on two points:

- **The branch is already pushed and PR #71 (`feat: pi settings`) is open**, `MERGEABLE`, tracking `origin/feature/pi-settings` with zero divergence (`eb5a08a`, same as local `HEAD`).
- **CI already ran and passed** `ansible-lint`, `ansible-playbook --syntax-check` for both `personal` and `work` profiles, the python/fish test suite, gitleaks, and Socket's two checks. `make lint` and `make syntax` in the Makefile shell out to the exact same commands CI runs (confirmed by reading both), so the handoff's step 1 ("must be run by hand before anything ships") is already satisfied through CI, not still outstanding.

What's confirmed still genuinely outstanding, from direct machine inspection (all read-only checks, no mutation performed):

- `~/.pi/agent/settings.json` is still a symlink into the **old** `~/Developer/dotfiles` checkout and still fails to parse (`json.decoder.JSONDecodeError: Illegal trailing comma ... line 23`).
- `~/.pi/agent/npm/node_modules/@tintinweb/` is empty, so `pi-subagents` is not installed.
- `~/.pi/agent/SYSTEM.md` is still a live symlink into the old checkout (the exact case the removal task exists to clear).
- `herdr integration status` already reports `pi: current (v8)`, but by hand-install, not through this role (matches the plan's own note that this was installed by hand).
- PR #71 has **zero reviews**.

Per your decisions just now: skip applying the role locally this session (needs your vault + become password interactively, out of scope here), skip building new `pi -p` smoke-test tooling, and run a `/code-review` pass on PR #71 now, since none has happened yet and the handoff itself called for one before merge.

## What this session will do

Run a structured review of PR #71's full diff (`git diff main...feature/pi-settings` scope, i.e. everything in the 7 commits `639a51a`..`eb5a08a`) against this repo's code review policy (`roles/ai/files/claude/rules/code-review.md`, detailed in `docs/internals/code-review-policy.md`):

1. Load the `review-mechanics` skill (mandatory before producing the actual report, per the code-review policy) and let it drive verification bar, effort level, and report format.
2. Review is read-only: no edits, no commits, no `/pr` actions. Findings only.
3. Score against the eight axes in order (correctness, contract/compatibility, security/privacy, failure visibility, test adequacy, performance, convention/repo fit, simplification), using the four-word severity vocabulary (`blocker`/`important`/`nit`/`pre-existing`).
4. Focus areas worth deliberate attention, based on what this session already read in the diff's own design docs:
   - `guardrails.ts`'s fail-open behavior when translating Claude's `PreToolUse` hooks for pi's `tool_call` event: a change here has real correctness/security stakes (a broken translation either blocks all pi tool calls or silently lets dangerous ones through).
   - `pi_trust.py` and the two-store trust model (cwd-realpathed vs. git-root, nearest-wins vs. walk-past-false): subtle enough to be worth a second pass on the derivation logic.
   - `test_pi_sandbox.py` and `files/pi/sandbox.json`'s regeneration/drift check: confirm the test actually fails on drift rather than just re-asserting the current file.
   - `restore.py`/`adopt.py`'s newly added pi convergence calls: confirm they're reached on the actual code paths the fix commit claims (early-return ordering was exactly the bug being fixed).
   - Cap nits at 3, zero if a blocker surfaces, per policy.
5. Report the review findings directly in this session (not filed anywhere), organized by severity, so you can decide what blocks merge vs. what to file for later.

## Also flagged, not actioned (per your "skip for now" answers)

- `make check-role ROLE=ai` / `make run-role ROLE=ai` still needs to be run by you locally (vault + become password) to fix the live `~/.pi/agent/settings.json`, install `pi-subagents`, and clear the stale `SYSTEM.md` symlink. Verification afterward: `pi config` starts clean, `~/.pi/agent/npm/node_modules/@tintinweb/pi-subagents` exists, `herdr integration status` still shows `pi: current` (now role-managed).
- Interactive pi-session checks (skill `allowed-tools` ignored but sandbox constrains; a mutating cloud CLI command refused; `/review` reflecting the four-severity vocabulary) remain manual, exercised in a real pi session once the settings fix above lands.
- The pre-existing, unrelated bug flagged in the plan's "Out of scope" section: 12 symlinks under `.claude/skills/` (this project's own dev-tooling links, e.g. `.claude/skills/node`, `.claude/skills/cloud`) hold **absolute** paths into `~/Developer/dotfiles/...` rather than this checkout, and are committed to git despite the documented design that project-level `claude-kit` symlinks are never committed. Confirmed still present, most recently touched in merged PR #76 (`chore: addyosmani skills`, Aug 17), so it's an actively-maintained pattern, not a one-off. Root cause: `claude_kit/paths.py:repo_root()` derives from `Path(__file__).resolve()`, which follows the `claude-kit` binary's symlink chain back to whichever checkout last had its `ai` role applied (`~/Developer/dotfiles`), regardless of the cwd a command was run from. Fix sketch for a future, separate change: add `.claude/skills/` (or just its symlink entries) to `.gitignore`, `git rm --cached` the 12 committed links, and let `claude-kit add`/sync regenerate them locally, uncommitted, once the role has been applied from the correct checkout. Not part of this session's scope.

## Verification

No code changes in this session, so no build/test verification applies. The deliverable is the review report itself; its own "verification" is the policy's own bar (every finding cites a concrete failure scenario, nothing asserted about behavior that wasn't actually read).
