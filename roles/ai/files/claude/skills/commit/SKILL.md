---
name: commit
description: Stage changes, split the diff into atomic concerns when it makes sense, and write one strict conventional commit per concern. Stops at commit — does not push.
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
  - Bash(gh repo view *)
  - Bash(glab repo view *)
  - AskUserQuestion
---

# Create commit(s)

Inspect the working tree, ensure we're on a branch the user is willing to commit on, split the diff into atomic concerns, draft a strict conventional commit message per concern, confirm the plan with the user, and commit each one in order. Never push, never open a PR — that is `/pr`'s job.

If invoked with arguments, treat them as user guidance — a desired scope, how to split concerns, or a branch name — and factor them into the plan before the approval gate.

## Steps

1. **Detect host and default branch**. Bootstrap from the local remote URL, then ask the host CLI:
   ```sh
   REMOTE=$(git remote get-url origin 2>/dev/null) || { echo "No origin remote"; exit 1; }
   case "$REMOTE" in
     *github*) HOST=gh ;;
     *gitlab*) HOST=glab ;;
     *) echo "Unsupported remote host: $REMOTE"; exit 1 ;;
   esac

   if [ "$HOST" = gh ]; then
     BASE=$(gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name' 2>/dev/null)
   else
     BASE=$(glab repo view -F json 2>/dev/null | jq -r '.default_branch')
   fi
   [ -z "$BASE" ] || [ "$BASE" = "null" ] && { echo "Could not determine default branch via $HOST"; exit 1; }

   BRANCH=$(git branch --show-current)
   ```
   Rule: use `gh` / `glab` wherever they have an equivalent. Fall back to `git` only for operations they don't cover (commit, push, diff, status, switch, log).

2. **Branch gate**:
   - If `BRANCH` equals `BASE` (i.e. on the default branch) → **stop and ask the user**: commit directly into `$BASE`, or create a new branch?
     - If the user confirms committing into `$BASE` (common for personal repos), proceed on the base branch.
     - If the user wants a new branch, ask for the name (do not propose one) and validate against:
       ```
       ^(feature|fix|chore|docs|refactor|test|perf|ci|build|style|revert)\/([A-Z]+-[0-9]+-)?[a-z0-9][a-z0-9-]*$
       ```
       Examples that pass: `feature/add-oauth`, `fix/PROJ-123-login-redirect`, `chore/bump-deps`, `refactor/PROJ-9-extract-cart-helper`. The Jira ticket is embedded with a dash (`PROJ-123-<slug>`), not a separate path segment. If the answer fails validation, show the failure reason and ask again. Create and switch with `git switch -c "$NEW_BRANCH"`.
   - If `BRANCH` is already a non-default branch → use it, no prompt.

3. **Staging gate**:
   - Run `git status --porcelain=v1`. Group output into *staged* (`M `, `A `, `D `, `R `, …) and *unstaged* (` M`, ` D`, `??`).
   - Cases:
     - **Nothing staged, nothing unstaged** → stop: "no changes to commit".
     - **Something staged, nothing unstaged** → proceed with the staged set as the candidate.
     - **Nothing staged, something unstaged** → ask the user: "stage all (`git add -A`), pick a subset, or cancel?". Default to *ask*; never auto-stage.
     - **Both staged and unstaged** → ask whether the unstaged should be folded in. If not, proceed with the *staged* set only and print which files are being left out.

4. **Concern analysis** — decide how many commits.
   - **Read the candidate diff** (`git diff --cached` if staged, else `git diff HEAD`). For the *message-drafting view*, exclude noisy paths whose contents add no signal:
     ```
     **/package-lock.json, **/yarn.lock, **/pnpm-lock.yaml, **/bun.lock*,
     **/*.min.js, **/*.min.css, **/*.map,
     **/dist/**, **/build/**, **/.next/**, **/node_modules/**,
     **/*.generated.*, **/*_generated.*, **/*.pb.ts
     ```
     These files still appear in `--stat`, so include them in the commit they belong to and mention them in the body if useful.
   - **Identify logical concerns.** A logical concern is a self-contained change with a single purpose. Cluster files into concerns by *intent*, not by directory.
     - **Separate concerns**: a bug fix + an unrelated config tweak; a feature + a dependency bump; a refactor + a doc update; secrets rework + a cosmetic UI change.
     - **Same concern**: a feature spanning N files; a refactor that renames a symbol across the repo; a fix and its test.
   - **Order commits** so each one leaves the build green on its own: infrastructure / config / deps first, then features and fixes, then cosmetic / cleanup last.
   - **Hunk-level splits**: if a single file mixes concerns, plan to stage hunks with `git add -p <file>` (interactive). Note this in the plan so the user knows it'll require hunk picking.
   - **Don't force a split** when the diff is genuinely cohesive — one feature touching ten files is still one commit.

