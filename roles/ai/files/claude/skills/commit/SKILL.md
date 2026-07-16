---
name: commit
description: Stage changes, split the diff into atomic concerns when it makes sense, and write one strict conventional commit per concern. Stops at commit; does not push.
argument-hint: "[guidance: scope, how to split, or branch name]"
model: sonnet
disable-model-invocation: true
allowed-tools:
  - Bash(git status *)
  - Bash(git diff *)
  - Bash(git add *)
  - Bash(git commit *)
  - Bash(git log *)
  - Bash(git branch *)
  - Bash(git switch *)
  - Bash(bash *skills/commit/scripts/context.sh)
  - Bash(python3 *skills/commit/scripts/apply.py *)
  - Write(//tmp/claude/**)
  - Write(//private/tmp/claude/**)
  - AskUserQuestion
---

# Create commit(s)

Inspect the working tree, confirm the branch, split the diff into atomic concerns, draft a strict conventional commit per concern, get approval, and commit each in order. Never push, never open a PR: that is `/pr`'s job. Arguments, if any, are user guidance (a scope, how to split, a branch name); factor them in before the approval gate.

Two bundled scripts do the mechanical work in one call each; don't re-run git for anything their output already shows. Global install: `~/.claude/skills/commit/scripts/`; project install: `.claude/skills/commit/scripts/`.

## Steps

1. **Gather context** (single call): `bash ~/.claude/skills/commit/scripts/context.sh`. It prints `BASE`/`BRANCH`, porcelain status, staged + unstaged stats, drafting diffs (noisy paths like lockfiles/minified/generated excluded, capped per file), untracked previews, and recent subjects. Excluded or capped files still show in the stats: commit them with the concern they belong to; only run `git diff -- <path>` when a capped file genuinely matters for clustering. `BASE=<none: no origin>` means skip the default-branch comparison and treat the current branch as the working branch.

2. **Branch gate:**
   - `BRANCH` == `BASE` (on the default branch) → **ask**: commit into `$BASE`, or create a new branch?
     - Into `$BASE` (common for personal repos) → proceed.
     - New branch → ask for the name (don't propose one) and validate against:
       ```
       ^(feature|fix|chore|docs|refactor|test|perf|ci|build|style|revert)\/([A-Z]+-[0-9]+-)?[a-z0-9][a-z0-9-]*$
       ```
       The Jira ticket is embedded with a dash (`PROJ-123-<slug>`), not a separate segment. On failure, show why and re-ask. Create with `git switch -c "$NEW_BRANCH"`.
   - Non-default branch that matches the work at hand → use it, no prompt. Looks unrelated to the diff (a `chore/bump-*`, a release branch, someone else's feature) → **ask** before reusing it; on "new branch", same name prompt + validation.

3. **Staging gate.** From the status section: nothing staged or unstaged → stop ("no changes to commit"). Otherwise the candidate is the *staged* set; if there are unstaged changes not already staged, **ask** whether to fold them in (all, a subset, or leave out) and print what's left out. If that empties the candidate set, stop with "no changes to commit". Never auto-stage.

4. **Concern analysis**: cluster files into concerns by intent, not directory; a concern is a self-contained change with one purpose.
   - Separate: a fix + an unrelated config tweak; a feature + a dep bump; a refactor + a doc update.
   - Same: a feature spanning N files; a rename across the repo; a fix and its test.
   - **Order** so each commit leaves the build green: config/deps first, features and fixes next, cosmetic/cleanup last.
   - If one file mixes concerns, plan a hunk split (`git add -p <file>`) and note it in the plan.
   - **Don't force a split** when the diff is cohesive: one feature touching ten files is one commit.

5. **Draft the plan**: one entry per concern.
   - **Header**: `<type>(<scope>): <subject>`, ≤ 100 chars, imperative, no leading capital, no trailing period. Types: `feat | fix | chore | docs | refactor | test | perf | ci | build | style | revert`. Derive scope from the touched area (monorepo package, top-level directory, role name in this dotfiles repo, feature area); omit `(<scope>)` only when genuinely repo-wide, and surface the doubt at the gate if unclear.
   - **Body**: only when the *why* isn't obvious from the subject. Blank line after subject, short `-` bullets, no prose paragraphs. Skip rather than pad.
   - **Never** write `Co-Authored-By: Claude …` or `🤖 Generated with …`: `settings.json` handles attribution and both the `git-skill-gate` hook and `apply.py` hard-block these lines.

6. **Humanize**: plain verbs (*add, fix, remove, rename, move, drop, bump, split*), no AI vocabulary (*leverage, robust, seamless, comprehensive, enhance, streamline, foster*), no promotional tone, no em dashes, no emojis. Be specific: `fix(checkout): handle empty cart on /checkout` beats `fix: bug in checkout`.

7. **Approval gate** (mandatory). Print the plan (per commit: number, subject, file group, any folded-in noisy files, body). Then call `AskUserQuestion`:
   - `question: "Proceed with these commits?"`, `header: "Commit plan"`, `multiSelect: false`
   - options: `Go` (commit each entry in order), `Cancel` (stop, commit nothing, unstage nothing).
   - The structured question *is* the gate: don't wait for prose like `go` / `lgtm` (free-form confirmations break the `git-skill-gate` hook).
   - On `Other`, integrate the redirect, replan from concern analysis if needed, and re-run this gate.

8. **Execute** (single call after Go). **Write** the approved plan to `/tmp/claude/commit-plan-<repo>-<suffix>.json` (`<suffix>` random once per run; `/tmp/claude/` is shared across sessions):
   ```json
   {"commits": [{"files": ["src/a.ts", "src/b.ts"], "message": "feat(x): subject\n\n- why bullet"}]}
   ```
   Newlines inside `message` are `\n` escapes; keep entries in plan order. Then run `python3 ~/.claude/skills/commit/scripts/apply.py <plan path>`. It validates every entry up front (attribution lines, em/en dashes, `.claude/tasks/`, secret-looking files, header length), then stages each file group and commits it with `-F`, stops on the first failure leaving that group staged, and prints the final log.
   - **Hunk splits**: `apply.py` stages whole files only. Commit a mixed-concern entry manually instead: `git add -p <file>`, **Write** the message to `/tmp/claude/commit-msg-<repo>-<suffix>.txt`, then `git commit -F <that file>`. Never inline `-m` and never a HEREDOC (the harness escapes `!` and other shell-special chars; the Write tool bypasses the shell).
   - **Never** `--no-verify`. On a pre-commit hook failure, surface the full output and stop: don't retry, don't continue until it's resolved.
   - **Never** `--amend` unless the user explicitly typed the word "amend".

## Rules

- Subject prefixes follow `@commitlint/config-conventional` (`feat`, not `feature`; lower-case type and scope; non-empty type + subject; no trailing full-stop; header ≤ 100).
- Never stage *cleartext* secrets (`.env`, `*.pem`, `*-key.json`, `credentials*`): warn and exclude by default. Vault-encrypted files (e.g. `vars/secrets.yml`) are meant to be committed and are fine.
- Never stage local-only Claude state (`.claude/tasks/` above all; hook and `apply.py` both hard-block it).
