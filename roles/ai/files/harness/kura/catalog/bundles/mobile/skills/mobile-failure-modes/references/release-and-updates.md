# Release and updates

When to read: the brief or diff touches store releases, build variants and flavors, signing, OTA updates, version gates, or crash reporting wiring.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **OTA update carrying native changes.** An over-the-air update ships script and asset changes only; if the diff touched native modules, native config, or the runtime, users on the old binary crash on launch.
  Check: any native-side change in the diff means the fix ships as a store build; the update channel's runtime or compatibility version must exclude older binaries.
- **Release-only breakage.** Minification, dead-code stripping, and engine differences make release a different program; reflection, dynamic lookup, and interop code that works in debug crashes only in release.
  Check: anything touching dynamic lookup, native interop, or build config gets a release-mode build and run before `done`, and a reflection-dependent library lands together with its shrinker keep rules.
- **New API above the floor.** A platform API newer than the app's minimum supported OS version crashes or misbehaves on every older device that CI and the simulator never saw.
  Check: new platform APIs are guarded with the platform's availability mechanism, or the minimum version is raised deliberately as an escalation, never as a side effect.
- **No path back.** Stores have no rollback; a bad release is fixed only by a forward release through review, measured in days.
  Check: risky behavior ships behind a remote flag or staged rollout so the mitigation is a config change, not a resubmission.
- **Version gate absent.** Old app versions keep running for years; a server or contract change an old client cannot parse strands users with no upgrade path.
  Check: the client tolerates unknown fields and responses, and a minimum-supported-version mechanism exists before any breaking dependency ships.
- **Crash reporting gaps.** New native code without symbol upload produces unreadable crashes; errors in new paths that never reach the tracker are invisible in production.
  Check: symbolication artifacts (dSYMs, mapping files) upload in the release path for every binary the diff produces, and new failure paths report to the existing tracker.
- **Build variant divergence.** Config that exists per flavor, scheme, or environment updated in one variant only; staging works, production does not.
  Check: every variant that carries the touched config is updated consistently, including the one the store build uses.
- **Identifier and entitlement drift.** Changing bundle identifiers, entitlements, or capabilities breaks signing and provisioning, and can orphan existing installs.
  Check: any identifier, entitlement, or capability diff is deliberate and escalated, never a side effect of tooling.
- **Review-hostage surprise.** Changes touching payments, permissions, tracking, or login methods can fail store review and block every other change on the release train.
  Check: name the policy surface the diff touches and flag review risk in the report before it reaches a release branch.
- **Store technical floor missed.** Stores also enforce binary-level requirements (target SDK floors, native-library alignment such as Android's 16 KB page size) that reject an upload outright, days after the code merged.
  Check: new or updated native libraries and build targets meet the current store technical requirements, verified when the dependency lands, not at submission.

## Escalation triggers (`needs-decision`)

- Raising the minimum OS version, target SDK, or update runtime version, or changing app identifiers, entitlements, capabilities, or store configuration (also an ask-first boundary in the agent).
- Any change that requires a forced upgrade or breaks clients older than the current release.

## What good looks like

- Native diffs ship as binaries with explicit update-compatibility versioning; script-only diffs state why they are OTA-safe.
- Risky logic sits behind remote flags; the first mitigation for a bad release is configuration, not review.
- Every shipped binary is symbolicated, and every new failure path is visible in the crash tracker.
