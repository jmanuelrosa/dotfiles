---
name: pr
description: Generate the PR description from the current branch and open the PR (GitHub) or MR (GitLab), returning the URL
argument-hint: "[base-branch] [--title \"<title>\"]"
model: sonnet
disable-model-invocation: true
allowed-tools:
  - Bash(git remote *)
  - Bash(git branch *)
  - Bash(git diff *)
  - Bash(git log *)
  - Bash(gh repo view *)
  - Bash(gh pr create *)
  - Bash(glab repo view *)
  - Bash(glab mr create *)
  - Bash(glab auth status *)
  - Bash(git symbolic-ref *)
  - Bash(git config --get *)
  - Read
  - Write
  - AskUserQuestion
---

# Create PR / MR

Fill the platform's PR template from the current branch's changes, push the branch, open the PR/MR, and return the URL.

## Steps

1. **Detect host, base branch, and (GitLab) account.**

   Host and branch from the remote:
   ```sh
   REMOTE=$(git remote get-url origin 2>/dev/null) || { echo "No origin remote"; exit 1; }
   case "$REMOTE" in
     *github*) HOST=gh ;;
     *gitlab*) HOST=glab ;;
     *) echo "Unsupported remote host: $REMOTE"; exit 1 ;;
   esac
   BRANCH=$(git branch --show-current)
   ```

   **Base branch.** Read it from local `origin/HEAD` (set at clone time, same for every account: avoids glab's per-account 404 on a repo cloned without its host alias). Fall back to the host CLI only when unset:
   ```sh
   BASE=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##')
   if [ -z "$BASE" ]; then
     if [ "$HOST" = gh ]; then
       BASE=$(gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name // empty' 2>/dev/null)
     else
       BASE=$(glab repo view -F json 2>/dev/null | jq -r '.default_branch // empty')
     fi
   fi
   [ -z "$BASE" ] && { echo "Could not determine default branch"; exit 1; }
   ```
   If invoked with an argument, use the bare (non-flag) argument as `$BASE` instead. If `--title "..."` is present, capture its quoted value as `$TITLE_OVERRIDE` (an explicit title the caller owns) and treat any remaining bare token as `$BASE`.

   **GitLab account** (skip for GitHub). If `HOST=glab`, read `references/gitlab-account.md` now and follow it to resolve `$GLHOST`/`$NS` from live `glab auth status` (one server can back multiple accounts, so a fixed list resolves wrong).

   Carry `$HOST`, `$BASE`, `$BRANCH`, and for GitLab `$GLHOST`/`$NS` forward. Use `gh`/`glab` wherever they have an equivalent; fall back to `git` only for what they don't cover (push, diff, log, status).

2. **Read the template**. First match wins, else proceed with none:
   - `.github/pull_request_template.md`
   - `.gitlab/merge_request_templates/*.md`

3. **Analyze the branch**:
   - `git log "$BASE"..HEAD --oneline`: commit history
   - `git diff "$BASE"...HEAD --stat`: overview of every touched file
   - Full diff excluding noisy paths that add no signal:
     ```sh
     git diff "$BASE"...HEAD -- . \
       ':(exclude)**/package-lock.json' ':(exclude)**/yarn.lock' \
       ':(exclude)**/pnpm-lock.yaml' ':(exclude)**/bun.lock*' \
       ':(exclude)**/*.min.js' ':(exclude)**/*.min.css' ':(exclude)**/*.map' \
       ':(exclude)**/dist/**' ':(exclude)**/build/**' ':(exclude)**/.next/**' \
       ':(exclude)**/*.generated.*' ':(exclude)**/*_generated.*' ':(exclude)**/*.pb.ts'
     ```
     Excluded files still show in `--stat`; mention them in the description when relevant.

4. **Fill the template**:
   - **Free-text sections**: clear, concise content on what the changes do and *why*. Extract Jira tickets from the branch name (`[A-Z]+-[0-9]+`) and link them where relevant.
   - **Checkbox sections**: check `[x]` only when the diff clearly supports it; leave `[ ]` for items not verifiable from code (e.g. "tested locally").
   - **Type/category selections**: infer from commit prefixes (`feat:`, `fix:`, `chore:`, `ci:`, `refactor:`, …) and check all that apply.

4b. **Confirm the target before pushing** (mandatory). The push below is the first outward action and the only sanctioned push path: a wrong branch means a manually-closed PR. Call `AskUserQuestion`:
   - `question`: "Push `$BRANCH` and open a PR against `$BASE`?" (interpolate real values; for GitLab name the resolved account too, e.g. "…as `gitlab.com-work`?")
   - `header`: "PR target", `multiSelect: false`
   - `options`: `Go` (push and open the PR/MR), `Cancel` (stop, push nothing).
   The structured question *is* the gate: don't accept prose like "yes" / "go" (free-form confirmations break the `git-skill-gate` hook). On `Other` (e.g. a different base), integrate it and re-confirm.

5. **Push the branch** (`$HOST`). `-u` sets the upstream when missing, pushes new commits when ahead, or prints `Everything up-to-date`.

   Issue the push as a **standalone top-level `git …` command**: never inside `if`/`case`/`&&` (the sandbox only runs a command unsandboxed when its leading token is `git`; a wrapper sandboxes the whole block and pre-push hooks then can't read `node_modules`).

   GitHub: force HTTPS and reset the credential-helper chain so sandboxed sessions (no readable `~/.ssh`, no keychain write) auth via the gh helper, leaving no state in `.git/config` or `~/.gitconfig`:
   ```sh
   git -c "url.https://github.com/.pushInsteadOf=git@github.com:" \
       -c credential.helper= \
       -c 'credential.helper=!gh auth git-credential' \
       push -u origin "$BRANCH"
   ```
   GitLab / other:
   ```sh
   git push -u origin "$BRANCH"
   ```
   On a real pre-push failure (lint, types, tests), surface the full output and stop. Never `--no-verify`.

6. **Build the title** (deterministic):
   - If `$TITLE_OVERRIDE` was captured in Step 1, use it verbatim as `$TITLE` and skip the rest of this step (the caller owns it; do not re-derive, re-humanize, or append a ticket).
   - Otherwise, build it from the branch name:
   - Split the branch on the first `/`: left side is the **branch type**, right side is everything else.
   - Map branch type → commit type: `feature` → `feat`; every other type passes through unchanged.
   - From the right side, strip a leading Jira ticket (`^[A-Z]+-[0-9]+`) and its trailing `-`; the rest is the slug. Replace remaining `-`/`_` with spaces and trim.
   - Derive the **scope** from the diff per step 6a.
   - Compose: `<commit-type>(<scope>): <slug-as-prose> (<TICKET>)`. Omit `(<scope>)` if repo-wide; omit `(<TICKET>)` if missing.

   Examples:
   - `feature/PROJ-123-add-auth`, files under `apps/auth/**` → `feat(auth): add auth (PROJ-123)`
   - `chore/bump-deps`, only root `package.json` → `chore: bump deps`

6a. **Derive the scope from the diff.** Take `git diff --name-only "$BASE"...HEAD` and pick, in order:
   - (a) a single `packages/*` or `apps/*` all paths live under → that package name.
   - (b) a shared top-level directory (e.g. `roles/<name>` here) → the directory name.
   - (c) a shared feature area from filenames (`auth`, `checkout`, `api`, …) → the feature area.

   If files cross two or more with no clear primary, leave the scope empty (repo-wide). When unsure, ask the user with the candidates listed.

7. **Write the filled template to a temp body file**:
   ```sh
   BODY=$(mktemp "${TMPDIR:-/tmp}/pr-body-XXXXXX")
   # write the filled template into "$BODY"
   ```

8. **Create the PR/MR** and self-assign to the author (`@me`), dispatching on `$HOST`:
   - `gh`: `gh pr create --base "$BASE" --head "$BRANCH" --title "$TITLE" --body-file "$BODY" --assignee @me`
   - `glab`: `glab mr create -R "$GLHOST/$NS" --target-branch "$BASE" --source-branch "$BRANCH" --title "$TITLE" --description "$(cat "$BODY")" --assignee @me --yes`

9. **Print only the resulting URL**, prefixed with `Created: ` (the last line of the create command's stdout).

## Humanization (required)

Every word in the title or description must read like a teammate wrote it: specific, plain, honest, no AI tells.

**Vocabulary to avoid** (and their cousins): *additionally, leverage, robust, seamless, comprehensive, holistic, delve, crucial, pivotal, key, vital, intricate, tapestry, landscape (figurative), testament, underscore, highlight (verb), enduring, vibrant, foster, journey, ecosystem, empower, unlock*.

**Constructions to avoid:**

- Punctuation/format tells: em dashes between clauses, curly quotes, emojis, Title Case headings, bold-header bullets (`**Performance:** …` → write a sentence).
- False-depth phrasing: negative parallelisms ("not only X but Y"), copula avoidance (*serves as / stands as / represents* → use *is* / *has*), tail "-ing" clauses ("…ensuring scalability"), forced rule-of-three, promotional adjectives (*powerful, seamless, cutting-edge*).
- Padding: filler ("in order to" → "to", "it is important to note that"), stacked hedges ("could potentially possibly"), generic positive endings ("a major step forward"), chatbot artifacts ("I hope this helps", "Certainly!").

**Voice:** say what changed and why, not how transformative it is. Be specific about numbers, file names, and behavior. If something's incomplete, say so plainly ("doesn't cover the X case yet"). Vary sentence length; short sentences are fine.

## Rules

- The `(<TICKET>)` title suffix is required whenever any commit in the branch references a Jira ticket. An explicit `--title` override is authoritative: used verbatim, exempt from derivation and this suffix rule.
- Use `--body-file` (or HEREDOC) so newlines and code fences in the description survive.
