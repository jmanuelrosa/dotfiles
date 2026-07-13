---
name: 1-research
description: Product Team stage 1 - fans out three parallel researchers (competitive, user evidence, market sizing) over an approved brief and synthesizes 01-research/summary.md with confidence levels. No gate; feeds Gate 1.
argument-hint: "[initiative slug, if not inferable from the branch]"
disable-model-invocation: true
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - AskUserQuestion
  - Agent
  - Bash(git status *)
  - Bash(git branch *)
  - Bash(git switch *)
  - Bash(gh pr list *)
  - Bash(gh pr view *)
---

# Stage 1: research fan-out

Gather evidence for an approved brief by spawning the three researcher agents **in parallel** (the only parallel moment in the pipeline), then synthesize their findings. No gate: this stage feeds Gate 1 (the PRD review).

First read `../product-lead/references/conventions.md` (sibling of this skill's base directory).

## Preflight

1. Resolve the initiative: ARGUMENTS slug, or the current `docs/{slug}` branch, or ask.
2. Precondition per conventions.md: STATUS.md stage 0 must be `approved` (reconcile a `gate-open` row against the merged Gate 0 PR first). Not approved -> stop and say what unblocks it.
3. Ensure you are on `docs/{slug}`; mark stage 1 `in-progress`.
4. Read `docs/initiatives/{slug}/00-brief.md` fully; create `docs/initiatives/{slug}/01-research/`.

## Fan-out

Spawn all three agents in a single message so they run concurrently. Each dispatch prompt carries: the brief path, the exact output path, and the reminder to cite URLs and cap at ~10 searches.

| Agent | Output |
|---|---|
| competitive-researcher | `01-research/competitive.md` |
| user-evidence-researcher | `01-research/user-evidence.md` |
| market-sizer | `01-research/sizing.md` |

## Synthesize

Write `01-research/summary.md` (metadata header per conventions.md, `sources` listing the three files):

- One section per research file: the 3-5 findings that should shape the PRD, each with a **confidence level** (high: multiple independent sources; medium: single decent source; low: inference or thin sourcing) and links back to the detail file.
- A **contradictions** section where the researchers disagree, stated plainly.
- An **evidence gaps** section: what nobody could find, so the PRD writes honest Open Questions instead of filler.
- Spot-check citations: a finding whose source URL is missing or dead gets downgraded to low and flagged.

Update STATUS.md: stage 1 -> `approved`, decided by `n/a (no gate)`, note the summary path. Suggest `/commit` (subject `docs({slug}): stage 1 research evidence`) and then `/2-write-prd`; no PR until Gate 1.

## Boundaries

- ✅ Always: cite sources with URLs; separate evidence from inference; record per-finding confidence.
- ⚠️ Ask first: any researcher needing more than ~10 searches (re-dispatch with a bigger budget only after the human agrees); web actions beyond search and fetch.
- 🚫 Never: present inference as evidence; invent market numbers or citations; run `git commit` / `git push` / `gh pr create`.
