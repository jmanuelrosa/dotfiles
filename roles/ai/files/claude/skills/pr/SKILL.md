---
name: pr
description: Generate the PR description from the current branch and open the PR (GitHub) or MR (GitLab), returning the URL
license: MIT
---

# Create PR / MR

Fill the platform's PR template from the current branch's changes, push if needed, open the PR/MR, and return the URL.

## Steps

1. **Detect the base branch** from `origin/HEAD`:
   ```sh
   git fetch origin --quiet
   BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
   if [ -z "$BASE" ]; then
     git remote set-head origin --auto >/dev/null 2>&1
     BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
   fi
   [ -z "$BASE" ] && { echo "Could not determine default branch"; exit 1; }
   BRANCH=$(git branch --show-current)
   ```

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

5. **Detect host** from `git remote get-url origin`:
   - contains `github` → use `gh`
   - contains `gitlab` → use `glab`
   - anything else → stop with `Unsupported remote host: <url>`

6. **Push branch if it has no upstream**:
   ```sh
   git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1 || \
     git push -u origin "$BRANCH"
   ```

7. **Build the title from the branch name** (deterministic):
   - If the first `/`-separated segment matches `feat|fix|chore|ci|refactor|docs|test|perf|build|style`, treat it as the type prefix.
   - Extract a Jira ticket (`[A-Z]+-[0-9]+`) from the rest and remove it.
   - Replace remaining `-`/`_` with spaces and trim.
   - Compose: `<type>: <rest> (<TICKET>)` — omit any part that's missing.

   Examples:
   - `feat/PROJ-123-add-auth` → `feat: add auth (PROJ-123)`
   - `fix/login-redirect-loop` → `fix: login redirect loop`
   - `PROJ-456-cleanup-tests` → `cleanup tests (PROJ-456)`

8. **Write the filled template to a temp body file**:
   ```sh
   BODY=$(mktemp "${TMPDIR:-/tmp}/pr-body.XXXXXX.md")
   # write the filled template into "$BODY"
   ```

9. **Create the PR/MR**:
   - GitHub: `gh pr create --base "$BASE" --head "$BRANCH" --title "$TITLE" --body-file "$BODY"`
   - GitLab: `glab mr create --target-branch "$BASE" --source-branch "$BRANCH" --title "$TITLE" --description "$(cat "$BODY")" --yes`

10. **Print only the resulting URL**, prefixed with `Created: `. The URL is the last line of stdout from the create command.

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
