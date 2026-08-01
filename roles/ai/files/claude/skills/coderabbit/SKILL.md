---
name: coderabbit
description: Walk open CodeRabbit review threads on a GitHub PR, investigate each in the code, then either fix it or reply to @coderabbitai explaining why it stays. Resolves each thread it handles. Stops before commit.
argument-hint: "[pr-number]"
effort: medium
disable-model-invocation: true
allowed-tools:
  - Bash(python3 *skills/coderabbit/scripts/context.py)
  - Bash(python3 *skills/coderabbit/scripts/context.py *)
  - Bash(python3 *skills/coderabbit/scripts/apply.py *)
  - Read
  - Edit
  - Grep
  - Glob
  - AskUserQuestion
---

# Address CodeRabbit review threads

Walk every open CodeRabbit thread on a PR, investigate each one in the code, triage it, get one batched approval, then either fix the code or reply to `@coderabbitai` explaining why it stays.
Resolve each thread once handled.
Never commit or push, that is `/commit` and `/pr`'s job.

Two bundled scripts do the mechanical work in one call each; don't run `gh` yourself for anything they already cover.
Global install: `~/.claude/skills/coderabbit/scripts/`; project install: `.claude/skills/coderabbit/scripts/`.

## Steps

1. **Gather context** (single call): `python3 ~/.claude/skills/coderabbit/scripts/context.py [pr-number]`.
   Pass the skill's argument through as `[pr-number]`; with no argument the script resolves the current branch's PR.

   It has already done all of this, so take its output as given: refused any non-GitHub remote, resolved the repo and PR, fetched every review thread with its resolved and outdated state, dropped the threads a previous run handled, stripped CodeRabbit's collapsed boilerplate, and grouped what survives by file path.
   For each surviving thread it prints `path:line`, a `severity`, the `thread=` node id, the `reply-to=` root comment id, the cleaned body, and the diff hunk CodeRabbit saw.
   It also prints the PR title, description, and the bot's latest walkthrough: read the walkthrough once for context, do not triage its bullets as tasks.

   Stop and report if it exits non-zero (no origin, a non-GitHub remote, or no PR: tell the user to pass a PR number or run `/pr` first).
   If it prints `No open CodeRabbit threads on PR #<n>.`, say so and stop.
   That is the normal steady state, not an error.

2. **Investigate each thread in the code**. This is the actual work, and it is the one part no script can do.
   For each thread: open `path` at the printed line, read enough surrounding context to judge it, use Grep/Glob to confirm whether the concern is real (is the null actually unguarded, is the export actually unused), and read the diff hunk to see exactly what CodeRabbit saw.
   Form a one-line, code-grounded verdict.
   Never take the comment's word for it: CodeRabbit reads a diff, you can read the whole repo.

3. **Triage into three buckets**:
   - **FIX**: the suggestion is correct and worth doing now.
     Note the exact edit.
   - **REPLY-AND-SKIP** (declined): wrong, out of scope, intentional, or a nitpick not worth it.
     Draft a reply per the format below.
   - **ASK-USER**: a judgment call, or a real change in behavior or public API the user should decide.
     Carries a specific question.

   Weigh the `severity` the script prints: `nitpick` and `outside-diff` are low priority, `potential` and `warning` are the real candidates.

4. **Single batched approval gate** (mandatory). Print **one** verdict table for the whole PR:
   ```
   # | path:line             | severity  | verdict        | action
   1 | src/auth/token.ts:42  | warning   | FIX            | guard null session before decode
   2 | src/api/users.ts:88   | nitpick   | REPLY-AND-SKIP | naming is intentional, matches column
   3 | src/cron/sweep.ts:12  | potential | ASK-USER       | changes retry semantics, confirm?
   ```
   Below the table, print the **full drafted reply text** for every REPLY-AND-SKIP item, so the user sees exactly what goes public before approving.
   Replies are visible to the whole team, the gate must cover them.

   Then call `AskUserQuestion`:
   - `question: "Apply this CodeRabbit triage?"`
   - `header: "CodeRabbit triage"`
   - `multiSelect: false`
   - `options`:
     - `Go`: apply all FIX edits and post all REPLY-AND-SKIP replies, then resolve every handled thread.
     - `Fixes only`: apply FIX edits and resolve those threads, post no replies.
     - `Replies only`: post replies and resolve those threads, make no code edits.
     - `Cancel`: do nothing.
   - The auto-provided `Other` lets the user redirect ("flip 2 to FIX", "answer ASK-USER #3: yes", "reword reply 2").
     On `Other`, fold in the feedback, re-triage, re-show the table, and re-run this gate.

   Resolve every ASK-USER item inside this loop (via `Other` or a short prior question) so the final answer is unambiguous.
   Never auto-pick an ASK-USER verdict.
   Do not wait for prose like `go` / `lgtm`.
   The structured question is the gate.
   Free-form confirmations break `attributionSkill` in the transcript and would cause `git-skill-gate.sh` to block a later `/commit`.

