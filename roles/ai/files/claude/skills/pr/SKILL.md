---
name: pr
description: Generate the PR description from the current branch and open the PR (GitHub) or MR (GitLab), returning the URL
argument-hint: "[base-branch]"
disable-model-invocation: true
allowed-tools:
  - Bash(git remote *)
  - Bash(git branch *)
  - Bash(git diff *)
  - Bash(git log *)
  - Bash(gh repo view *)
  - Bash(gh pr create *)
  - Bash(gh pr view *)
  - Bash(glab repo view *)
  - Bash(glab mr create *)
  - Read
  - Write
  - AskUserQuestion
---

# Create PR / MR

Fill the platform's PR template from the current branch's changes, push the branch, open the PR/MR, and return the URL.

## Steps

1. **Detect host and base branch**. Bootstrap host from the local remote URL, then ask the host CLI for the default branch:
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
   Rule: use `gh` / `glab` wherever they have an equivalent. Fall back to `git` only for operations they don't cover (push, diff, log, status).

   If the skill was invoked with an argument, use it as `$BASE` (the target base branch) instead of the auto-detected default.

2. **Read the template** — first match wins, otherwise proceed with no template:
   - `.github/pull_request_template.md`
   - `.gitlab/merge_request_templates/*.md`

3. **Analyze the branch**:
   - `git diff "$BASE"...HEAD` — full diff
   - `git log "$BASE"..HEAD --oneline` — commit history

4. **Fill the template**:
   - **Free-text sections** (descriptions, related issues): write clear, concise content based on what the changes do and why. Focus on the "why", not just the "what". Extract Jira tickets from the branch name (`[A-Z]+-[0-9]+`) and link them where relevant.
   - **Checkbox sections**: check `[x]` only when the diff clearly supports it; leave `[ ]` for items not verifiable from code (e.g. "tested locally").
   - **Type/category selections**: infer from commit prefixes (`feat:`, `fix:`, `chore:`, `ci:`, `refactor:`, …) and check all that apply.

4b. **Confirm the target before pushing** (mandatory). The push below is the first outward action and the only sanctioned push path here, so a wrong branch means a manually-closed PR. Call `AskUserQuestion` before pushing:
   - `question`: "Push `$BRANCH` and open a PR against `$BASE`?" (interpolate the real branch and base)
   - `header`: "PR target", `multiSelect: false`
   - `options`: `Go` (push and open the PR/MR) and `Cancel` (stop without pushing).
   Don't accept prose like "yes" / "go" in place of the structured question. On `Cancel`, stop and push nothing. The auto-provided `Other` lets the user redirect (e.g. a different base branch); integrate it and re-confirm.

5. **Push the branch** (use `$HOST` from step 1). Always push: `-u` sets the upstream when it's missing, pushes new commits when the branch is ahead, and prints `Everything up-to-date` when there's nothing to send.

   Issue the push as a **standalone top-level `git …` command** — never inside `if`/`case`/`&&` or any other shell construct. The sandbox runs a command unsandboxed only when its leading token is the excluded binary (`git`); a wrapper like `if … then git push; fi` leads with `if`, so the whole block is sandboxed and the pre-push hook (e.g. Biome) fails because it can't read `node_modules`. A bare `git push` runs unsandboxed, so the hook runs normally.

   GitHub:
   ```sh
   # Force HTTPS for this push so sandboxed sessions (where ~/.ssh is
   # unreadable) can authenticate via the gh credential helper. The empty
   # credential.helper resets the inherited chain so the osxkeychain helper
   # is never invoked — its store step can't write the keychain in the
   # sandbox and would fail the push with "failed to store" even though the
   # push itself succeeded. Leaves no state in .git/config or ~/.gitconfig.
   git -c "url.https://github.com/.pushInsteadOf=git@github.com:" \
       -c credential.helper= \
       -c 'credential.helper=!gh auth git-credential' \
       push -u origin "$BRANCH"
   ```
   GitLab / other:
   ```sh
   git push -u origin "$BRANCH"
   ```
   If the pre-push hook fails on real errors (lint, types, tests), surface the full output and stop. Never `--no-verify`.

