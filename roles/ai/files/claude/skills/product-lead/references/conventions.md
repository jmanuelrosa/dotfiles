# Product Team conventions

Shared mechanics for every stage skill. Load this file before doing anything else in a stage. Templates referenced here live in `templates/` next to this file; stage skills resolve both as siblings of their own base directory: `<skill base dir>/../product-lead/references/`.

## Artifact layout in the target repo

The pipeline scaffolds into whatever repo it runs in:

```
docs/
  ideas/                   # /idea-refine one-pagers, read by stage 0 to pre-fill
  adr/                     # NNNN-{decision-slug}.md - all ADRs, global numbering, each with an Initiative field linking it back
  strategy/
    strategy.md            # /setup-strategy
    okrs.md
  LEARNINGS.md             # appended by stage 7 retrospectives
  initiatives/{slug}/
    STATUS.md              # the state machine for this initiative
    00-brief.md
    01-research/           # competitive.md, user-evidence.md, sizing.md, summary.md
    02-prd.md
    03-red-team-report.md
    04-design-doc.md       # its ADR index points at the ADRs in docs/adr/
    05-backlog/            # epic-{n}.md, story-{n.m}.md
    06-dor-report.md
.github/CODEOWNERS         # gate ownership
```

Slug rule: lowercase, `a-z0-9-` only, words joined by single hyphens, max 40 chars, derived from the idea's core noun phrase (`"let customers export their data as CSV"` -> `csv-data-export`).

Every artifact starts with the YAML metadata header its template defines (`initiative`, `stage`, `status`, `authors`, `date`, `sources`). Authors list both the human and the producing skill or agent. Dates are absolute (YYYY-MM-DD).

## STATUS.md is the state machine

Statuses per stage: `pending | in-progress | gate-open | approved | killed`.

- A stage skill MUST refuse to run if its predecessor's row is not `approved` (see reconciliation below for the one exception). Print the blocking row and the command or review that unblocks it, then stop.
- Every stage updates its own row when it starts (`in-progress`) and when it hands off (`gate-open` for gated stages, `approved` with note `no gate` for ungated ones).
- Ungated stages (1-research, 3-red-team, 5-decompose) feed the next gate; they mark themselves `approved` directly, `decided by: n/a (no gate)`.
- Killed: the human can kill at any gate. Record `killed` on the current stage row, fill the kill reason field, and leave the whole folder in place forever. Institutional memory of dead ideas is a feature. Killing at Gate 0 is success, not failure.

## Branching

All work for an initiative happens on `docs/{slug}` (initiative artifacts are all docs, hence the `docs` prefix). Stage 0 creates it from the default branch with `git switch -c`. Later stages verify they are on it (`git branch --show-current`) and switch to it if not; if the working tree is dirty with unrelated changes, stop and ask. Strategy work uses `chore/product-strategy`.

Gate PRs all originate from this one branch: each gate is a new PR containing the commits since the previous gate merged.

## Gate protocol (stop before commit)

Gated stages NEVER run `git commit`, `git push`, or `gh pr create`; the human owns those through `/commit` and `/pr`. A gated stage ends by:

1. Updating its STATUS.md row to `gate-open` with note `awaiting commit + PR`.
2. Printing a handoff block:
   - files written this stage (paths);
   - suggested commit subject: `docs({slug}): gate {n} {stage name}`;
   - PR title: the same string as the commit subject above (the initiative branch is shared across gates, so the title must carry the gate; pass it explicitly because `/pr` otherwise derives a generic branch-based title);
   - suggested PR body: what to review, the decision being gated (including "kill" as a first-class option), and a 3-5 item reviewer checklist;
   - the instruction: run `/commit`, then `/pr --title "<the commit subject above>"`, then have the gate owner review. Merge = gate passed.
3. Stopping. Do not continue to the next stage.

## Gate reconciliation

STATUS.md lags GitHub by design (the human merges outside the session). When a stage's precondition row says `gate-open`:

1. Find the PR: `gh pr list --head docs/{slug} --state all --json url,title,state,mergedAt`, matching the one whose title contains `gate {n}`.
2. Merged -> update the row to `approved`, fill gate PR URL, decided by (PR merger), date, then proceed.
3. Open -> the gate is still under review; stop and say so. The human may instead say "record approval" explicitly (e.g. approved out-of-band); note `approved by <name> without merge` and proceed.
4. Closed unmerged -> treat as a kill signal; ask the human whether to record `killed` and the reason.

## Local mode (no origin remote)

A repo with no `origin` remote (or a Product Team config whose `github_repo` is `UNSET`) runs the pipeline in local mode: same stages, same artifacts, no PR machinery.

- Gated stages end with the same handoff block minus the `/pr` step: instead of a PR review, ask the human for the gate decision directly (AskUserQuestion: proceed / kill / not yet) and record it in STATUS.md as `approved by {name} without merge (local mode)`, or `killed` with the reason. Still suggest `/commit`; local history matters.
- Skip every `gh` call (gate reconciliation, PR lookups); STATUS.md is the only record.
- Stage 7 needs a real `github_repo` and Project number; in local mode it refuses and says what is missing.

## Expedited path (small features)

For a small, low-risk feature the human may skip stage 1 (research) and stage 3 (red-team). Nothing else is skippable: every gate still happens, and stages 4-6 always run (the traceability chain needs the PRD's R#s).

- The skip is the human's explicit call, never the skill's. Record the skipped stage's row as `approved`, decided by the human, note `skipped (expedited): {reason}`.
- Stage 2 then writes the PRD from the brief alone: every unevidenced segment needs the explicit human sign-off stage 2 already requires, and unknown baselines still become owned Open Questions.
- If the Gate 1 review or later stages surface surprises, run the skipped stage then; its skill overwrites the skip row when it runs.

## Revision flow

Re-running a stage whose gate PR is open means "address the review". Read the comments with `gh pr view <url> --comments` (and `gh api repos/{owner}/{repo}/pulls/{n}/comments` for inline ones), address every comment in the artifact, list what changed per comment, and end with the gate protocol again (same branch: `/commit` + `/pr` update the open PR). Never dismiss or resolve review threads yourself.

## Interview style (setup-strategy, 0-refine-idea)

Relentless, one question at a time; wait for each answer. Recommend an answer with every question. Challenge vagueness: a number with no source, a segment with no size, an "everyone" audience all get a follow-up, not a nod. Facts findable in the repo or on disk are looked up, never asked. Decisions are the human's; never fill one in.

## Hard rules (every stage, every agent)

- Never invent metrics, baselines, market numbers, or citations. Unknown baseline -> `UNKNOWN -> Open Question #n` with an owner.
- Never present inference as evidence; label each item `evidence` or `assumption`.
- Never merge PRs, push to main, or edit an accepted ADR (supersede it with a new one; the only permitted edit to the old one is its Status line).
- Never delete an initiative folder.
- Only stage 7 touches `gh issue` / `gh project`, and only after its dry-run is confirmed.
