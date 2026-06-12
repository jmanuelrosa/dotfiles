---
name: coderabbit
description: Walk open CodeRabbit review threads on a GitHub PR, investigate each in the code, then either fix it or reply to @coderabbitai explaining why it stays. Resolves each thread it handles. Stops before commit.
argument-hint: "[pr-number]"
disable-model-invocation: true
---

# Address CodeRabbit review threads

Walk every open CodeRabbit thread on a PR, investigate each one in the code,
triage it, get one batched approval, then either fix the code or reply to
`@coderabbitai` explaining why it stays. Resolve each thread once handled. Never
commit or push, that is `/commit` and `/pr`'s job.

If invoked with an argument, treat it as the PR number to work on instead of the
current branch's PR.

## Steps

1. **Resolve host and PR**. CodeRabbit is a GitHub bot, so fail loudly on any
   non-GitHub remote.
   ```sh
   REMOTE=$(git remote get-url origin 2>/dev/null) || { echo "No origin remote"; exit 1; }
   case "$REMOTE" in
     *github*) : ;;
     *) echo "coderabbit only supports GitHub remotes (got: $REMOTE)"; exit 1 ;;
   esac

   REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner')
   PR=$(gh pr view --json number --jq '.number' 2>/dev/null)
   ```
   If the skill was invoked with a PR number argument, use it as `$PR` instead of
   the current-branch detection. If neither an argument nor a current-branch PR is
   found, stop and tell the user to pass a PR number or run `/pr` first.

   The gh alias `pr = pr create --web` shadows only the bare first token, so
   `gh pr view`, `gh pr create`, and `gh api` are all safe to call.

2. **Fetch the threads and the walkthrough**. The PR-level walkthrough comes from
   a native subcommand. Read it once for context, do not triage its bullets as
   tasks:
   ```sh
   gh pr view "$PR" --json title,body,reviews
   ```
   The actionable inline threads need resolved/outdated state, which no `gh`
   subcommand and no REST endpoint exposes. Only the GraphQL `reviewThreads`
   connection has it, so this one fetch uses `gh api graphql`. It is the source of
   truth for what to process and what to skip.

   GraphQL type signatures contain `!` (non-null markers: `String!`, `Int!`, `ID!`).
   **Never put a GraphQL document in a Bash command** — the shell escapes `!` to
   `\!` even inside single quotes and heredocs, which GitHub rejects with
   `Expected VAR_SIGN, actual: UNKNOWN_CHAR ("!")`. Instead **create the query file
   with the Write tool** (it writes literal bytes, bypassing the shell), then pass it
   with `-F query=@file`.

   Write this to `/tmp/cr-threads.graphql` with the Write tool, verbatim (use a
   literal absolute path — the Write tool does not expand `$TMPDIR`):
   ```graphql
   query($owner:String!,$name:String!,$pr:Int!,$endCursor:String){
     repository(owner:$owner,name:$name){
       pullRequest(number:$pr){
         reviewThreads(first:100, after:$endCursor){
           pageInfo{ hasNextPage endCursor }
           nodes{
             id isResolved isOutdated
             comments(first:100){ nodes{ databaseId author{login} body path line originalLine diffHunk } }
           }
         }
       }
     }
   }
   ```
   Then run (no `!` in this command, so it is shell-safe):
   ```sh
   OWNER=${REPO%/*}; NAME=${REPO#*/}
   gh api graphql --paginate \
     -f owner="$OWNER" -f name="$NAME" -F pr="$PR" \
     -F query=@/tmp/cr-threads.graphql
   ```
   `--paginate` walks the `reviewThreads` pages via the `$endCursor` variable. A
   CodeRabbit thread is one whose **first** comment author is `coderabbitai[bot]`.
   Each comment's `databaseId` equals the REST comment id, used for replies in
   step 8. Each thread's `id` is the node id, used to resolve it in step 8.

3. **Skip already-handled threads** (idempotency). Skip a CodeRabbit thread when
   any of:
   - `isResolved == true` — the primary signal. Step 8 resolves every thread this
     skill acts on, so anything handled in a prior run drops out here. Also covers
     threads resolved by hand or auto-resolved by CodeRabbit on re-review.
   - `isOutdated == true` — the line no longer exists, the suggestion is stale.
   - the thread already has a reply by a human or the PR author.
   - the thread already has a reply carrying this skill's hidden marker
     (`<!-- cr-skill -->`), a backup signal if a resolve call failed mid-run.

   If zero actionable threads remain, print `No open CodeRabbit threads on PR #<n>.`
   and stop. This is the normal steady state, not an error.

