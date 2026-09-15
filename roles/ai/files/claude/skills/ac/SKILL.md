---
name: ac
description: Write a Jira ticket's acceptance criteria into the branch's working copy before implementing, then publish them to the ticket as one comment that later runs update in place
argument-hint: "[push] [<TICKET>]"
model: sonnet
effort: high
disable-model-invocation: true
allowed-tools:
  - Bash(python3 *skills/jira/scripts/adf.py *)
  - Bash(acli jira workitem view *)
  - Bash(acli jira workitem comment create *)
  - Bash(acli jira workitem comment update *)
  - Bash(git rev-parse *)
  - Bash(git branch --show-current)
  - Bash(git check-ignore *)
  - Bash(mkdir -p *)
  - Bash(shasum *)
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - AskUserQuestion
---

# Acceptance criteria

Keep a Jira-tracked branch's acceptance criteria in the repo while you work, and publish them to the ticket as a single comment that is rewritten rather than duplicated.

Bare `/ac` authors or refines them. `/ac push` publishes.
Writing them *before* implementing is the point: criteria derived from a finished diff always pass, so they measure nothing.

The criteria themselves are `/jira`'s subject, not this skill's. It owns the strict-Gherkin rule and the wording bar (`skills/jira/SKILL.md`, the "Acceptance criteria are strict Gherkin" section), `adf.py` enforces the grammar, and this file owns only where the file lives and how it reaches the ticket.

## Scope: this skill is inert unless the branch says otherwise

Run both checks before anything else, and stop silently when either fails. Say which check failed in one line and do nothing further: no acli call, no file written.

1. The branch is `<type>/<KEY>-<slug>` with `KEY` matching `[A-Z]+-[0-9]+`. Read it with `git branch --show-current`.
2. `KEY`'s project prefix equals `$JIRA_PROJECT`.

The second check is what keeps this off a non-Jira repo. `$JIRA_PROJECT` is exported only by the work profile, so on a personal machine it is unset and every branch fails the check. It also rejects the false positives the key shape produces on its own: `fix/UTF-8-decoding-bug` yields prefix `UTF`, and `HTTP-2` and `ISO-8601` read the same way.

## The working copy

`<toplevel>/.claude/state/ac/<KEY>.md`, from `git rev-parse --show-toplevel` so the answer does not depend on the cwd.

It is an `adf.py` template and nothing more, so it is fed to the script with no editing in between:

```markdown
## Acceptance criteria

Scenario: a submitted review adds the eyes reaction
GIVEN a PR message posted in the review channel
WHEN a reviewer submits a review on GitHub
THEN the bot adds the eyes reaction to that message
AND the reaction is recorded against the PR number
```

Never commit it, and make that structural rather than a habit. When creating the working copy, check `git check-ignore -q .claude/state/ac` and append `.claude/state/ac/` to the repo's `.gitignore` if it exits non-zero, saying so in one line. The ignore rule is the only thing keeping this file out of a commit, so a repo without it leaks the file silently the first time someone runs `git add -A`. It is committed like any other `.gitignore` line, and a `wt` worktree inherits it because the file is tracked.

`<KEY>.comment-id` sits beside it holding two lines: the id of the published comment, then the sha256 of the body that was published. Line 1 decides create versus update, line 2 decides whether to publish at all. It is a separate file so the markdown stays something `adf.py` accepts verbatim.

## Steps

1. **Scope.** Both checks above. Stop if either fails.
2. **Read the ticket** when the working copy does not exist yet: `acli jira workitem view <KEY> --fields summary,description --json`. If its description already carries an Acceptance criteria section, seed the file from it so you refine rather than replace. If acli fails, say so and carry on from the file and the code; a missing seed is not a reason to stop.
3. **Author.** Write or refine the scenarios against the actual code, following `/jira`'s wording bar. Where the ticket states a symptom with no expected outcome, or several directions with no decision, stop and ask the specific open question rather than inventing scope.
4. **Check**, always, before showing anything: `python3 ~/.claude/skills/jira/scripts/adf.py <file> --comment --out /tmp/claude/ac-<KEY>.json`. Exit 4 is a grammar error naming the line; fix the file and run it again. Never hand-write the ADF, and never publish a body the script has not produced.
5. **Show** the scenarios as plain text and stop. Bare `/ac` ends here: publishing is `/ac push`, so the criteria can settle while the work is still moving.

## Publishing (`/ac push`)

Steps 1 and 4 first, always: nothing is published that has not just passed the grammar check.

Then hash the body the check just produced, and stop if the ticket already has it:

```bash
shasum -a 256 /tmp/claude/ac-<KEY>.json
```

Compare that hash to line 2 of `<KEY>.comment-id`. If they match, say `UNCHANGED` and stop: no acli call at all. The hash is over the generated ADF rather than the markdown, so reformatting the file without changing a scenario is correctly a no-op, and an `update` that rewrote a byte-identical body would still move the issue's `updated` timestamp, which perturbs every `ORDER BY updated` board and the `weekly-recap` query.

Otherwise publish, by whether line 1 of the sidecar exists:

| state | command |
|---|---|
| no sidecar | `acli jira workitem comment create --key <KEY> -F /tmp/claude/ac-<KEY>.json` |
| id on line 1 | `acli jira workitem comment update --key <KEY> --id <id> --body-adf /tmp/claude/ac-<KEY>.json` |

The two flags are not interchangeable. `create` reads ADF through `-F/--body-file`; `update` ignores that flag's ADF and needs `--body-adf`. Getting it backwards posts a raw JSON document to the ticket.

After either call succeeds, rewrite the sidecar with the id on line 1 and the hash on line 2. A `create` returns the id in its `--json` output. Without that write the next push creates a second comment, and without the hash the no-op above never fires. A sidecar carrying only an id is treated as an unknown hash: publish, then write both lines.

If `update` fails because the comment is gone, delete the sidecar and create a new one. If acli fails for any other reason, report it and stop: an auth lapse mid-session is routine here (see the note in `skills/jira/SKILL.md` on the config write), and the fix is `acli jira auth login --web` in the user's own terminal, not a retry.

## Boundaries

Publish only when the user asked (`/ac push`). Bare `/ac` never writes to Jira.

Never touch the ticket's description. The AC section there is `/jira`'s, and rewriting it from here would fight a human editor over a field this skill does not own.

One ticket, one file, one comment. A second branch on the same ticket shares the working copy, and the last push wins.
