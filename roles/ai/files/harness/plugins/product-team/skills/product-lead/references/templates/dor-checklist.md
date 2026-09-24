# Definition of Ready checklist

<!-- Run by /product-team:6-verify. Split by who can decide each item, because that split is what stopped this being a $21.92 Opus pass over a backlog: a set difference is not a judgment, and asking a model to perform one is how three initiatives in a row failed the gate on the same lexical defect.

`pt.py check {slug}` decides the first group and exits non-zero on any finding. The model decides the second group and never re-does the first. Neither ever fixes what it finds: 6-verify is a checker, and a fix belongs to the skill that owns the artifact. -->

## Decided by `pt.py check` (run it first; do not re-check these by hand)

- [ ] **Scenario ids resolve**: every scenario a story or task claims is defined in 02-prd.md.
- [ ] **Coverage is complete**: every scenario 02-prd.md defines is claimed by at least one story or task. This is the item nothing used to check, and the one that catches a requirement nobody implemented.
- [ ] **Every requirement is testable at all**: no requirement carries zero scenarios.
- [ ] **Design pointer resolves**: each story's Design/UX note anchors at a heading that really exists in 04-ux-spec.md.
- [ ] **Design seat flag set**: `Needs design seat` reads yes or no.
- [ ] **Size hint present**, and an `L` carries its split rationale.
- [ ] **Dependencies flagged**: `Depends on` is filled (a story with none says `none`) and no cycle exists.
- [ ] **Deferrals are closed**: every deferral points forward at a real artifact, and that artifact settles it.

## Decided by the model

- [ ] **Scenarios are testable**: each `THEN` names something observable (a response, a stored record, a rendered state), never "works correctly". A scenario id that resolves is not the same as a scenario worth having, which is why this item cannot move up.
- [ ] **Slices are vertical**: each story cuts through every layer and is demoable alone. A story that only touches one layer is a task in some other story.
- [ ] **The task list runs from nothing to shipped**: a group for getting it built, a group for getting it deployed, a group for accepting it in the place it runs, or an explicit line saying why one does not apply.
- [ ] **No unowned open question** in 02-prd.md touches a requirement this backlog implements.

Report format (`06-dor-report.md`): the script's findings verbatim, then one PASS/FAIL line per story for the model's items, and for every FAIL a concrete fix list naming the file and the failing item. No "PASS with notes".
