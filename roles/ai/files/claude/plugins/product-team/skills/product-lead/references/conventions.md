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
    product-team.yml       # profile, gate medium, gate owners, roster
  specs/{capability}/spec.md  # living capability specs, merged at ship time from shipped requirements
  LEARNINGS.md             # appended by /product-team:8-living-spec at ship time
  initiatives/{slug}/
    STATUS.md              # gate decisions and kills only; stage order is derived, see below
    00-brief.md
    01-research/           # competitive.md, user-evidence.md, sizing.md, summary.md
    02-prd.md              # SHALL requirements, each with scenarios: R{n}.S{k}
    03-red-team-report.md
    04-ux-spec.md          # ux-shaper writes it before the design doc
    04-design-doc.md       # its ADR index points at the ADRs in docs/adr/
    05-tasks.md            # the whole build, dependency-ordered, from empty repo to accepted
    05-backlog/            # epic-{n}.md, story-{n.m}.md - thin board headers; absent in the solo profile
    06-dor-report.md       # full profile only
.github/CODEOWNERS         # gate ownership, and docs/adr/ so an ADR still needs an approver
```

Slug rule: lowercase, `a-z0-9-` only, words joined by single hyphens, max 40 chars, derived from the idea's core noun phrase (`"let customers export their data as CSV"` -> `csv-data-export`).

Every artifact starts with the YAML metadata header its template defines (`initiative`, `stage`, `status`, `authors`, `date`, `sources`). Authors list both the human and the producing skill or agent. Dates are absolute (YYYY-MM-DD). That header is also the only record of when a stage ran, now that STATUS.md no longer tracks transitions, so it is not decoration.

## The config file

`docs/strategy/product-team.yml`, scaffolded by `/product-team:setup-strategy` from `templates/config.yml`. Read it in every stage's preflight. It decides four things a stage would otherwise have to guess: the `profile`, the `gate_medium`, the `gate_owners`, and the `roster` of agents that take part.

It is not in CLAUDE.md, and that is deliberate: CLAUDE.md is loaded on every turn of every session in the repo, so a config block there is paid for by every conversation that has nothing to do with this pipeline.

A missing config file means the defaults: `profile: full`, `gate_medium: session`, `github_repo: UNSET`, the full roster.

## Stage order is derived, not tracked

```
python3 .claude/skills/product-team/skills/product-lead/scripts/pt.py status {slug}
```

That prints every stage as `done`, `partial`, `ready` or `blocked`, plus the next command. It reads the files on disk, so it cannot disagree with them. Use it in preflight instead of reading a stage table, and never write a stage row anywhere.

A stage refuses to run when `pt.py status` reports it `blocked`: print the blocking artifact and the command that produces it, then stop. `partial` is not blocked and is not a reason to re-run a stage: it means an older initiative completed that stage before one of its artifacts existed, and the missing file is named so nobody has to guess.

The same script owns two other jobs:

| Command | Used by |
|---|---|
| `pt.py check {slug}` | `/product-team:6-verify`, before it judges anything |
| `pt.py spec-merge {slug}` | `/product-team:8-living-spec`, at ship time |

`check` exits non-zero when it has findings. Run it and quote it; never re-decide by hand what it has already decided, and never fix what it reports from inside a checking stage.

## Two gates

| Gate | Question | Opened by | Kill is an answer |
|---|---|---|---|
| Gate 0 | Is this worth building at all? | `0-refine-idea` | yes, and killing here is the pipeline working |
| Gate 1 | Are these the right requirements? | `2-write-prd` | yes |

There is no design gate and no Definition of Ready gate. The design gate went because the open decisions at stage 4 resolve with no human in the loop, and the ones that do not are reached at implementation whether or not a gate sat there; `docs/adr/` under CODEOWNERS is what keeps the hard-to-reverse half of stage 4 reviewed. The DoR gate went because across three initiatives it produced one repeated mechanical defect, which `pt.py check` now catches for nothing.

Every gate records its decision **and its reason** in STATUS.md. A gate answered in session leaves no PR comments behind, so an "approved" with no reason is indistinguishable from nobody having read it.

### gate_medium: session (the default)

The stage ends by asking the human directly with `AskUserQuestion`: proceed, kill, or not yet. Then:

1. Record the answer in the STATUS.md gate row: status, decided by, date, and one line on what convinced them or which concern they accepted.
2. Suggest `/commit` (subject `docs({slug}): gate {n} {stage name}`). Local history is the artifact trail.
3. Stop. Do not continue into the next stage in the same turn.

No branch, no PR, no `gh` calls.

### gate_medium: pr

Each gate gets its own branch, cut fresh from the up-to-date default branch when the gate begins. A gate PR must never carry the previous gate's already-merged commits: repos that squash-merge collapse each merged gate into a new commit that is not an ancestor of a reused branch, so a shared branch diverges and every later gate PR conflicts.

| Gate | Branch |
|---|---|
| 0 | `docs/{slug}-gate-0-brief` |
| 1 | `docs/{slug}-gate-1-prd` |

Switch to the branch if it exists (this gate's PR is open, or you are revising), otherwise cut it fresh from the default branch:

    git fetch origin
    git switch -c docs/{slug}-gate-{n}-{label} origin/{default-branch}

Resolve the default branch from the remote (`gh repo view --json defaultBranchRef -q .defaultBranchRef.name`). Where `git fetch` cannot reach the remote, compare local `HEAD` against `gh api repos/{repo}/commits/{default} -q .sha` and cut from the local default branch once they match; a machine with working SSH should keep using the fetch.

The stage then ends by updating the gate row to `pending` with the PR url, printing a handoff block (files written, the commit subject above, the same string as the PR title, a suggested body naming the decision being gated including kill, and a 3 to 5 item reviewer checklist), and stopping. The human runs `/commit`, then `/pr --title "<subject>"`. Merge is the gate passing, and the next stage records it: find the PR with `gh pr list --head docs/{slug}-gate-{n}-{label} --state all --json url,title,state,mergedAt`, then write status, decider, date and reason into the gate row. Closed unmerged is a kill signal: ask before recording it.

Gated stages never run `git commit`, `git push` or `gh pr create` under either medium.

## Deferrals

An artifact may hand a question forward to one that runs after it, instead of guessing or hedging. That is the whole mechanism, and it exists so an upstream artifact can stop pretending to answer something it cannot: a UX spec should not be inventing pagination semantics, and a PRD should not be choosing an encoder.

- Declare it in a `## Deferrals` table: an id (`D1`), the question, and the resolving artifact.
- **Forwards only.** The resolver must run after the artifact raising it, in the order `02-prd.md`, `04-ux-spec.md`, `04-design-doc.md`, `05-tasks.md`. Pointing sideways or back is a hole with a label on it, because nothing upstream will run again to close it.
- The resolving stage **must** close every deferral aimed at it: name the id, and either decide it or restate it as an open question with an owner. `04-design-doc.md` has a table for exactly this.
- `pt.py check` fails the initiative on a deferral that is unclosed, points the wrong way, or names something that is not an artifact.

