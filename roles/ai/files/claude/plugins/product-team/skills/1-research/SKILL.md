---
name: 1-research
description: Product Team stage 1 - fans out the configured researchers (competitive, user evidence, market sizing) in parallel over an approved brief and synthesizes 01-research/summary.md with confidence levels. No gate; feeds Gate 1.
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
  - Bash(python3 *product-lead/scripts/pt.py *)
  - Bash(git status *)
  - Bash(git branch *)
  - Bash(git switch *)
  - Bash(git fetch *)
  - Bash(gh pr list *)
  - Bash(gh pr view *)
---

# Stage 1: research fan-out

Gather evidence for an approved brief by spawning the researcher agents **in parallel** (the only parallel moment in the pipeline), then synthesize their findings. No gate: this stage feeds Gate 1.

First read `../product-lead/references/conventions.md` (sibling of this skill's base directory).

## Preflight

1. Resolve the initiative: ARGUMENTS slug, the slug inferred from a `docs/{slug}-…` branch, or ask.
2. Read `docs/strategy/product-team.yml` for `roster.research` and `gate_medium`.
3. `python3 .claude/skills/product-team/skills/product-lead/scripts/pt.py status {slug}`. This stage must read `ready`; `blocked` means stop and print the artifact it names. Gate 0 must read `approved` in STATUS.md, or say what unblocks it and stop.
4. Read `docs/initiatives/{slug}/00-brief.md` fully; create `docs/initiatives/{slug}/01-research/`.

## Fan-out

Spawn every agent in `roster.research` in a single message so they run concurrently. Each dispatch prompt carries the brief path, the exact output path, and the reminder to cite URLs and cap at ~10 searches.

| Agent | Output |
|---|---|
| product-team:competitive-researcher | `01-research/competitive.md` |
| product-team:user-evidence-researcher | `01-research/user-evidence.md` |
| product-team:market-sizer | `01-research/sizing.md` |

The roster is the repo's decision, not yours: a tool with no market has nothing for a sizer to find, and dispatching one anyway buys a page of hedged prose. An agent the roster omits gets no dispatch and no file, and `summary.md` says which passes did not run so a later reader does not mistake an absent file for an empty finding. An empty roster means every pass is inline, and the summary says that too.

## Synthesize

Write `01-research/summary.md` (metadata header per conventions.md, `sources` listing the files that exist):

- One section per research file: the 3-5 findings that should shape the PRD, each with a **confidence level** (high: multiple independent sources; medium: single decent source; low: inference or thin sourcing) and links back to the detail file.
- A **contradictions** section where the researchers disagree, stated plainly.
- An **evidence gaps** section: what nobody could find, so the PRD writes honest Open Questions instead of filler. A pass the roster skipped is named here as a gap, because it is one.
- Spot-check citations: a finding whose source URL is missing or dead gets downgraded to low and flagged.

Suggest `/commit` (subject `docs({slug}): stage 1 research evidence`) and then `/product-team:2-write-prd`. Then stop.

## Boundaries

- ✅ Always: cite sources with URLs; separate evidence from inference; record per-finding confidence; name the passes the roster skipped.
- ⚠️ Ask first: any researcher needing more than ~10 searches (re-dispatch with a bigger budget only after the human agrees); web actions beyond search and fetch.
- 🚫 Never: present inference as evidence; invent market numbers or citations; dispatch an agent the roster omits; write a stage-status row; run `git commit` / `git push` / `gh pr create`.
