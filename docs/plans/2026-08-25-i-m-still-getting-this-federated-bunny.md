# Let pi commit inside a linked worktree

## Context

`/skill:commit` fails in pi with what looks like a guardrail refusal.
It is not one.

Traced through the pi session at `~/.pi/agent/sessions/--Users-jmanuelrosa-Developer-work-didomi-partner-portal-SER-1242--/2026-08-25T05-07-55-868Z_*.jsonl`:

- **The skill gate already works.** Three separate `pi__bash` runs of `~/.claude/skills/commit/scripts/apply.py` passed `git-skill-gate.sh` and reached `git add`. `<skill name="commit" …>` was present on the invoking user message, `activeSkills` in [guardrails.ts](../../roles/ai/files/pi/extensions/guardrails.ts) matched it, and the hook allowed the wrapper. Nothing about `/skill:commit` needs supporting; it is supported.
- **pi's sandbox is what blocked the commit.** Every one of those runs died with `fatal: Unable to create '/Users/…/partner-portal/spa/.git/worktrees/SER-1242/index.lock': Operation not permitted`. `SER-1242` is a linked worktree: its gitdir lives under the main checkout's `.git`, which is a *sibling* of cwd. [sandbox.json](../../roles/ai/files/pi/sandbox.json) grants `allowWrite: ["."]`, so every git write in a linked worktree is denied: not just `commit`, but `add`, `switch` and `stash` too.
- **Claude Code never hits this** because `sandbox.excludedCommands` in [settings.json](../../roles/ai/files/claude/settings.json) lists `git`, which runs it outside the sandbox entirely. pi-sandbox has no per-command exclusion, so the confinement is real there and only there.
- The `Cursor's PreToolUse hook rejects git commit` line in the failure report came from a **Cursor Shell subagent**, not from pi's bridge: its quoted hook text lacks the `In pi those skills are /skill:commit and /skill:pr` line `blockResult` appends to every refusal guardrails.ts returns. That path is Cursor-side, it also returned `Cursor shell did not complete / missing completion` (already recorded at [pi-harness.md](../internals/pi-harness.md)), and it is out of scope here. The `pi__*` preference rule in `APPEND_SYSTEM.md` is the existing mitigation.

Intended outcome: a worktree created by `wt add` can run the full `/skill:commit` flow under pi's sandbox, without widening write access to anything beyond the repository that worktree belongs to.

## Approach

`wt add` writes a project-scoped pi-sandbox config into the new worktree, naming that repo's git common directory and nothing else.

pi-sandbox reads `<cwd>/.pi/sandbox.json` alongside the global `~/.pi/agent/sandbox.json` and **unions the path arrays** (`mergeConfigLayers` / `mergeStringArrays` in the package's `src/config.ts`), so the project file adds a grant without restating the global one. Non-glob `allowWrite` entries are prefix-matched (`matchesPattern` in `src/policy.ts`), so a single entry for the common dir covers `worktrees/<name>/index.lock`, refs, objects and logs. Write access implies read access, so no `allowRead` entry is needed.

### Files

**[roles/shell/files/fish/functions/wt.fish](../../roles/shell/files/fish/functions/wt.fish)**

Add a helper beside `_wt_in_herdr`, and call it from `_wt_add` in the block that already copies `.env*`, `.vscode/` and `.claude/` into the new worktree (around lines 107-120), before the lockfile install.

The helper, given the new worktree path:

1. Reads the common dir with `git -C $target rev-parse --git-common-dir`. For a linked worktree this is absolute (`/…/partner-portal/spa/.git`); for a plain checkout it is the relative `.git`.
2. Returns without writing anything when that path resolves inside `$target`. A worktree whose gitdir is its own `.git` is already covered by the global `.` grant, and a file there would be noise.
3. Writes `$target/.pi/sandbox.json`:

   ```json
   {
     "filesystem": {
       "allowWrite": ["<absolute git common dir>"]
     }
   }
   ```

4. Writes `$target/.pi/.gitignore` holding `.gitignore` and `sandbox.json`, one per line. The file names itself because a `.gitignore` is not matched by its own patterns; this is the same containment `claude_kit/pi.py` uses for `.agents/` (see its `IGNORE` constant and the comment above it), and it keeps the grant out of the repo's history without touching the repo's own `.gitignore`.
5. Reports through `_ui step` in the same voice as the copies above it, per [Script output style](../internals/script-output-style.md).

Idempotency: the helper overwrites both files unconditionally. `wt add` refuses an existing target, so it only ever writes into a directory it just created.

**[roles/shell/README.md](../../roles/shell/README.md)**: extend the `wt add` description with the `.pi/sandbox.json` write and why it exists.

**[docs/internals/pi-harness.md](../internals/pi-harness.md)**: in the "Permissions and the sandbox" section, record the asymmetry the derivation cannot express. Claude's `excludedCommands` runs `git` unsandboxed, pi-sandbox has no per-command exclusion, so a linked worktree's gitdir falls outside `allowWrite: ["."]` and needs the per-worktree grant `wt add` now writes.

### Worktrees that already exist

Out of scope for the change, and there is already a first-class path: inside the worktree, run `/sandbox-allow write <common gitdir>` in pi and choose **Allow for this project**, which writes the same `.pi/sandbox.json`. Note it in the README line so it is discoverable. Recreating the worktree through `wt add` also works.

## Verification

1. `make test`: unchanged suites must stay green. No fish function has a suite, so this only proves nothing else broke.
2. Create a scratch worktree and inspect the artifacts:
   - `cd` into any repo, `wt add sandbox-probe`
   - `cat ../sandbox-probe/.pi/sandbox.json` matches `git rev-parse --git-common-dir` resolved to an absolute path
   - `git -C ../sandbox-probe status --porcelain` is empty: the `.pi/` directory is invisible to git
3. End to end, which is the actual bug: `pi` inside the new worktree, make a trivial edit, `/skill:commit`, approve. `apply.py` must complete and `git log -1` must show the new commit. Before the change this fails at `git add` with `Unable to create … index.lock: Operation not permitted`.
4. Confirm the narrow grant held: in the same session, `/sandbox` shows the merged config with only that repo's `.git` added, and a write to an unrelated sibling repo is still refused.
5. Confirm a plain (non-worktree) checkout is untouched: `wt` is not involved, no `.pi/` appears, and committing under pi still works as before.