A deferral is closed by the next artifact. An open question is closed by a person. Do not use one for the other.

## Profiles

`profile: full` runs everything. `profile: solo` keeps every stage that produces findings and both gates, and drops the board-facing half:

| Dropped in solo | Why it is safe |
|---|---|
| `05-backlog/` stories and epics | `05-tasks.md` already carries the work, ordered; stories exist to be put on a board |
| `/product-team:6-verify` | its script half still runs on demand; there is no gate for it to feed |
| `/product-team:7-push-to-board` | there is no board |
| PR machinery | `gate_medium: session` |

Nothing that produces a finding is dropped, and that is the point. Research and red-team together are 13% of the cost and produced the decision-changing findings on every initiative that ran, so a profile that skipped them would save nothing worth having. There is no shorter path than `solo`, and no stage is individually skippable: a skip is a human decision recorded in STATUS.md's Skipped stages section with its reason, never a skill's own call.

## Revision flow

Re-running a stage after Gate 1 is answered means "address the review". Under `session`, read the recorded reason and concerns from the gate row. Under `pr` with the PR still open, read the comments with `gh pr view <url> --comments` (and `gh api repos/{owner}/{repo}/pulls/{n}/comments` for inline ones), address every comment in the artifact, list what changed per comment, and end with the gate protocol again. Never dismiss or resolve review threads yourself.

## Interview style (setup-strategy, 0-refine-idea)

Relentless, one question at a time; wait for each answer. Recommend an answer with every question. Challenge vagueness: a number with no source, a segment with no size, an "everyone" audience all get a follow-up, not a nod. Facts findable in the repo or on disk are looked up, never asked. Decisions are the human's; never fill one in.

## Hard rules (every stage, every agent)

- Never invent metrics, baselines, market numbers, or citations. Unknown baseline -> `UNKNOWN -> Open Question #n` with an owner.
- Never present inference as evidence; label each item `evidence` or `assumption`.
- Never merge PRs, push to main, or edit an accepted ADR (supersede it with a new one; the only permitted edit to the old one is its Status line).
- Never delete an initiative folder.
- Never write a stage-status row; `pt.py status` derives it and a hand-written one can only be wrong.
- Only stage 7 touches `gh issue` / `gh project`, and only after its dry-run is confirmed.
