---
name: ship
description: Commit the working tree as strict conventional commits, push the branch, and open the PR (GitHub) or MR (GitLab) in one run, after a single confirmation. Use when the user asks to ship, or to commit and open a PR/MR. Trial replacement for /commit plus /pr.
argument-hint: "[guidance: scope, how to split, branch name, or base branch]"
model: haiku
effort: medium
allowed-tools:
  - Bash(python3 *skills/ship/scripts/context.py*)
  - Bash(python3 *skills/ship/scripts/apply.py *)
  - Bash(python3 *skills/diagram/scripts/diagrams.py scan*)
  - Bash(git push *)
  - Bash(git diff *)
  - Bash(git log *)
  - Bash(git status *)
  - Bash(gh pr checks *)
  - Bash(gh run view *)
  - Edit(//tmp/claude/**)
  - Edit(//private/tmp/claude/**)
  - Read
  - AskUserQuestion
---

# Ship

Turn the working tree into conventional commits, push the branch and open the PR/MR, then watch CI.
Everything before the confirmation gate is read-only; everything after it runs unattended through one script call.
Arguments, if any, are user guidance (a scope, how to split, a branch name, a base branch); factor them in before the gate.

Two bundled scripts do the mechanical work. Global install: `~/.claude/skills/ship/scripts/`; project install: `.claude/skills/ship/scripts/`.
Don't re-run git, gh or glab for anything their output already shows.

## The one confirmation

Whoever invoked this skill, the user or a model, nothing is committed, pushed or opened before the user answers the gate in step 4.
A model that loaded this skill on its own initiative asks there like everyone else: the gate *is* the confirmation, so never skip it and never ask a second time afterwards.
The `git-skill-gate` hook enforces the order: it lets `apply.py` run only once a human turn follows the invocation.

After that answer the run is unattended: no more questions, no "shall I push?", no pause between commit, push and PR.
The answer can be the structured option or plain prose: `go`, `continue`, `yes`, `ship it`, `dale`, `sí` or any other plain affirmative, in any language, means the first option of every question in the gate.
Prose that changes something (another base, another split, leave a file out) is a redirect: integrate it and ask the gate again.
`Cancel` or a refusal stops the run with nothing written.

## Steps

1. **Gather context** (single call): `python3 ~/.claude/skills/ship/scripts/context.py [<base>]`. Forward a bare base-branch argument when one was given.

   `== target ==` carries `HOST`, `BASE`, `BASE_REF`, `BRANCH`, `BRANCH_CONVENTION` (`ok`, `default` or `nonstandard`), `UPSTREAM`, `WORKTREE`, `UNPUSHED_COMMITS`, `PUSHED_COMMITS`, `TITLE`, `TICKET`, `TICKET_KIND`, and for GitLab `NS`, `GLHOST`, `REPO`, `GLHOST_CANDIDATES` or `NOT_LOGGED_IN`.
   Then the unpushed and pushed commit lists, the porcelain status, staged and unstaged stats and diffs (noisy paths excluded, capped per file), untracked previews, recent subjects, and the PR/MR template.
   Excluded or capped files still show in the stats: ship them with the concern they belong to, and only run `git diff -- <path>` when one genuinely matters.

   Stop with a one-line reason when `WORKTREE=clean` and `UNPUSHED_COMMITS=0` and `PUSHED_COMMITS=0`: there is nothing to ship.

   **Stale diagrams** (single call, skipped when the arguments say `skip diagrams`): `python3 ~/.claude/skills/diagram/scripts/diagrams.py scan --since <BASE_REF> --lint`.
   A missing script or `DIAGRAMS=0` means move on. A non-zero `STALE` or `LINT_ERRORS` count means diagrams rest on files this branch changes, or fail lint: list each as `<name> (<FILE>)` with its changed files or `lint:` lines, then one `AskUserQuestion`, `header: "Diagrams"`: "`<n>` diagrams are stale or fail lint. Refresh them first?". Options: `Refresh first` (stop the run with nothing written and say to run `/diagram refresh`, then `/ship` again), `Ship anyway` (continue; the PR description names the stale diagrams under a "Docs" line). This question comes before the gate, so a `go` at the gate still means ship.

2. **Decide the branch.**
   - `BRANCH_CONVENTION=ok` and the branch matches the work → `keep`, no question.
   - `default` → `create` (ships from the default branch are never allowed). Propose two names.
   - `nonstandard` → `rename`. Propose two names.
   - `ok` but plainly unrelated to the diff (a `chore/bump-*`, a release branch, someone else's feature) → propose two names for `create-from-base` and ask (see the gate).

   Names match `^(feature|fix|chore|docs|refactor|test|perf|ci|build|style|revert)\/([A-Z]+-[0-9]+-|gh-[0-9]+-)?[a-z0-9][a-z0-9-]*$`.
   The first candidate follows the dominant concern, the second a different framing (broader or narrower slug, or the other type when the diff is arguably either).
   A `feat` commit belongs on a `feature/` branch. Carry a ticket (`PROJ-123-<slug>` or `gh-456-<slug>`) only when the diff, the branch or the arguments name it: never invent one.
   The PR title is derived from the final branch name by `apply.py`, so the branch name is the title's wording: pick it accordingly.

3. **Draft the commits and the description.**
   - **Candidates**: every change in the status (staged, unstaged and untracked), except cleartext secrets (`.env`, `*.pem`, `*-key.json`, `credentials*`) and `.claude/tasks/`, which are left out and listed. Vault-encrypted files are fine.
   - **Concerns**: cluster files by intent, not directory. Separate a fix from an unrelated config tweak, a feature from a dep bump, a refactor from a doc update; keep a feature spanning ten files, a repo-wide rename, or a fix and its test together. Don't force a split on a cohesive diff. Order so each commit leaves the build green: config and deps first, features and fixes next, cosmetic cleanup last. `apply.py` stages whole files, so a file mixing concerns goes with its dominant one.
   - **Header**: `<type>(<scope>): <subject>`, at most 100 chars, imperative, lower-case start, no trailing period. Types: `feat | fix | chore | docs | refactor | test | perf | ci | build | style | revert` (`@commitlint/config-conventional`). Scope from the touched area (monorepo package, top-level directory, role name, feature area); omit it only when the change is genuinely repo-wide.
   - **Body**: only when the *why* isn't obvious from the subject. Short `-` bullets, no prose paragraphs.
   - **Description**: fill the template from `== template ==` (or a short what-and-why body when there is none). Free-text sections say what changed and why; check `[x]` only what the diff supports; pick type checkboxes from the commit prefixes, including the unpushed commits when they ship too. When `TICKET_KIND=github`, `apply.py` appends `Closes #<n>` if the body lacks it.
   - Humanize all of it (section below). Never write `Co-Authored-By: Claude …` or `🤖 Generated with …`: settings handle attribution and `apply.py` hard-blocks both.

4. **Confirmation gate** (mandatory, one `AskUserQuestion` call holding every question that applies, recommended option first).
   First print the plan: the branch (kept, created or renamed, and from where), each commit (number, header, files, body), files left out and why, the unpushed commits that would ship, and the base.
   Then ask, in this order:

   - Always, `header: "Ship"`: "Commit, push `<branch>` and open a PR against `<base>`?" (for GitLab name the account too). Options: `Go`; `Go, staged only` only when some changes are staged and others are not; `Cancel`.
   - When step 2 needs a name, `header: "Branch"`: the two candidates. `Other` covers a typed name; validate it against the regex and re-ask on failure.
   - When `UNPUSHED_COMMITS` > 0, `header: "Commits"`: "`<n>` commits on this branch are not pushed yet. Ship them too?" Options: `Ship them too` (they land in the PR), `Leave them out` (a new branch off `BASE_REF` with only the working-tree changes; name it in the option description from your candidates), `Cancel`. When the working tree is clean, leaving them out means nothing to ship: say so in that option's description.
   - When `GLHOST_CANDIDATES` is set, `header: "GitLab account"`: one option per candidate, labelled `<host> (<account>)`, the one matching `GIT_EMAIL` first. `NOT_LOGGED_IN` instead means leave `repo` out.

   Read the answer as `The one confirmation` describes. `Leave them out` turns the branch action into `create-from-base`; `Go, staged only` drops every unstaged and untracked file from the commits.

5. **Execute** (single call, no further questions). **Write** the description to `/tmp/claude/ship-body-<repo>-<suffix>.md` and the plan to `/tmp/claude/ship-plan-<repo>-<suffix>.json` (`<suffix>` random once per run). Never a HEREDOC: the harness escapes `!` and other shell-special characters, and the Write tool bypasses the shell.

   ```json
   {"branch": {"action": "keep", "name": "fix/gh-456-banner"},
    "commits": [{"files": ["src/a.ts", "src/a.test.ts"], "message": "fix(consent): keep banner state across reloads\n\n- why bullet"}],
    "pr": {"base": "main", "body_file": "/tmp/claude/ship-body-app-a1b2c3.md"}}
   ```

   `action` is `keep`, `create`, `create-from-base` or `rename`; `commits` is empty when the branch already holds the work; paths are relative to the repo root; `pr.repo` is GitLab only (`"gitlab.com-work/group/project"`).
   Then run `python3 ~/.claude/skills/ship/scripts/apply.py <plan path>`. It validates everything before the first write, switches or renames the branch, commits each entry in order, pushes with `-u`, then opens the PR/MR self-assigned to `@me`, or reuses the open one for the branch, and prints `Created: <url>` or `Updated: <url>`.

   When it fails, recover without asking as long as the approved scope (files, branch, base) stays the same:
   - A plan the validator rejects (a dash, an overlong header, a stray staged path) → fix the plan and rerun.
   - A push failing on auth or a pre-push hook that needs the network → it prints the standalone `git …` push. Run it verbatim as its own call, never chained, then rerun `apply.py <plan> --from pr`.
   - Commits landed but a later step failed → rerun with `--from push` or `--from pr`, never from the start.
   - A pre-commit or pre-push hook failing on the code itself (lint, types, tests) → surface the full output and stop: fixing the code is a new task. Never `--no-verify`, never `--amend`.

6. **Watch CI** (GitHub only, one call): `gh pr checks <url> --watch --fail-fast`. On a failure, name the failing check, pull its log with `gh run view <run-id> --log-failed | tail -n 80`, and report the cause. Skip on GitLab or when the repo has no checks.

7. **Report**: the `Created:` or `Updated:` line, the commits made, and the CI result. Nothing else.

## Humanization (required)

Every commit message, title and description reads like a teammate wrote it: specific, plain, honest.

- Plain verbs (*add, fix, remove, rename, move, drop, bump, split*). Be specific: `fix(checkout): handle empty cart on /checkout` beats `fix: bug in checkout`.
- Avoid *additionally, leverage, robust, seamless, comprehensive, holistic, delve, crucial, pivotal, key, vital, enhance, streamline, foster, empower, unlock* and their cousins.
- No em dashes, curly quotes, emojis, Title Case headings, or bold-header bullets.
- No negative parallelisms, tail "-ing" clauses ("…ensuring scalability"), forced rule-of-three, promotional adjectives, filler ("in order to"), stacked hedges, or upbeat endings.
- If something is incomplete, say so plainly ("doesn't cover the X case yet").

## Rules

- The PR title is derived, never written: `apply.py` builds it from the final branch name and the changed files (branch-type map, scope precedence, a Jira key as a `(<TICKET>)` suffix, a GitHub issue never in the title).
- Never stage a cleartext secret; when `git add` refuses an ignored file, never answer with `git add -f`.
- Never push the default branch, never force-push, never delete a branch: the hook and the deny list refuse them even here.
