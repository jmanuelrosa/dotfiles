# STATUS: {initiative name}

<!-- The state machine for this initiative. Every stage skill reads this before running and updates it before stopping. Humans and agents both treat it as the single source of truth; GitHub is reconciled into it, never the other way around. -->

| Field | Value |
|---|---|
| Initiative | {initiative name} |
| Slug | {slug} |
| Branch | docs/{slug} |
| Created | {YYYY-MM-DD} |
| Owner | {human} |

## Stages

<!-- status: pending | in-progress | gate-open | approved | killed -->

| Stage | Status | Gate PR | Decided by | Date | Notes |
|---|---|---|---|---|---|
| 0-brief (Gate 0) | in-progress |  |  |  |  |
| 1-research | pending |  |  |  | no gate, feeds Gate 1 |
| 2-prd (Gate 1) | pending |  |  |  |  |
| 3-red-team | pending |  |  |  | no gate, feeds Gate 1 |
| 4-tech-shape (Gate 2) | pending |  |  |  |  |
| 5-decompose | pending |  |  |  | no gate, feeds Gate 3 |
| 6-gate-check (Gate 3) | pending |  |  |  |  |
| 7-push-to-board | pending |  |  |  | dry-run confirm, no PR gate |

## Kill reason

<!-- Filled only if killed. Keep the folder; dead ideas are institutional memory. -->

none
