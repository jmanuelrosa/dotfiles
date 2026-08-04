# Definition of Ready checklist

<!-- Run by /product-team:6-gate-check against EVERY story file in 05-backlog/. A story passes only with every item checked; any unchecked item means FAIL, no exceptions, no auto-fixing. -->

Per story:

- [ ] **ACs present & testable**: at least one Given/When/Then block with an AC id; each Then is observable, not "works correctly".
- [ ] **PRD traceability**: every AC and the story itself reference existing R# ids that appear in 02-prd.md.
- [ ] **Dependencies flagged**: the Depends-on field is filled (a story with none says `none`), and no dependency cycle exists across the backlog.
- [ ] **Design pointer resolves**: the Design/UX note points at a section that exists in `04-ux-spec.md` (a flow anchor, or that spec's "No user-facing surface" argument). Follow the pointer and check; a dangling anchor fails, and so does any freehand "N/A because ..." written in the story instead of a pointer.
- [ ] **Design seat flag set**: the `Needs design seat` field reads `yes` or `no`, and `yes` iff the story's flow draws on the UX spec's "New system pieces needed" section. Blank fails.
- [ ] **No unowned open questions**: no open question in 02-prd.md that touches this story's requirements is missing an owner.
- [ ] **Size hint present**: S, M, or L. An L should carry a note on why it was not split.

Report format (06-dor-report.md): one PASS/FAIL line per story, and for every FAIL a concrete fix list naming the file and the failing item.
