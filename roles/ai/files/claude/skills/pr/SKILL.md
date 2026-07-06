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
   If invoked with an argument, use it as `$BASE` instead.

   **GitLab account** (skip for GitHub). One GitLab server can back more than one authenticated account (a host alias can point a second account at the same server), and glab picks by the remote's host token, so a repo cloned with a bare or shared host can resolve to the wrong account (silent 404). Resolve from live `glab auth status`, never a fixed list:
   ```sh
   RHOST=$(printf '%s' "$REMOTE" | sed -E 's#^[a-z]+://##; s#^[^@]*@##; s#[:/].*##')
   NS=$(printf '%s' "$REMOTE" | sed -E 's#^[a-z]+://[^/]+/##; s#^[^@]*@[^:]+:##; s#\.git$##')
   # host <TAB> api-endpoint-host <TAB> account, one line per authenticated host
   HOSTMAP=$(glab auth status 2>&1 | awk '
     /^[A-Za-z0-9._-]+$/  { h=$1; a="?" }
     /Logged in to/       { for (i=1;i<=NF;i++) if ($i=="as") a=$(i+1) }
     /REST API Endpoint:/ { u=$NF; gsub(/https?:\/\/|\/.*/, "", u); print h"\t"u"\t"a }')
   # candidates: authenticated hosts whose key OR API endpoint matches the remote host token
   CANDS=$(printf '%s\n' "$HOSTMAP" | awk -F'\t' -v r="$RHOST" '$1==r || $2==r {print $1"\t"$3}')
   ```
   Pick `$GLHOST` from `$CANDS` (each line is `host <TAB> account`):
   - **One** → use its host, don't ask.
   - **More than one** → `AskUserQuestion` (`header: "GitLab account"`, `multiSelect: false`, one option per candidate labelled `<host> (<account>)`, default to the one whose account matches `git config --get user.email`). Set `$GLHOST` to the choice.
   - **None** → not logged into `$RHOST`: drop `-R` and let glab auto-detect; if that fails, surface "not logged into `$RHOST`: run `glab auth login`".

   Carry `$HOST`, `$BASE`, `$BRANCH`, and for GitLab `$GLHOST`/`$NS` forward. Use `gh`/`glab` wherever they have an equivalent; fall back to `git` only for what they don't cover (push, diff, log, status).

2. **Read the template**. First match wins, else proceed with none:
   - `.github/pull_request_template.md`
   - `.gitlab/merge_request_templates/*.md`

3. **Analyze the branch**:
   - `git diff "$BASE"...HEAD`: full diff
   - `git log "$BASE"..HEAD --oneline`: commit history

4. **Fill the template**:
   - **Free-text sections**: clear, concise content on what the changes do and *why*. Extract Jira tickets from the branch name (`[A-Z]+-[0-9]+`) and link them where relevant.
   - **Checkbox sections**: check `[x]` only when the diff clearly supports it; leave `[ ]` for items not verifiable from code (e.g. "tested locally").
   - **Type/category selections**: infer from commit prefixes (`feat:`, `fix:`, `chore:`, `ci:`, `refactor:`, …) and check all that apply.

4b. **Confirm the target before pushing** (mandatory). The push below is the first outward action and the only sanctioned push path: a wrong branch means a manually-closed PR. Call `AskUserQuestion`:
   - `question`: "Push `$BRANCH` and open a PR against `$BASE`?" (interpolate real values; for GitLab name the resolved account too, e.g. "…as `gitlab.com-work`?")
   - `header`: "PR target", `multiSelect: false`
   - `options`: `Go` (push and open the PR/MR), `Cancel` (stop, push nothing).
   Don't accept prose like "yes" / "go" in place of the structured question. On `Other` (e.g. a different base), integrate it and re-confirm.

5. **Push the branch** (`$HOST`). `-u` sets the upstream when missing, pushes new commits when ahead, or prints `Everything up-to-date`.

   Issue the push as a **standalone top-level `git …` command**: never inside `if`/`case`/`&&`. The sandbox runs a command unsandboxed only when its leading token is the excluded binary (`git`); a wrapper leads with `if`/etc., so the whole block is sandboxed and a pre-push hook (e.g. Biome) fails because it can't read `node_modules`.

   GitHub: force HTTPS so sandboxed sessions (no readable `~/.ssh`) auth via the gh helper; the empty `credential.helper` resets the inherited chain so osxkeychain (which can't write in the sandbox) is never invoked. Leaves no state in `.git/config` or `~/.gitconfig`:
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

6. **Build the title from the branch name** (deterministic):
   - Split the branch on the first `/`: left side is the **branch type**, right side is everything else.
   - If the branch type matches `feature|fix|chore|docs|refactor|test|perf|ci|build|style|revert`, use it; otherwise treat the branch as having no type prefix (rare: legacy or hand-named branches).
   - Map branch type → commit type: `feature` → `feat`; every other type passes through unchanged.
   - From the right side, strip a leading Jira ticket (`^[A-Z]+-[0-9]+`) and its trailing `-`; the rest is the slug. Replace remaining `-`/`_` with spaces and trim.
   - Derive the **scope** from the diff per step 6a.
   - Compose: `<commit-type>(<scope>): <slug-as-prose> (<TICKET>)`. Omit `(<scope>)` if repo-wide; omit `(<TICKET>)` if missing; omit `<commit-type>:` if the branch had no recognized type.

   Examples:
   - `feature/PROJ-123-add-auth`, files under `apps/auth/**` → `feat(auth): add auth (PROJ-123)`
   - `fix/login-redirect-loop`, files under `apps/web/**` → `fix(web): login redirect loop`
   - `chore/bump-deps`, only root `package.json` → `chore: bump deps`
   - `refactor/PROJ-9-extract-cart-helper`, files under `packages/cart/**` → `refactor(cart): extract cart helper (PROJ-9)`

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

- Em dashes between clauses: use commas or periods.
- Negative parallelisms ("not only X but Y", "it's not just X, it's Y").
- Copula avoidance (*serves as / stands as / marks / represents*): use *is* / *has*.
- Tail "-ing" clauses for false depth ("…highlighting our commitment", "…ensuring scalability").
- Forced rule-of-three when there are really one or two things.
- Promotional adjectives (*powerful, seamless, robust, cutting-edge, modern*).
- Bold-header bullets (`**Performance:** …`): write a sentence.
- Emojis, anywhere.
- Title Case Headings: use sentence case.
- Filler ("in order to" → "to"; drop "it is important to note that").
- Stacked hedges ("could potentially possibly").
- Generic positive endings ("a major step forward", "exciting things ahead").
- Curly quotes: use straight quotes.
- Chatbot artifacts ("I hope this helps", "Let me know if…", "Certainly!").

**Voice:** say what changed and why, not how transformative it is. Be specific about numbers, file names, and behavior. If something's incomplete, say so plainly ("doesn't cover the X case yet"). Vary sentence length; short sentences are fine.

**Bad:** This PR introduces a robust new authentication layer, leveraging modern protocols to deliver a seamless and secure user experience — serving as a key milestone in our journey toward enterprise-grade security.

**Good:** Adds OAuth login via Google and GitHub. Replaces the password-only flow on the admin panel. Session middleware is unchanged; that's the next PR.

## Rules

- Title format: `<type>(<scope>): <subject> (<TICKET>)`. Drop `(<scope>)` only when repo-wide; the `(<TICKET>)` suffix is required whenever any commit in the branch references a Jira ticket.
- Use `--body-file` (or HEREDOC) so newlines and code fences in the description survive.
- Never `--no-verify` or skip hooks.
