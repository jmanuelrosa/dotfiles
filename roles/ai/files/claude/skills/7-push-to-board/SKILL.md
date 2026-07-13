---
name: 7-push-to-board
description: Product Team stage 7 - exports the all-PASS backlog to GitHub as epic parent issues with story sub-issues on the configured Project, after a confirmed dry-run; writes issue URLs back and appends the docs/LEARNINGS.md retrospective.
argument-hint: "[initiative slug, if not inferable from the branch]"
disable-model-invocation: true
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - AskUserQuestion
  - Bash(git status *)
  - Bash(git branch *)
  - Bash(git switch *)
  - Bash(gh auth status)
  - Bash(gh pr list *)
  - Bash(gh pr view *)
  - Bash(gh label *)
  - Bash(gh issue create *)
  - Bash(gh issue view *)
  - Bash(gh project *)
  - Bash(gh api *)
---

# Stage 7: push to board + retrospective

The only stage that touches the live board. Export epics and stories as GitHub issues on the configured Project, write the URLs back, and close the loop with a retrospective. Nothing is created before the human confirms a dry-run.

First read `../product-lead/references/conventions.md` (sibling of this skill's base directory).

## Preflight (all must pass)

1. Resolve the initiative (ARGUMENTS, branch, or ask). Gate 3 `approved` in STATUS.md (reconcile per conventions.md).
2. `06-dor-report.md` says ALL PASS. Any FAIL -> refuse, point at the fix list, stop. No exceptions.
3. Read the Product Team config from this repo's CLAUDE.md: `github_repo`, `project_number`, labels. `github_repo` UNSET (local mode) -> refuse: this stage needs a real GitHub repo and Project; say what to configure. `project_number` UNSET -> ask for it and offer to record it in CLAUDE.md.
4. `gh auth status` must show the `project` scope; missing -> print `gh auth refresh -s project` for the user to run in a terminal, then stop.
5. On branch `docs/{slug}`; mark stage 7 `in-progress`.

## Dry-run (mandatory)

Build the full plan from `05-backlog/` without creating anything:

- One parent issue per epic (title from the epic file, label `initiative:{slug}`, `epic:{n}`), one issue per story (title `Story {n.m}: {title}`, body = the story file content, labels `initiative:{slug}`, `epic:{n}`, `type:story`), linked as native sub-issues of their epic.
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

## Retrospective + wrap

1. Append to `docs/LEARNINGS.md`: date, initiative, what the agents got wrong this run, which template sections caused friction, what to change before the next initiative.
2. Update STATUS.md: stage 7 -> `approved`, notes with issue counts and the Project URL.
3. Suggest `/commit` (subject `docs({slug}): board export urls and retrospective`) then `/pr` (title `Board export: {initiative name}`). Then stop.

## Boundaries

- ✅ Always: refuse on any DoR FAIL; dry-run + structured confirmation before creating anything; write URLs back; append the retrospective.
- ⚠️ Ask first: creating labels beyond the configured set; recording a Project number in CLAUDE.md.
- 🚫 Never: delete or close existing issues; touch the board without a confirmed dry-run; run `git commit` / `git push` / `gh pr create`.
