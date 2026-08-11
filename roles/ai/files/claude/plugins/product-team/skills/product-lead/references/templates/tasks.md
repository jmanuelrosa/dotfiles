---
initiative: "{slug}"
stage: 5-decompose
status: draft
authors: ["5-decompose"]
date: "{YYYY-MM-DD}"
sources: ["02-prd.md", "04-ux-spec.md", "04-design-doc.md"]
---

# Tasks: {initiative name}

<!-- The whole build, in the order it can be built, one line per task.

This is the layer the pipeline used to leave out. Stories are board items for humans and are sliced by user value, so nothing in them could ever describe setting the project up or getting it deployed: a story must trace to a requirement, and no requirement asks for a toolchain. The work still had to happen, so it was rediscovered at implementation time by whoever got there first.

Ordering is by dependency, so following the list top to bottom works. Every task names what it serves: a scenario id (R3.S1) for behaviour, or a design decision (D5) for a technical choice. A task that can name neither is either infrastructure, which is fine and says so, or scope nobody asked for.

Keep each line to one session's work and make it verifiable: you can tell when it is done. `- [ ]` is load-bearing, because pt.py reads the checkboxes to decide which requirements have shipped and are ready to merge into docs/specs/. -->

## 1. Toolchain and skeleton

<!-- From an empty checkout to something that builds and runs. Absent only when the project already exists, and then say so on one line rather than deleting the group. -->

- [ ] 1.1 {task} (infrastructure)

## 2. {Capability or layer}

- [ ] 2.1 {task} (R{#}.S{#})
- [ ] 2.2 {task} (D{#})

## {n}. Deployment

<!-- How this reaches an environment where a user meets it, and what refuses to publish when it is invalid. The measured gap this group closes was a validation that ran only on a developer's machine, so nothing stopped a bad artifact reaching production. -->

- [ ] {n}.1 {task}

## {n+1}. Acceptance

<!-- Proving the thing works in the place it actually runs, as opposed to in a test. The last group on purpose: an initiative whose final task is "write the tests" has no step where anyone looks at it. -->

- [ ] {n+1}.1 {task} (R{#}.S{#})

<!-- No Deferrals section here, deliberately: this is the last artifact, so there is nothing downstream to hand a question to. An unknown that survives to this point is an open question for a person, and it belongs in 02-prd.md's Open questions table with an owner. -->
