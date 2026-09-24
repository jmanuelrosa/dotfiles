# STATUS: {initiative name}

<!-- The decisions, and only the decisions.

There used to be an eight-row stage table here, and every stage read it, wrote to it twice, and could disagree with the files on disk about what had happened. Which stage comes next is a fact about which artifacts exist, so `pt.py status {slug}` derives it and nothing maintains it.

What a file listing cannot derive is who decided a gate, why, and whether this initiative is dead. That is what stays. -->

| Field | Value |
|---|---|
| Initiative | {initiative name} |
| Slug | {slug} |
| Created | {YYYY-MM-DD} |
| Owner | {human} |

## Gates

<!-- Two gates. Gate 0 asks whether this is worth building at all, Gate 1 whether these are the right requirements, and kill is a first-class answer to both.

The Reason column is not optional and not a formality. A gate reviewed as a PR left the reviewer's thinking in the PR comments; a gate answered in session leaves nothing at all unless it is written down here, and "approved" with no reason is indistinguishable from nobody having looked. One line: what convinced them, or which concern they accepted. -->

| Gate | Status | Decided by | Date | Reason / concern accepted |
|---|---|---|---|---|
| Gate 0 | pending |  |  |  |
| Gate 1 | pending |  |  |  |

<!-- status: pending | approved | killed. A gate reviewed as a PR (gate_medium: pr) puts the PR url in the Reason column alongside the one-line summary. -->

## Skipped stages

<!-- Only when the human explicitly skipped one, with their reason. A stage skipped by nobody's decision is a stage that has not run yet, which pt.py status already reports. -->

none

## Kill reason

<!-- Filled only if killed. Keep the folder; dead ideas are institutional memory, and killing at Gate 0 is the pipeline working. -->

none