4. **Strip noise from each comment body** before triage. Drop:
   - collapsed `<details>` blocks, especially "Nitpick comments" and "Outside diff
     range" sections,
   - the "🤖 Prompt for AI Agents" block — read it as a hint, never paste it into a
     reply,
   - `<summary>` wrappers and committable-suggestion diff fences.

   Treat `nitpick` items as low priority. Treat items flagged `potential issue` or
   `warning` as the real candidates.

5. **Investigate each comment in the code**. For each kept comment: open `path` at
   `line` (fall back to `originalLine` when `line` is null on an outdated hunk),
   read enough surrounding context to judge it, use Grep/Glob to confirm whether
   the concern is real (is the null actually unguarded, is the export actually
   unused), and read the `diffHunk` to see exactly what CodeRabbit saw. Form a
   one-line, code-grounded verdict.

6. **Triage into three buckets**:
   - **FIX** — the suggestion is correct and worth doing now. Note the exact edit.
   - **REPLY-AND-SKIP** — declined: wrong, out of scope, intentional, or a nitpick
     not worth it. Draft a reply per the format below.
   - **ASK-USER** — a judgment call, or a real change in behavior or public API the
     user should decide. Carries a specific question.

7. **Single batched approval gate** (mandatory). Print **one** verdict table for
   the whole PR:
   ```
   # | path:line             | severity  | verdict        | action
   1 | src/auth/token.ts:42  | warning   | FIX            | guard null session before decode
   2 | src/api/users.ts:88   | nitpick   | REPLY-AND-SKIP | naming is intentional, matches column
   3 | src/cron/sweep.ts:12  | potential | ASK-USER       | changes retry semantics, confirm?
   ```
   Below the table, print the **full drafted reply text** for every
   REPLY-AND-SKIP item, so the user sees exactly what goes public before
   approving. Replies are visible to the whole team, the gate must cover them.

   Then call `AskUserQuestion`:
   - `question: "Apply this CodeRabbit triage?"`
   - `header: "CodeRabbit triage"`
   - `multiSelect: false`
   - `options`:
     - `Go` — apply all FIX edits and post all REPLY-AND-SKIP replies, then
       resolve every handled thread.
     - `Fixes only` — apply FIX edits and resolve those threads, post no replies.
     - `Replies only` — post replies and resolve those threads, make no code edits.
     - `Cancel` — do nothing.
   - The auto-provided `Other` lets the user redirect ("flip 2 to FIX", "answer
     ASK-USER #3: yes", "reword reply 2"). On `Other`, fold in the feedback,
     re-triage, re-show the table, and re-run this gate.

   Resolve every ASK-USER item inside this loop (via `Other` or a short prior
   question) so the final answer is unambiguous. Never auto-pick an ASK-USER
   verdict. Do not wait for prose like `go` / `lgtm` — the structured question is
   the gate. Free-form confirmations break `attributionSkill` in the transcript
   and would cause `git-skill-gate.sh` to block a later `/commit`.

8. **Execute, then resolve each handled thread**:
   - **FIX**: make the edits with Edit. Do **not** commit or push — the
     `git-skill-gate.sh` hook blocks `git commit` / `git push` outside `/commit`
     and `/pr`, and that is intended. After edits, tell the user to run `/commit`
     then `/pr`.
   - **REPLY-AND-SKIP**: reply into the correct thread by replying to the thread's
     **first** CodeRabbit comment `databaseId` (the thread root), so the
     `in_reply_to` chain stays attached to the right thread. No `gh pr` subcommand
     posts a threaded reply to an inline review comment (`gh pr comment` only adds
     top-level issue comments), so this uses `gh api`:
     ```sh
     gh api "repos/$REPO/pulls/$PR/comments" \
       -f body="$REPLY_BODY" \
       -F in_reply_to="$ROOT_COMMENT_ID"
     ```
     Append the hidden marker `<!-- cr-skill -->` to each reply body for
     traceability on later runs.
   - **Resolve the thread** once its action succeeds, for both FIX (edit applied)
     and REPLY-AND-SKIP (reply posted). No `gh` subcommand resolves threads, so use
     the GraphQL `resolveReviewThread` mutation against the thread node `id` from
     step 2. It has an `ID!` marker, so the same rule applies: write the mutation to
     a file with the **Write tool** (once, then reuse for every thread), never inline
     it. Write this to `/tmp/cr-resolve.graphql` with the Write tool, verbatim:
     ```graphql
     mutation($threadId:ID!){
       resolveReviewThread(input:{threadId:$threadId}){ thread{ id isResolved } }
     }
     ```
     Then resolve each thread (shell-safe, no `!`):
     ```sh
     gh api graphql -f threadId="$THREAD_NODE_ID" -F query=@/tmp/cr-resolve.graphql
     ```
     Resolve only the threads acted on by the chosen gate option. If a resolve call
     fails, report it and continue — the hidden marker and the `isResolved` check
     in step 3 still keep the next run idempotent.

9. **Print a summary**: N fixed (files touched), N replied (with thread links), N
   threads resolved, N asked, N skipped as already resolved or outdated. Remind the
   user to run `/commit` then `/pr` to push the fixes — the threads are resolved,
   but the code is not pushed yet, and resolving does not push for them. Multiple
   rounds are normal: re-run `/coderabbit` after each push and step 3 keeps it
   idempotent.

## Reply format

Every REPLY-AND-SKIP reply is addressed to `@coderabbitai` and structured so the
thread reads as CodeRabbit's suggestion, then our reason. Restate the suggestion
in a blockquote, then give the reason in plain prose:

> @coderabbitai
>
> > Suggestion: guard the session before decoding the token.
>
> The session is guaranteed non-null here. `requireAuth` runs before this handler
> and 401s otherwise, so leaving it as is.

End the body with the marker on its own line: `<!-- cr-skill -->`.

## Reply voice (required)

Replies are public and read by teammates, so they must read like a teammate
wrote them. Same anti-AI-slop rules as the `/pr` skill, narrowed to short
technical replies.

**Vocabulary to avoid** (and their cousins): *leverage, robust, seamless,
comprehensive, delve, crucial, pivotal, key, additionally, underscore,
highlight (verb), holistic, foster, streamline, enhance*. Use plain English.

**Constructions to avoid:**

- Sycophancy: "Great catch!", "You're absolutely right!". State the reason.
- Em dashes between clauses. Use commas or periods.
- Emojis. Anywhere.
- Curly quotes. Use straight quotes.
- Title Case headings.
- Stacked hedges ("could potentially possibly").

Keep it to one to three sentences after the restated suggestion. Say what the
code does and why the suggestion does not apply, or that the current behavior is
intentional. If declining a valid but out-of-scope point, say so and where it
belongs ("out of scope here, tracked separately"). Never paste CodeRabbit's
"Prompt for AI Agents" block back at it.

Good:

> @coderabbitai
>
> > Suggestion: memoize this selector to avoid recomputation.
>
> This runs once per mount, not on every render, so memoizing adds indirection
> for no measurable gain. Leaving it as is.

Bad:

> Great catch! You're absolutely right that we should leverage a more robust
> memoization approach here to ensure a seamless experience.

## Rules

- GitHub only. Fail loudly on any other host.
- Prefer native `gh` subcommands. Use `gh api` / `gh api graphql` only for the
  three things with no subcommand: review-thread resolved/outdated state, posting
  a threaded reply, and resolving a thread. Never WebFetch, MCP, or `curl`.
- Never put a GraphQL document in a Bash command. The shell escapes `!` to `\!`
  even inside single quotes and heredocs, corrupting the `Type!` non-null markers
  (`Expected VAR_SIGN, actual "!"`). Create the `.graphql` file with the **Write
  tool** (literal bytes, no shell), then pass it with `gh api graphql -F query=@file`.
- Nothing mutates before the approval gate. Edits and replies happen only after
  `Go` / `Fixes only` / `Replies only`.
- Never commit or push. Hand off to `/commit` then `/pr`. The hook enforces this.
- Resolve every thread the skill acts on once the action succeeds. Never resolve a
  thread that was not fixed or replied to.
- Never auto-pick an ASK-USER verdict.
- Skip resolved, outdated, and already-answered threads so re-running is safe.
