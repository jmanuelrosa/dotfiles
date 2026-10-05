# Codegen and generated artifacts

When to read: the brief or diff touches generated clients or types (OpenAPI/GraphQL/Prisma/protobuf), codegen config, or checked-in generated files.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Generated code hand-edited.** An edit made directly in a generated file is lost on the next regeneration, and reviewers cannot tell source from output.
  Check: generated files are clearly marked and never hand-edited; customization lives in inputs or post-generation hooks, not in the output.
- **Drift between schema and generated client.** A committed generated client that is not regenerated when its schema changes compiles against a contract that no longer exists.
  Check: regeneration is reproducible from the current schema, and a check fails when the committed output differs from a fresh generate, flagging newly generated untracked files, not only modifications to tracked ones.
- **Generation not reproducible.** Codegen that depends on network state, wall-clock, or an unpinned generator version produces a different artifact each run, so the diff is noise.
  Check: the generator version is pinned and generation from the same input is byte-stable.
- **Generated output outside the type graph.** Generated code excluded from typecheck hides breakages until runtime; included without a style exemption, it floods the diff with lint noise.
  Check: generated output is typechecked so drift breaks the build, but exempt from style lint via an explicit ignore, not deletion.
- **Committed and rebuilt at once.** An artifact both committed and regenerated during the build can disagree, and reviewers trust the wrong copy.
  Check: each artifact is either committed-and-verified or build-time-only, not both; the choice is explicit and consistent.
- **Regeneration is a manual ritual.** Codegen that requires remembering a command drifts the moment someone forgets.
  Check: regeneration is a single discoverable task wired into the affected build graph, and drift is caught by a check, not a reviewer's eye.
- **Breaking output change unversioned.** A generator upgrade that changes output shape (renamed types, different nullability) breaks consumers with no signal.
  Check: generator upgrades that change output are treated as a contract change, reviewed, with consumers updated in the same change.
- **Environment baked into output.** Generation that embeds an endpoint, token, or environment-specific value into a committed artifact leaks it and pins the artifact to one environment.
  Check: generated output is environment-neutral; environment values are injected at runtime, never generated in.

## Escalation triggers (`needs-decision`)

- Adding a new codegen tool or generator to the repo (also an ask-first boundary in the agent).
- A generator upgrade whose output change breaks a published or cross-package contract.

## What good looks like

- `generate` is one reproducible task, and drift is caught by a check that diffs fresh output against the committed copy.
- Generated files are unmistakable, typechecked, and never hand-edited.
- Consumers of a generated contract break loudly at build time when the source changes.
