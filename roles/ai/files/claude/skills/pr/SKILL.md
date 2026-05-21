---
name: pr
description: Generate the PR description from the current branch and open the PR (GitHub) or MR (GitLab), returning the URL
---

# Create PR / MR

Fill the platform's PR template from the current branch's changes, push if needed, open the PR/MR, and return the URL.

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

5. **Push branch if it has no upstream** (use `$HOST` from step 1):
   ```sh
   git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1 || \
     git push -u origin "$BRANCH"
   ```

6. **Build the title from the branch name** (deterministic):
   - If the first `/`-separated segment matches `feat|fix|chore|ci|refactor|docs|test|perf|build|style`, treat it as the type prefix.
   - Extract a Jira ticket (`[A-Z]+-[0-9]+`) from the rest and remove it.
   - Replace remaining `-`/`_` with spaces and trim.
   - Compose: `<type>: <rest> (<TICKET>)` — omit any part that's missing.

   Examples:
   - `feat/PROJ-123-add-auth` → `feat: add auth (PROJ-123)`
   - `fix/login-redirect-loop` → `fix: login redirect loop`
   - `PROJ-456-cleanup-tests` → `cleanup tests (PROJ-456)`

7. **Write the filled template to a temp body file**:
   ```sh
   BODY=$(mktemp "${TMPDIR:-/tmp}/pr-body.XXXXXX.md")
   # write the filled template into "$BODY"
   ```

8. **Create the PR/MR** (dispatch on `$HOST`):
   - `gh`: `gh pr create --base "$BASE" --head "$BRANCH" --title "$TITLE" --body-file "$BODY"`
   - `glab`: `glab mr create --target-branch "$BASE" --source-branch "$BRANCH" --title "$TITLE" --description "$(cat "$BODY")" --yes`

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
- Use HEREDOC or `--body-file` so newlines and code fences in the description are preserved.
- Never `--no-verify` or skip hooks.
