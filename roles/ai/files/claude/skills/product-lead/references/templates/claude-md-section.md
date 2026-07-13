<!-- Appended to the target repo's CLAUDE.md by /setup-strategy. Fill every {placeholder}; values marked UNSET are provided later (project number can wait until stage 7). -->

## Product Team

This repo runs the Product Team pipeline (run `/product-lead` for the guide and current status). `docs/initiatives/{slug}/STATUS.md` is the state machine: stage skills refuse to run unless the predecessor gate is `approved` there. Each initiative lives on branch `docs/{slug}`; every gate is a PR reviewed by the owners below.

### Config

| Key | Value |
|---|---|
| github_repo | {owner/repo, or UNSET (local mode)} |
| project_number | {N or UNSET} |
| epic_convention | parent issues with native sub-issues |
| labels | `initiative:{slug}`, `epic:{n}`, `type:story` |
| gate_owners | Gates 0/1/3 (PM): {@handle} - Gate 2 (tech lead): {@handle} - Strategy: {@handle} |
| extra_codebase_paths | {paths /4-tech-shape may read beyond this repo, or none} |

### Boundaries

- Never merge gate PRs or push to main; humans decide gates.
- Never edit an accepted ADR; supersede it with a new one.
- Never invent metrics, baselines, market numbers, or citations; unknowns become owned Open Questions.
- Never delete an initiative folder; killed initiatives keep their folder and kill reason in STATUS.md.
