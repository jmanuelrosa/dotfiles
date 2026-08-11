---
name: 7-push-to-board
description: Product Team stage 7 - exports the all-PASS backlog to GitHub as epic parent issues with story sub-issues on the configured Project, after a confirmed dry-run, expanding each story's claimed scenarios into the issue body; writes issue URLs back. Full profile only.
argument-hint: "[initiative slug, if not inferable from the branch]"
disable-model-invocation: true
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - AskUserQuestion
  - Bash(python3 *product-lead/scripts/pt.py *)
  - Bash(git status *)
  - Bash(git branch *)
  - Bash(git switch *)
  - Bash(git fetch *)
  - Bash(gh auth status)
  - Bash(gh pr list *)
  - Bash(gh pr view *)
  - Bash(gh label *)
  - Bash(gh issue create *)
  - Bash(gh issue view *)
  - Bash(gh project *)
  - Bash(gh api *)
---

# Stage 7: push to board

The only stage that touches the live board. Export epics and stories as GitHub issues on the configured Project and write the URLs back. Nothing is created before the human confirms a dry-run.

The retrospective is no longer here. It moved to `/product-team:8-living-spec`, because a retrospective written at board-export time is written before anything has shipped, and because the `solo` profile never runs this stage and so would never get one.

First read `../product-lead/references/conventions.md` (sibling of this skill's base directory).

## Preflight (all must pass)

1. Resolve the initiative (ARGUMENTS, branch, or ask). `pt.py status {slug}` must read this stage `ready`.
2. Read `docs/strategy/product-team.yml`: `profile` must be `full` (in `solo` there is no board and no backlog, so refuse and say so), plus `github_repo`, `project_number` and `labels`. `github_repo` UNSET -> refuse: this stage needs a real GitHub repo and Project; say what to configure. `project_number` UNSET -> ask for it and offer to record it in the config file.
3. `06-dor-report.md` says ALL PASS. Any FAIL -> refuse, point at the fix list, stop. No exceptions.
4. `gh auth status` must show the `project` scope; missing -> print `gh auth refresh -s project` for the user to run in a terminal, then stop.

## Dry-run (mandatory)

Build the full plan from `05-backlog/` without creating anything:

- One parent issue per epic (title from the epic file, label `initiative:{slug}`, `epic:{n}`), one issue per story (title `Story {n.m}: {title}`, labels `initiative:{slug}`, `epic:{n}`, `type:story`), linked as native sub-issues of their epic.
- **The story body expands its claimed scenarios.** Take each `R{n}.S{k}` from the story's Scenarios row and copy that scenario's WHEN/THEN text out of `02-prd.md` into the issue, under the requirement's SHALL sentence. A story file claims ids because two copies of a scenario in the repo drift; an issue reading "satisfies R3.S1" is unreadable in the one place it is actually used, and an issue is a throwaway projection of the docs rather than a second source of truth. Also carry the task-group numbers, so the board links to the work.
- A story whose `Needs design seat` field reads `yes` also gets `needs:design`. That label is the whole point of the field: it makes design work countable on the board before anyone picks a story up, instead of surfacing when an implementer seat stops mid-task to ask for a token that does not exist.
- Labels that do not exist yet, listed as to-create.
- Every issue added to Project `{project_number}`.

Print the whole table (N issues, titles, labels, parent links), then a structured AskUserQuestion gate: `Go` (create exactly this) / `Cancel`. The structured question is the gate; free-form "ok" does not count. On `Other`, integrate the redirect and re-run the dry-run.

## Execute

1. Create missing labels (`gh label create`).
2. Create epic issues first (`gh issue create --title ... --body-file ... --label ...`), capture URLs and numbers.
3. Create story issues; each body also gets a `## Parent` line naming its epic issue (fallback convention), then link natively: `gh api graphql` with the `addSubIssue` mutation (epic issue id + story issue id via their node ids).
4. Add every issue to the Project: `gh project item-add {project_number} --owner {owner} --url {issue_url}`.
5. Write each issue URL into its story file's Board issue field and each epic's URL into `epic-{n}.md`.
6. Failures mid-run: stop, report exactly what was and was not created; re-running must skip issues whose story files already carry a Board issue URL (idempotent resume).

## Wrap

1. Report the issue counts and the Project URL.
2. Suggest `/commit` (subject `docs({slug}): board export urls`). Then stop.

The board issue urls written back into the story files are what make `pt.py status` read this stage done, so there is no status row to write.

## Boundaries

- ✅ Always: refuse on any DoR FAIL; dry-run + structured confirmation before creating anything; expand claimed scenarios into the issue body; write URLs back.
- ⚠️ Ask first: creating labels beyond the configured set; recording a Project number in the config file.
- 🚫 Never: delete or close existing issues; touch the board without a confirmed dry-run; push an issue body that names scenario ids without their text; write a stage-status row; run `git commit` / `git push` / `gh pr create`.
