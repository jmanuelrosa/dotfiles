# Bundle registry metadata

## Decisions

Bundle catalog policy belongs in `roles/ai/files/harness/kura/catalog/bundle-registry.json`, matching the skill and agent registries.
Each entry carries `groups`; append `global` last to select machine scope, with no separate boolean.
`bundle.json` keeps identity, descriptive metadata, and `requires`.
Preserve every existing group and leave all shipped bundles project-scoped.
The user approved preparing only the dotfiles migration; Kura implementation and the release-pin update are prerequisites, not part of this change.

The planning skill's separate task files are replaced by the ordered checklist here, satisfying its task-recording check within the repository's dated plan convention.
The existing `.gitignore` excludes plans despite the plan documentation; make only this referenced migration plan trackable, leaving the other plans ignored.
The skill-writer description-optimization and new maintenance-artifact steps are not needed: replace existing packaging guidance without changing the skill's trigger, layout, or authoring scope.

## Ordered tasks

- [x] Move the 17 bundle group arrays into their existing registry entries without changing tags, identities, or requirements.
- [x] Update registry documentation and the agent-writer packaging template and verification guidance.
- [x] Add catalog tests for registry coverage, exclusive group ownership, valid tags, and unchanged project scope; run `make test`.
- [ ] In the Kura repository, accept and validate bundle registry `groups`, expose them through group browsing, and derive scope from the final `global` tag.
- [ ] In Kura, resolve global bundles as their owned agents and skills plus required catalog artifacts and transitive skill dependencies; verify shared members, pruning, and idempotent convergence.
- [ ] Release Kura support, update `KURA.release` and its checksum here, and add the bundle registry schema reference once its schema supports `groups`.
- [ ] Validate live bundle listing and group filters with that release; verify global bundle convergence in isolated fixtures before using machine views.

## Compatibility boundary

The pinned Kura v0.7.0 does not consume bundle registry metadata and reports empty bundle groups and `global: false`.
The newer local Kura checkout currently rejects `groups` in bundle registry entries.
This migration is staged, not a usable Kura feature yet.
Do not run catalog commands with that registry-enforcing build until its support lands.
Do not change the release pin or run live `sync` or `converge` as part of this preparation.

## Verification

All registry names must match shipped bundle directory and manifest names.
Every registered bundle must carry a nonempty, deduplicated group array; manifests must carry neither groups nor scope policy.
No shipped bundle gains `global`.
Existing manifest metadata and requirements must remain unchanged.
Run the focused Kura-role suite and the full suite through `make test`.
A passing dotfiles suite verifies catalog structure, not Kura runtime support.

## Validation results

The focused Kura-role suite passed: 30 tests.
A before/after comparison confirmed all 17 tag arrays and all remaining manifest metadata are unchanged.
The agent-writer structural validator passed with no warnings.
Tests used cached dependencies with `UV_OFFLINE=1` after the default invocation could not reach PyPI.
The full suite stopped after 346 passes at `test_detached_sdk_runner_records_terminal_goal_outcomes[responses2-4-blocked-2]`: its minion runner remained `running` instead of reaching `blocked` within the test's deadline.
No minion files were changed, and debugging that failure is outside this metadata preparation.
