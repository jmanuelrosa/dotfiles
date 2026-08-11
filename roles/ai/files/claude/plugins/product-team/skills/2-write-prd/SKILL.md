---
name: 2-write-prd
description: "Product Team stage 2 - writes the PRD from the approved brief and research: SHALL requirements each carrying WHEN/THEN scenarios with stable ids, mandatory non-goals, and no invented baselines. No gate; 3-red-team attacks it and then opens Gate 1."
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
  - Bash(gh pr list *)
  - Bash(gh pr view *)
  - Bash(gh api *)
---

# Stage 2: write the PRD

Produce `docs/initiatives/{slug}/02-prd.md` grounded in the on-disk brief and research, not in conversation memory. The PRD is what Gate 1 approves and what every later stage traces back to.

First read `../product-lead/references/conventions.md` (sibling of this skill's base directory).

## Preflight

1. Resolve the initiative (ARGUMENTS, branch, or ask).
2. Read `docs/strategy/product-team.yml` for `gate_medium` and `profile`.
3. `pt.py status {slug}`: this stage must read `ready`. Gate 0 must read `approved` in STATUS.md.
4. Read `00-brief.md` and `01-research/summary.md` fully; open the detail research files where the summary's confidence or gaps warrant it.

## Write

Fill `../product-lead/references/templates/prd.md` -> `02-prd.md`, honoring every guidance comment. The load-bearing rules:

- **Requirements carry their scenarios.** Each one is `### R{n}: {name}`, a SHALL sentence, a `Capability:` line, and at least one `#### R{n}.S{k}` block in WHEN/THEN form. The scenario is written here, not three stages later in a story, because a requirement and the test that would catch it breaking are one thought. Split apart, what goes unwritten is the ceiling on a value, the survival of data through a restart, or the state a surface reaches when it is empty.
- **A constraint is a requirement.** An unbounded value, a field with no ceiling, data that must survive something the platform can do to it (eviction under storage pressure, a cold start, a revoked permission) is a SHALL with a scenario. A property nobody wrote down is a property nobody implements: a real initiative shipped a note field whose "unbounded" was agreed in conversation and stated in no artifact.
- **Ids are stable.** `R3.S2` is claimed by stories, by tasks, by the DoR check and by the spec merge. Renumbering a requirement invalidates all four, so append rather than renumber.
- **The product must be able to report on itself.** For every metric and key result, name the requirement that makes it measurable, or say who measures it by hand. The class this pipeline most reliably drops is exactly this: how many items the thing holds, when its data was last refreshed, when a record was created. Three were missed on the first initiative, all three traceable to OKR reasoning nobody turned into a requirement.
- **Metrics**: definition, baseline, target, and how it is measured. A baseline nobody measured is written exactly as `UNKNOWN -> Open Question #n` with an owner. Inventing a baseline is the cardinal sin of this pipeline.
- **Non-goals**: minimum 3, mandatory.
- **Capabilities**: the durable kebab-case names the requirements belong to. Each becomes `docs/specs/{capability}/spec.md` at ship time, so name the lasting behaviour and never the project.
- **Target users**: only segments evidenced in `01-research/`. A segment the human wants anyway needs their explicit sign-off, recorded in the section.
- **Deferrals**: a question this PRD deliberately hands forward, per conventions.md. Forwards only, and the resolving artifact must close it.

## Handoff

Suggest `/commit` (subject `docs({slug}): stage 2 prd`) and then `/product-team:3-red-team`, which attacks this PRD and opens Gate 1 once its blockers are resolved. Do not ask for the gate decision here: a PRD that has not been read adversarially is not what Gate 1 exists to approve, and on a real initiative the gate was answered before the red team ran and the report then had to amend an already-approved PRD.

## Boundaries

- ✅ Always: a SHALL and at least one scenario per requirement; a capability per requirement; non-goals; full metric definitions; ground every section in the on-disk brief and research.
- ⚠️ Ask first: any target segment not evidenced in research; dropping a brief kill-criterion from the PRD; renumbering an existing requirement.
- 🚫 Never: invent metric baselines; include implementation detail (stage 4 owns it); write the PRD from chat history instead of the artifacts; open Gate 1 from here; write a stage-status row; run `git commit` / `git push` / `gh pr create`.