5. **Draft the plan** — one entry per concern.
   - **Header**: `<type>(<scope>): <subject>`. The whole header line ≤ 100 chars (commitlint `header-max-length`), imperative mood, no leading capital / sentence-case subject (`subject-case`), no trailing period (`subject-full-stop`). Types: `feat | fix | chore | docs | refactor | test | perf | ci | build | style | revert`. Derive scope from the touched area (monorepo package, top-level directory, role name in this dotfiles repo, feature area like `auth`/`api`). Omit `(<scope>)` only when the change is genuinely repo-wide; if unclear, surface it in the approval gate and ask.
   - **Body**: only when the *why* isn't obvious from the subject. Blank line after the subject, wrap at 100 cols (commitlint `body-max-line-length`), short `-` bullets, no prose paragraphs. Skip rather than pad.
   - **Never** write `Co-Authored-By: Claude …` or `🤖 Generated with …` lines. Attribution is handled by Claude Code's `attribution` setting in `settings.json`.

6. **Humanize** — plain verbs (*add, fix, remove, rename, move, drop, bump, split*), no AI vocabulary (*leverage, robust, seamless, comprehensive, enhance, streamline, foster*), no promotional tone, no em dashes between clauses, no emojis. Be specific: `fix(checkout): handle empty cart on /checkout` beats `fix: bug in checkout`.

7. **Approval gate** (mandatory):
   - Print the plan: for each commit, show its number, subject, file group (and any noisy files folded in), and body if any. For a single-concern diff, this is one entry.
   - Then call `AskUserQuestion` to collect the approval. Use:
     - `question: "Proceed with these commits?"`
     - `header: "Commit plan"`
     - `multiSelect: false`
     - `options`:
       - `Go` — commit each entry in the plan, in order.
       - `Cancel` — stop without committing.
   - Do not wait for prose like `go` / `lgtm` / `ok` — the structured question is the gate. Free-form prose confirmations between the plan and the commits break `attributionSkill` in the transcript and cause `git-skill-gate.sh` to block.
   - The auto-provided `Other` option lets the user redirect ("change commit 2's scope to `auth`", "split commit 1", "drop the last commit"). On `Other`, integrate the feedback, replan from concern analysis if needed, and re-run this approval gate.
   - On `Cancel`, stop. Do not commit, do not unstage.
   - Never auto-commit, even in auto mode.

8. **Commit each concern in order**:
   - For each entry in the approved plan:
     - **Stage** exactly its file group with `git add <files>`, or `git add -p <file>` for hunk-level splits.
     - **Commit**:
       - Single-line message: `git commit -m "<subject>"`.
       - Multi-line message: HEREDOC, never `-m` chains.
         ```sh
         git commit -m "$(cat <<'EOF'
         <subject>

         <body>
         EOF
         )"
         ```
     - **Never** `--no-verify`. If a pre-commit hook fails, surface the full failure output and stop the whole loop. Do not retry with `--no-verify`. Do not start the next commit until the failure is resolved.
     - **Never** `--amend` unless the user explicitly typed the word "amend".
   - After the loop, print `git log -n <count> --pretty='%h %s'` so the user can see all the recorded subjects.

## Rules

- Stops at `git commit`. Do not push. Do not open a PR. `/pr` handles both.
- Branch names must match the regex in Step 2. Commit subject prefixes use the Conventional Commits set (`feat`, not `feature`); branch prefixes use the Conventional Branch set (`feature`, not `feat`).
- These rules mirror `@commitlint/config-conventional`: the type-enum above, lower-case type and scope, non-empty type + subject, no trailing full-stop, header ≤ 100. The branch-name regex (Step 2) is the separate Conventional Branch set, intentionally distinct.
- **One concern → one commit. Many concerns → many commits.** Don't force a split when the diff is cohesive; don't bundle when it isn't.
- Each commit must be self-contained: it should compile, lint, and ideally pass tests on its own. Order accordingly (config/deps first, features next, cleanup last).
- Do not stage files that look like *cleartext* secrets (`.env`, `*.pem`, `*-key.json`, `credentials*`). If they appear in the unstaged set, warn and exclude them by default. Vault-encrypted files (e.g. `vars/secrets.yml` in Ansible repos) are *not* in this set — they're meant to be committed.
- Use `git switch` for branch creation, not `git checkout -b`.
- Read the plan back to the user *before* running any `git commit`, never after.
