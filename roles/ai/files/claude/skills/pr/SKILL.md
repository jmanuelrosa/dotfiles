---
name: pr
description: Generate the PR description from the current branch and open the PR (GitHub) or MR (GitLab), returning the URL
argument-hint: "[base-branch] [--title \"<title>\"]"
model: sonnet
disable-model-invocation: true
allowed-tools:
  - Bash(python3 *skills/pr/scripts/context.py*)
  - Bash(python3 *skills/pr/scripts/apply.py *)
  - Bash(git push *)
  - Bash(git diff *)
  - Bash(git log *)
  - Edit(//tmp/claude/**)
  - Edit(//private/tmp/claude/**)
  - Read
  - AskUserQuestion
---

# Create PR / MR

Fill the platform's PR template from the current branch's changes, push the branch, open the PR/MR, and return the URL.

Two bundled scripts do the mechanical work in one call each; don't re-run git, gh or glab for anything their output already shows.
Global install: `~/.claude/skills/pr/scripts/`; project install: `.claude/skills/pr/scripts/`.
Everything left in this file is judgment: what the description says, whether a checkbox is honest, and the push confirmation.

## Steps

1. **Gather context** (single call): `python3 ~/.claude/skills/pr/scripts/context.py [<base>] [--title "<title>"]`.
   Forward the arguments this skill was invoked with: the bare token is `<base>`, `--title` is passed through verbatim.

   It resolves the host from `origin`, the base from local `origin/HEAD` (falling back to the host CLI), the GitLab account from live `glab auth status`, and the template, then prints:

   - `== target ==`, one `KEY=value` per line: `HOST` (`gh` or `glab`), `BASE`, `BRANCH`, `BRANCH_CONVENTION`, `TYPE`, `SCOPE`, `SCOPE_CANDIDATES`, `TITLE`, `TITLE_SOURCE` (`derived`, `override` or `unresolved`), `TICKET`, `TICKET_KIND` (`jira`, `github` or `none`), `CLOSES`, and for GitLab `NS`, `GLHOST`, `REPO`.
   - `== template ==`, the discovered PR/MR template inline, or `PATH=<none>` when the repo has none.
   - `== commits ==`, `== changed files (stat) ==`, `== diff (noisy paths excluded, capped per file) ==`. Excluded and capped files still show in the stat: mention them in the description when they matter, and only run `git diff -- <path>` when one genuinely does.

   `TITLE` is final. It already applies the branch-type map, the ticket split, the scope precedence and the `(<TICKET>)` suffix rule; don't recompute or rewrite it.
   Three lines need a decision rather than a read:

   - `BRANCH_CONVENTION=nonstandard` (so `TITLE_SOURCE=unresolved`): the branch is not `<type>/<slug>` with a known type, so no title can be derived from it. Stop and ask the user to rename the branch or rerun with `--title`.
   - `SCOPE` empty with `SCOPE_CANDIDATES` listed: the diff crosses two or more areas with no clear primary. Ask the user which to use, listing the candidates, or agree it is repo-wide.
   - `GLHOST_CANDIDATES` (GitLab only, when one server backs more than one authenticated account): `AskUserQuestion` with `header: "GitLab account"`, `multiSelect: false`, one option per candidate labelled `<host> (<account>)`, defaulting to the account matching `GIT_EMAIL`. Use `<chosen host>/<NS>` as the plan's `repo` in step 4. `NOT_LOGGED_IN=<host>` instead means leave `repo` out and let glab auto-detect; if the create then fails, tell the user to run `glab auth login`.

2. **Fill the template**:
   - **Free-text sections**: clear, concise content on what the changes do and *why*. Link the ticket where relevant. When `TICKET_KIND=github`, put the `CLOSES` line (`Closes #<n>`) in the body, so merging closes the issue and advances its board card. Write that line even when `s-task` created the branch through `gh issue develop`: a linked branch already closes its issue on merge, but the keyword states the link where a reviewer sees it, and it is the only mechanism when the branch was not created that way.
   - **Checkbox sections**: check `[x]` only when the diff clearly supports it; leave `[ ]` for items not verifiable from code (e.g. "tested locally").
   - **Type/category selections**: infer from the commit prefixes in `== commits ==` (`feat:`, `fix:`, `chore:`, `ci:`, `refactor:`, …) and check all that apply.

3. **Confirm the target before pushing** (mandatory). The push in step 4 is the first outward action and the only sanctioned push path: a wrong branch means a manually-closed PR. Call `AskUserQuestion`:
   - `question`: "Push `$BRANCH` and open a PR against `$BASE`?" (interpolate the real values; for GitLab name the resolved account too, e.g. "…as `gitlab.com-work`?")
   - `header`: "PR target", `multiSelect: false`
   - `options`: `Go` (push and open the PR/MR), `Cancel` (stop, push nothing).

   The structured question *is* the gate: don't accept prose like "yes" / "go" (free-form confirmations break the `git-skill-gate` hook). On `Other` (e.g. a different base), integrate it and re-confirm.

4. **Push and open the PR/MR** (single call after `Go`). **Write** the filled description to `/tmp/claude/pr-body-<repo>-<suffix>.md` and the plan to `/tmp/claude/pr-plan-<repo>-<suffix>.json` (`<suffix>` random once per run; `/tmp/claude/` is shared across sessions). Never a HEREDOC for either: the harness escapes `!` and other shell-special characters, and the Write tool bypasses the shell.

   ```json
   {"host": "gh", "base": "main", "branch": "fix/gh-456-banner", "title": "fix(consent): banner not persisting", "body_file": "/tmp/claude/pr-body-app-a1b2c3.md"}
   ```

   `repo` is GitLab only, and only when step 1 resolved one: `"repo": "gitlab.com-work/group/project"`.

   Then run `python3 ~/.claude/skills/pr/scripts/apply.py /tmp/claude/pr-plan-<repo>-<suffix>.json`. It validates the title and body (attribution lines, em/en dashes) and the branch (`.claude/tasks/` state, cleartext secrets), pushes with `-u`, then creates the PR/MR self-assigned to `@me` and prints the URL.

   - Never `--no-verify`. On a real pre-push failure (lint, types, tests), surface the full output and stop.
   - A push that fails on auth or on a pre-push hook needing the network is the sandbox, not the branch: the sandbox only runs a command unsandboxed when its leading token is `git`, and the push `apply.py` spawns does not qualify. It prints the exact standalone `git …` command for that case. Run that command verbatim as a top-level command, then rerun `apply.py` with `--skip-push`.

5. **Print only the `Created: <url>` line** that `apply.py` wrote to stdout.

## Humanization (required)

Every word in the title or description must read like a teammate wrote it: specific, plain, honest, no AI tells.

**Vocabulary to avoid** (and their cousins): *additionally, leverage, robust, seamless, comprehensive, holistic, delve, crucial, pivotal, key, vital, intricate, tapestry, landscape (figurative), testament, underscore, highlight (verb), enduring, vibrant, foster, journey, ecosystem, empower, unlock*.

**Constructions to avoid:**

- Punctuation/format tells: em dashes between clauses, curly quotes, emojis, Title Case headings, bold-header bullets (`**Performance:** …` → write a sentence).
- False-depth phrasing: negative parallelisms ("not only X but Y"), copula avoidance (*serves as / stands as / represents* → use *is* / *has*), tail "-ing" clauses ("…ensuring scalability"), forced rule-of-three, promotional adjectives (*powerful, seamless, cutting-edge*).
- Padding: filler ("in order to" → "to", "it is important to note that"), stacked hedges ("could potentially possibly"), generic positive endings ("a major step forward"), chatbot artifacts ("I hope this helps", "Certainly!").

**Voice:** say what changed and why, not how transformative it is. Be specific about numbers, file names, and behavior. If something's incomplete, say so plainly ("doesn't cover the X case yet"). Vary sentence length; short sentences are fine.

## Rules

- `TITLE` from `context.py` is authoritative, including the invariant behind it: a Jira key becomes a `(<TICKET>)` suffix, a GitHub issue never does (GitHub appends its own `(#<pr-number>)` on squash merge, so `(#456)` in a title reads as a PR number), and an explicit `--title` is used verbatim, exempt from derivation and from the suffix rule.
- The description travels as a file, never as a shell argument: newlines and code fences survive that way, and nothing in it can reach a shell.
- Never write `Co-Authored-By: Claude …` or `🤖 Generated with …` in the title or body: `settings.json` handles attribution and `apply.py` hard-blocks both.
