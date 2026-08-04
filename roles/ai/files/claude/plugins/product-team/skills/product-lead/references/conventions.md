# Product Team conventions

Shared mechanics for every stage skill. Load this file before doing anything else in a stage. Templates referenced here live in `templates/` next to this file; stage skills resolve both as siblings of their own base directory: `<skill base dir>/../product-lead/references/`.

## Artifact layout in the target repo

The pipeline scaffolds into whatever repo it runs in:

```
docs/
  ideas/                   # /idea-refine one-pagers, read by stage 0 to pre-fill
  adr/                     # NNNN-{decision-slug}.md - all ADRs, global numbering, each with an Initiative field linking it back
  strategy/
    strategy.md            # /product-team:setup-strategy
    okrs.md
  LEARNINGS.md             # appended by stage 7 retrospectives
  initiatives/{slug}/
    STATUS.md              # the state machine for this initiative
    00-brief.md
    01-research/           # competitive.md, user-evidence.md, sizing.md, summary.md
    02-prd.md
    03-red-team-report.md
    04-ux-spec.md          # ux-shaper writes it before the design doc; the design gate owner approves it
    04-design-doc.md       # its ADR index points at the ADRs in docs/adr/
    05-backlog/            # epic-{n}.md, story-{n.m}.md
    06-dor-report.md
.github/CODEOWNERS         # gate ownership, including the design owner of 04-ux-spec.md
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

Each gate gets its own branch, cut fresh from the up-to-date default branch when the gate begins. A gate PR must never carry the previous gate's already-merged commits: repos that squash-merge collapse each merged gate into a new commit that is not an ancestor of a reused branch, so a shared branch diverges and every later gate PR conflicts. A fresh branch off current `default` avoids this entirely. Branch names are deterministic per gate (`docs` prefix because initiative artifacts are all docs):

| Gate | Branch | Cut by (first stage) | Later stages on it |
|---|---|---|---|
| 0 | `docs/{slug}-gate-0-brief` | 0-refine-idea | - |
| 1 | `docs/{slug}-gate-1-prd` | 1-research (or 2-write-prd if research skipped) | 2-write-prd, 3-red-team |
| 2 | `docs/{slug}-gate-2-design` | 4-tech-shape | - |
| 3 | `docs/{slug}-gate-3-dor` | 5-decompose | 6-gate-check |
| board export | `docs/{slug}-board` | 7-push-to-board | - |

Every stage enters its gate's branch after its precondition passes: derive the name from the table. If it already exists (this gate's PR is open, or you are revising) switch to it. Otherwise cut it fresh from the default branch (resolve the default branch from the remote HEAD, e.g. `git remote show origin` / `gh repo view --json defaultBranchRef -q .defaultBranchRef.name`):

    git fetch origin
    git switch -c docs/{slug}-gate-{n}-{label} origin/{default-branch}

If the working tree is dirty with unrelated changes, stop and ask. The fresh cut is safe only because a gate's first stage runs only after the previous gate is `approved` (see reconciliation), so `origin/{default-branch}` already holds every prior gate's merged artifacts. Never rebase or reset an existing gate branch; superseded branches from merged gates are left in place (delete them by hand if you like). Strategy work uses `chore/product-strategy`.

## Gate protocol (stop before commit)

Gated stages NEVER run `git commit`, `git push`, or `gh pr create`; the human owns those through `/commit` and `/pr`. A gated stage ends by:

1. Updating its STATUS.md row to `gate-open` with note `awaiting commit + PR`.
2. Printing a handoff block:
   - files written this stage (paths);
   - suggested commit subject: `docs({slug}): gate {n} {stage name}`;
   - PR title: the same string as the commit subject above; pass it explicitly (`/pr --title "..."`) so the PR carries the clean gate-labelled subject rather than one derived from the branch name;
   - suggested PR body: what to review, the decision being gated (including "kill" as a first-class option), and a 3-5 item reviewer checklist;
   - the instruction: run `/commit`, then `/pr --title "<the commit subject above>"`, then have the gate owner review. Merge = gate passed.
3. Stopping. Do not continue to the next stage.

## Gate reconciliation

STATUS.md lags GitHub by design (the human merges outside the session). When a stage's precondition row says `gate-open`:

1. Find the PR by that gate's branch (names in the Branching table): `gh pr list --head docs/{slug}-gate-{n}-{label} --state all --json url,title,state,mergedAt`, matching the one whose title contains `gate {n}`.
2. Merged -> the gate passed. Enter THIS stage's own gate branch first (per Branching: cut it fresh from the updated default branch), then on that fresh branch update the merged gate's row to `approved`, fill gate PR URL, decided by (PR merger), date, and proceed. Recording on the fresh branch carries the approval into the next gate's PR.
3. Open -> the gate is still under review; stop and say so. The human may instead say "record approval" explicitly (e.g. approved out-of-band); note `approved by <name> without merge` and proceed.
4. Closed unmerged -> treat as a kill signal; ask the human whether to record `killed` and the reason.

## Local mode (no origin remote)

A repo with no `origin` remote (or a Product Team config whose `github_repo` is `UNSET`) runs the pipeline in local mode: same stages, same artifacts, no PR machinery.

- Gated stages end with the same handoff block minus the `/pr` step: instead of a PR review, ask the human for the gate decision directly (AskUserQuestion: proceed / kill / not yet) and record it in STATUS.md as `approved by {name} without merge (local mode)`, or `killed` with the reason. Still suggest `/commit`; local history matters.
- Skip every `gh` call (gate reconciliation, PR lookups); STATUS.md is the only record.
- Branching stays single-branch: with no remote there are no squash merges to diverge from, so every stage works on one `docs/{slug}` branch that stage 0 creates. Do not cut per-gate branches or `git fetch` (there is nothing to fetch, and a fresh cut from an unadvanced local main would drop prior gates' artifacts).
- Stage 7 needs a real `github_repo` and Project number; in local mode it refuses and says what is missing.

## Expedited path (small features)

For a small, low-risk feature the human may skip stage 1 (research) and stage 3 (red-team). Nothing else is skippable: every gate still happens, and stages 4-6 always run (the traceability chain needs the PRD's R#s).

- The skip is the human's explicit call, never the skill's. Record the skipped stage's row as `approved`, decided by the human, note `skipped (expedited): {reason}`.
- Stage 2 then writes the PRD from the brief alone: every unevidenced segment needs the explicit human sign-off stage 2 already requires, and unknown baselines still become owned Open Questions.
- If the Gate 1 review or later stages surface surprises, run the skipped stage then; its skill overwrites the skip row when it runs.

## Revision flow

Re-running a stage whose gate PR is open means "address the review". Read the comments with `gh pr view <url> --comments` (and `gh api repos/{owner}/{repo}/pulls/{n}/comments` for inline ones), address every comment in the artifact, list what changed per comment, and end with the gate protocol again (switch to that gate's existing branch per the Branching table; `/commit` + `/pr` update the open PR). Never dismiss or resolve review threads yourself.

## Interview style (setup-strategy, 0-refine-idea)

Relentless, one question at a time; wait for each answer. Recommend an answer with every question. Challenge vagueness: a number with no source, a segment with no size, an "everyone" audience all get a follow-up, not a nod. Facts findable in the repo or on disk are looked up, never asked. Decisions are the human's; never fill one in.

## Hard rules (every stage, every agent)

- Never invent metrics, baselines, market numbers, or citations. Unknown baseline -> `UNKNOWN -> Open Question #n` with an owner.
- Never present inference as evidence; label each item `evidence` or `assumption`.
- Never merge PRs, push to main, or edit an accepted ADR (supersede it with a new one; the only permitted edit to the old one is its Status line).
- Never delete an initiative folder.
- Only stage 7 touches `gh issue` / `gh project`, and only after its dry-run is confirmed.
