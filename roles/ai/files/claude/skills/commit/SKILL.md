---
name: commit
description: Stage changes, split the diff into atomic concerns when it makes sense, and write one strict conventional commit per concern. Stops at commit; does not push.
argument-hint: "[guidance: scope, how to split, or branch name]"
disable-model-invocation: true
allowed-tools:
  - Bash(git status *)
  - Bash(git diff *)
  - Bash(git add *)
  - Bash(git commit *)
  - Bash(git log *)
  - Bash(git branch *)
  - Bash(git switch *)
  - Bash(git remote *)
  - Bash(git symbolic-ref *)
  - Write(/tmp/claude/**)
  - AskUserQuestion
---

# Create commit(s)

Inspect the working tree, confirm the branch is one the user will commit on, split the diff into atomic concerns, draft a strict conventional commit per concern, get approval, and commit each in order. Never push, never open a PR: that is `/pr`'s job.

Arguments, if any, are user guidance: a scope, how to split concerns, or a branch name. Factor them into the plan before the approval gate.

## Steps

1. **Resolve base and current branch:**
   ```sh
   BASE=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##')
   BRANCH=$(git branch --show-current)
   ```
   If `BASE` is empty, `origin/HEAD` is unset. Populate it once with `git remote set-head origin -a` (plain git, works on any host), then re-read. With no `origin` remote at all, `BASE` stays empty: skip the default-branch comparison in Step 2 and treat the current branch as the working branch.

2. **Branch gate:**
   - `BRANCH` == `BASE` (on the default branch) → **ask**: commit into `$BASE`, or create a new branch?
     - Into `$BASE` (common for personal repos) → proceed.
     - New branch → ask for the name (don't propose one) and validate against:
       ```
       ^(feature|fix|chore|docs|refactor|test|perf|ci|build|style|revert)\/([A-Z]+-[0-9]+-)?[a-z0-9][a-z0-9-]*$
       ```
       Passing: `feature/add-oauth`, `fix/PROJ-123-login-redirect`, `chore/bump-deps`. The Jira ticket is embedded with a dash (`PROJ-123-<slug>`), not a separate segment. On failure, show why and re-ask. Create with `git switch -c "$NEW_BRANCH"`.
   - `BRANCH` is a non-default branch:
     - Matches the work at hand (named for this change, or the user pointed you at it) → use it, no prompt.
     - Looks unrelated to the diff (a `chore/bump-*`, a release branch, someone else's feature branch) → **ask** before reusing it; on "new branch", follow the same name prompt + validation.

3. **Staging gate.** Run `git status --porcelain=v1`. If nothing is staged or unstaged → stop ("no changes to commit"). Otherwise the candidate is the *staged* set; if there are unstaged changes not already staged, **ask** whether to fold them in (stage all, pick a subset, or leave out) and print what's left out. If leaving out empties the candidate set (nothing was staged), that's a cancel: stop with "no changes to commit". Never auto-stage.

4. **Concern analysis**: decide how many commits.
   - **Read the candidate diff** (`git diff --cached` if staged, else `git diff HEAD`). For the *drafting view only*, exclude noisy paths that add no signal:
     ```
     **/package-lock.json, **/yarn.lock, **/pnpm-lock.yaml, **/bun.lock*,
     **/*.min.js, **/*.min.css, **/*.map,
     **/dist/**, **/build/**, **/.next/**, **/node_modules/**,
     **/*.generated.*, **/*_generated.*, **/*.pb.ts
     ```
     They still show in `--stat`, so commit them with the concern they belong to and mention them in the body if useful.
   - **Cluster files into concerns by intent, not directory.** A concern is a self-contained change with one purpose.
     - Separate: a fix + an unrelated config tweak; a feature + a dep bump; a refactor + a doc update.
     - Same: a feature spanning N files; a rename across the repo; a fix and its test.
   - **Order** so each commit leaves the build green: config / deps first, then features and fixes, cosmetic / cleanup last.
   - **Hunk-level splits**: if one file mixes concerns, plan `git add -p <file>` and note it in the plan.
   - **Don't force a split** when the diff is cohesive: one feature touching ten files is one commit.

5. **Draft the plan**: one entry per concern.
   - **Header**: `<type>(<scope>): <subject>`, ≤ 100 chars, imperative, no leading capital, no trailing period. Types: `feat | fix | chore | docs | refactor | test | perf | ci | build | style | revert`. Derive scope from the touched area (monorepo package, top-level directory, role name in this dotfiles repo, feature area like `auth`/`api`); omit `(<scope>)` only when genuinely repo-wide, and surface the doubt at the gate if unclear.
   - **Body**: only when the *why* isn't obvious from the subject. Blank line after subject, wrap at 100 cols, short `-` bullets, no prose paragraphs. Skip rather than pad.
   - **Never** write `Co-Authored-By: Claude …` or `🤖 Generated with …`. Attribution is handled by the `attribution` setting in `settings.json`; duplicating it in the message body produces the trailer even when attribution is configured to be empty. The `git-skill-gate` hook hard-blocks messages containing these lines.

6. **Humanize**: plain verbs (*add, fix, remove, rename, move, drop, bump, split*), no AI vocabulary (*leverage, robust, seamless, comprehensive, enhance, streamline, foster*), no promotional tone, no em dashes between clauses, no emojis. Be specific: `fix(checkout): handle empty cart on /checkout` beats `fix: bug in checkout`.

7. **Approval gate** (mandatory). Print the plan (per commit: number, subject, file group, any folded-in noisy files, body). Then call `AskUserQuestion`:
   - `question: "Proceed with these commits?"`, `header: "Commit plan"`, `multiSelect: false`
   - options: `Go` (commit each entry in order), `Cancel` (stop, commit nothing, unstage nothing).
   - The structured question *is* the gate: don't wait for prose like `go` / `lgtm` / `ok`. Free-form confirmations between the plan and the commits break `attributionSkill` in the transcript and cause `git-skill-gate.sh` to block.
   - On `Other`, integrate the redirect ("change commit 2's scope", "split commit 1", "drop the last"), replan from concern analysis if needed, and re-run this gate.

8. **Commit each concern in order:**
   - **Stage** exactly its file group with `git add <files>`, or `git add -p <file>` for hunk splits.
   - **Commit**: write the full message (subject, blank line, body when present) with the **Write tool** to a message file unique to this session: `/tmp/claude/commit-msg-<repo>-<suffix>.txt`, where `<suffix>` is a short random string picked once per run. Concurrent sessions share `/tmp/claude/`, so a fixed filename lets another session's message land between your Write and your commit. Then:
     ```sh
     git commit -F /tmp/claude/commit-msg-<repo>-<suffix>.txt
     ```
     Applies to every commit, single-line included: never inline `-m` and never a HEREDOC. The harness escapes `!` and other shell-special characters before the shell runs, so subjects like `feat(api)!: drop v1` pick up stray backslashes on both paths; the Write tool bypasses the shell entirely. Overwrite the same file for each commit in the loop.
   - **Never** `--no-verify`. On a pre-commit hook failure, surface the full output and stop the loop: don't retry, don't start the next commit until it's resolved.
   - **Never** `--amend` unless the user explicitly typed the word "amend".
   - After the loop, print `git log -n <count> --pretty='%h %s'`.

## Rules

- Subject prefixes follow `@commitlint/config-conventional` (`feat`, not `feature`; lower-case type and scope; non-empty type + subject; no trailing full-stop; header ≤ 100). Branch prefixes use the distinct Conventional Branch set (`feature`, not `feat`): the Step 2 regex.
- Never stage *cleartext* secrets (`.env`, `*.pem`, `*-key.json`, `credentials*`): warn and exclude by default. Vault-encrypted files (e.g. `vars/secrets.yml`) are meant to be committed and are fine.
- Never stage local-only Claude state, `.claude/tasks/` above all: the `git-skill-gate` hook hard-blocks it, so exclude it at staging.
- Use `git switch` for branch creation, not `git checkout -b`.