5. **Apply the FIX edits** with Edit, before running the executor.
   Do **not** commit or push.
   The `git-skill-gate.sh` hook blocks `git commit` / `git push` outside `/commit` and `/pr`, and that is intended.

6. **Post the replies and resolve the threads** (single call). **Write** the approved plan to `/tmp/claude/coderabbit-plan-<repo>-<suffix>.json` (`<suffix>` random once per run), carrying only the verdicts the chosen gate option covers:
   ```json
   {
     "repo": "owner/name",
     "pr": 42,
     "threads": [
       {"thread": "PRRT_a", "verdict": "fix", "files": ["src/auth/token.ts"]},
       {"thread": "PRRT_b", "verdict": "reply", "reply_to": 1001, "body": "@coderabbitai\n\n> Suggestion: ...\n\nThe reason."},
       {"thread": "PRRT_c", "verdict": "ask"}
     ],
     "skipped": {"resolved": 4, "outdated": 1}
   }
   ```
   Copy `repo`, `pr` and the `skipped` counts from step 1's output, and `thread` / `reply_to` verbatim from the thread you are acting on.
   Newlines inside `body` are `\n` escapes.
   Then run `python3 ~/.claude/skills/coderabbit/scripts/apply.py <plan path>`.

   It validates every reply up front (attribution lines, long dashes, emoji, an echoed "Prompt for AI Agents" block, a missing `reply_to`), posts each reply into the right thread, appends the `<!-- cr-skill -->` marker for you, resolves each thread only once its action succeeded, and prints the counters.
   A `fix` entry resolves its thread without posting anything; an `ask` entry resolves nothing, because an unanswered question must stay visible.
   It exits non-zero if any call failed and names the thread; report that and move on, the next run stays idempotent either way.

7. **Report** the summary line apply.py printed (N fixed, N replied, N resolved, N asked, N skipped) and remind the user to run `/commit` then `/pr`.
   The threads are resolved, but the code is not pushed yet, and resolving does not push for them.
   Multiple rounds are normal: re-run `/coderabbit` after each push and step 1 keeps it idempotent.

## Reply format

Every REPLY-AND-SKIP reply is addressed to `@coderabbitai` and structured so the thread reads as CodeRabbit's suggestion, then our reason.
Restate the suggestion in a blockquote, then give the reason in plain prose:

> @coderabbitai
>
> > Suggestion: guard the session before decoding the token.
>
> The session is guaranteed non-null here.
> `requireAuth` runs before this handler and 401s otherwise, so leaving it as is.

`apply.py` appends the `<!-- cr-skill -->` marker; don't write it yourself.

## Reply voice (required)

Replies are public and read by teammates, so they must read like a teammate wrote them.
Same anti-AI-slop rules as the `/pr` skill, narrowed to short technical replies.

**Vocabulary to avoid** (and their cousins): *leverage, robust, seamless, comprehensive, delve, crucial, pivotal, key, additionally, underscore, highlight (verb), holistic, foster, streamline, enhance*.
Use plain English.

**Constructions to avoid:**

- Sycophancy: "Great catch!", "You're absolutely right!". State the reason.
- Long dashes between clauses. Use commas or periods.
- Emojis. Anywhere.
- Curly quotes. Use straight quotes.
- Title Case headings.
- Stacked hedges ("could potentially possibly").

Keep it to one to three sentences after the restated suggestion.
Say what the code does and why the suggestion does not apply, or that the current behavior is intentional.
If declining a valid but out-of-scope point, say so and where it belongs ("out of scope here, tracked separately").
Never paste CodeRabbit's "Prompt for AI Agents" block back at it.

Good:

> @coderabbitai
>
> > Suggestion: memoize this selector to avoid recomputation.
>
> This runs once per mount, not on every render, so memoizing adds indirection for no measurable gain.
> Leaving it as is.

Bad:

> Great catch!
> You're absolutely right that we should leverage a more robust memoization approach here to ensure a seamless experience.

## Rules

- GitHub only.
  `context.py` fails loudly on any other host; don't work around it.
- The two scripts own every `gh` call.
  Never WebFetch, MCP, or `curl`, and don't hand-roll a `gh api graphql` call: the scripts pass their documents as JSON request bodies, which is what keeps the `Type!` non-null markers intact.
- Nothing mutates before the approval gate.
  Edits and replies happen only after `Go` / `Fixes only` / `Replies only`.
- Never commit or push.
  Hand off to `/commit` then `/pr`.
  The hook enforces this.
- Resolve every thread the skill acts on once the action succeeds.
  Never resolve a thread that was not fixed or replied to, and never one left as ASK-USER.
- Never auto-pick an ASK-USER verdict.
- Re-running is safe: resolved, outdated, and already-answered threads never reach triage.