6. **Build the title from the branch name** (deterministic):
   - Split the branch on the first `/`. The left side is the **branch type**; the right side is everything else.
   - If the branch type matches `feature|fix|chore|docs|refactor|test|perf|ci|build|style|revert`, use it. Otherwise treat the branch as having no type prefix (rare — happens on legacy or hand-named branches).
   - Map branch type → commit type: `feature` → `feat`. Every other branch type passes through unchanged (`fix` stays `fix`, `chore` stays `chore`, …).
   - From the right side, extract a leading Jira ticket (`^[A-Z]+-[0-9]+`) if present and strip it along with its trailing `-`. What remains is the slug.
   - Replace remaining `-`/`_` with spaces and trim.
   - Derive the **scope** from the diff per step 6a below.
   - Compose: `<commit-type>(<scope>): <slug-as-prose> (<TICKET>)`. Omit `(<scope>)` if the change is repo-wide; omit `(<TICKET>)` if missing; omit `<commit-type>:` if the branch had no recognized type.

   Examples:
   - `feature/PROJ-123-add-auth`, files under `apps/auth/**` → `feat(auth): add auth (PROJ-123)`
   - `fix/login-redirect-loop`, files under `apps/web/**` → `fix(web): login redirect loop`
   - `chore/bump-deps`, only root `package.json` → `chore: bump deps`
   - `refactor/PROJ-9-extract-cart-helper`, files under `packages/cart/**` → `refactor(cart): extract cart helper (PROJ-9)`

6a. **Derive the scope from the diff.** Take the file list from `git diff --name-only "$BASE"...HEAD`. Pick the scope by, in order:
   - (a) shared monorepo package if all paths live under a single `packages/*` or `apps/*` → use that package name.
   - (b) shared top-level directory (e.g. `roles/<name>` in this dotfiles repo) → use the directory name.
   - (c) shared feature area inferred from filenames (`auth`, `checkout`, `api`, …) → use the feature area.

   If files cross two or more candidates with no clear primary one, leave the scope empty and treat the change as repo-wide. When unsure, ask the user with the candidates listed.

7. **Write the filled template to a temp body file**:
   ```sh
   BODY=$(mktemp "${TMPDIR:-/tmp}/pr-body-XXXXXX")
   # write the filled template into "$BODY"
   ```

8. **Create the PR/MR** and self-assign it to the author (`@me`) (dispatch on `$HOST`):
   - `gh`: `gh pr create --base "$BASE" --head "$BRANCH" --title "$TITLE" --body-file "$BODY" --assignee @me`
   - `glab`: `glab mr create --target-branch "$BASE" --source-branch "$BRANCH" --title "$TITLE" --description "$(cat "$BODY")" --assignee @me --yes`

9. **Print only the resulting URL**, prefixed with `Created: `. The URL is the last line of stdout from the create command.

## Humanization (required)

Every word that ends up in the title or description must read like a teammate wrote it. This is not optional. The output should be specific, plain, and honest — no AI tells.

**Vocabulary to avoid** (and their cousins): *additionally, leverage, robust, seamless, comprehensive, holistic, delve, crucial, pivotal, key, vital, intricate, tapestry, landscape (figurative), testament, underscore, highlight (verb), enduring, vibrant, foster, journey, ecosystem, empower, unlock*. Use plain English.

**Constructions to avoid:**

- Em dashes between clauses. Use commas or periods.
- Negative parallelisms: "not only X but Y", "it's not just X, it's Y".
- Copula avoidance: *serves as / stands as / marks / represents*. Use *is* or *has*.
- Tail "-ing" clauses tacked on for depth ("…highlighting our commitment", "…ensuring scalability").
- Forced rule-of-three lists when there are really one or two things.
- Promotional adjectives (*powerful, seamless, robust, cutting-edge, modern*).
- Bold-header bullets (`**Performance:** …`) — write a sentence.
- Emojis. Anywhere.
- Title Case Headings. Use sentence case.
- Filler ("in order to" → "to"; "it is important to note that" → drop it).
- Stacked hedges ("could potentially possibly").
- Generic positive endings ("a major step forward", "exciting things ahead").
- Curly quotes (`"…"`). Use straight quotes.
- Chatbot artifacts: "I hope this helps", "Let me know if…", "Certainly!".

**Voice:** say what changed and why, not how transformative it is. Be specific about numbers, file names, and behavior. If something's incomplete, say so plainly ("doesn't cover the X case yet") instead of papering over it. Vary sentence length naturally — short sentences are fine.

### Bad vs good

Bad:

> This PR introduces a robust new authentication layer, leveraging modern protocols to deliver a seamless and secure user experience — serving as a key milestone in our journey toward enterprise-grade security.

Good:

> Adds OAuth login via Google and GitHub. Replaces the password-only flow on the admin panel. Session middleware is unchanged; that's the next PR.

## Rules

- Use `gh` for GitHub remotes and `glab` for GitLab remotes; fail loudly on any other host.
- Self-assign the PR/MR to the author with `--assignee @me`.
- Title format is `<type>(<scope>): <subject> (<TICKET>)`. Drop `(<scope>)` only when the change is repo-wide. The `(<TICKET>)` suffix is required if any commit in the branch references a Jira ticket.
- Use HEREDOC or `--body-file` so newlines and code fences in the description are preserved.
- Issue `git push` as a standalone top-level command — no `if`/`case`/`&&` wrapper — so the sandbox runs it (and its pre-push hooks) unsandboxed.
- Never `--no-verify` or skip hooks.
