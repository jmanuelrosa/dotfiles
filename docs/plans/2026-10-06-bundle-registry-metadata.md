# Bundle registry metadata

## Current status

[Kura v0.9.0](https://github.com/jmanuelrosa/kura/releases/tag/v0.9.0) is now pinned with its verified release checksum and supports descriptive groups in local and upstream bundle registry rows.
All 17 historical bundle group arrays are restored in `bundle-registry.json` without changing tags, identities, or requirements.
Groups support filtering, grouping, and project selection; they are not inherited by bundle-owned artifacts and do not select install scope.
Bundle rows still omit `global`, `dependencies`, and `dependency_only`, and the retired `global` group tag remains forbidden.
All bundles stay project-scoped; the original global-bundle proposal below is superseded.
Skill and standalone-agent global roots and dependencies are unchanged.
Run `make run-role ROLE=ai` to install v0.9.0 before using this catalog; no live catalog mutations are part of this update.

Decisions: skill-writer requested description optimization and maintenance artifacts; Tier 2 satisfies the trigger and contract checks with unchanged `SKILL.md` and registration, replacing only obsolete packaging guidance in the existing references.
The skill-writer completion template is overridden by the harness output contract; no extra report sections are added.

## Original decisions (superseded)

Bundle catalog policy belongs in `roles/ai/files/harness/kura/catalog/bundle-registry.json`, matching the skill and agent registries.
Each entry carries `groups`; append `global` last to select machine scope, with no separate boolean.
`bundle.json` keeps identity, descriptive metadata, and `requires`.
Preserve every existing group and leave all shipped bundles project-scoped.
The user approved preparing only the dotfiles migration; Kura implementation and the release-pin update are prerequisites, not part of this change.

The planning skill's separate task files are replaced by the ordered checklist here, satisfying its task-recording check within the repository's dated plan convention.
The existing `.gitignore` excludes plans despite the plan documentation; make only this referenced migration plan trackable, leaving the other plans ignored.
The skill-writer description-optimization and new maintenance-artifact steps are not needed: replace existing packaging guidance without changing the skill's trigger, layout, or authoring scope.

## Ordered tasks

- [x] Pin Kura v0.9.0 and its verified checksum.
- [x] Preserve the 17 restored historical group arrays in the registry, leaving bundle manifests unchanged.
- [x] Update registry documentation, agent-writer packaging templates, and catalog assertions for descriptive groups and project-only scope.
- [x] Validate all registry schemas and read-only bundle listing and group filters with v0.9.0.
- [x] Run the agent-writer structural validator, focused Kura-role tests, and full suite through `make test`.

## Original compatibility boundary

Kura v0.7.0 did not consume bundle registry metadata and reported empty bundle groups and `global: false`.
Kura v0.8.0 supported explicit global flags but rejected bundle registry groups, so the earlier staged tags were removed.
Kura v0.9.0 supports descriptive bundle groups, closing that compatibility boundary without adding global bundles.

## Verification

All registry names must match shipped bundle directory and manifest names.
Every registered bundle must carry a nonempty, deduplicated group array; manifests must carry neither groups nor scope policy.
No shipped bundle gains `global`.
Existing manifest metadata and requirements must remain unchanged.
Run the focused Kura-role suite and the full suite through `make test`.
A passing dotfiles suite verifies catalog structure, not Kura runtime support.

## Validation results

The release asset matches the pinned v0.9.0 checksum, and all three registries validate against its schemas.
All 17 group arrays match their historical values; bundle manifests are unchanged.
Read-only listing loads all 17 project-scoped bundles with matching group membership, and filters for all 25 tags match the registry.
The skill and standalone-agent catalogs also load successfully with v0.9.0.
The agent-writer structural validator passed with no errors or warnings.
The focused Kura-role suite passed: 33 tests.
The full suite passed: 1,418 tests, with 2 skipped.
