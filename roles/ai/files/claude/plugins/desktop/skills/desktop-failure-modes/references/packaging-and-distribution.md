# Packaging and distribution

When to read: the brief or diff touches installer or bundle configuration, the auto-update path, release channels, version numbers, signing key handling, or first-run and uninstall behavior.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Update payload not signature-verified.** An updater that trusts the transport alone turns any feed compromise, cache poisoning, or intercepted connection into code execution on every installed machine, at user or elevated privilege.
  Check: the payload's signature is verified against a public key shipped inside the app, never one fetched alongside the update, before the file is extracted, executed, or handed to the installer. The signed message covers the version as well as the hash, so a validly signed older artifact cannot be replayed as an upgrade, and verification and installation address the same file in a directory only the installer can write.
- **Signature that stops validating when the certificate does.** An untimestamped signature is only valid while the certificate is, so a build signs cleanly today and warns on every machine after expiry; certificates now rotate on a schedule far shorter than an app's life.
  Check: the signing step countersigns with a timestamp, and a certificate or signing-identity change is treated as a reputation reset rather than a routine rotation, because reputation accrues to a consistent identity and starts over with a new one.
- **No way to stop a bad release.** An automatic update reaches everyone within hours, and unlike a store release it cannot be recalled: there is no review before it ships and no third party able to withdraw it.
  Check: the release path can halt a rollout and can serve the prior version, and a staged rollout keys its percentage off an identifier persisted per install rather than one regenerated each launch, which otherwise re-rolls the dice until every client is eventually included.
- **Update applied over the user.** Swapping files under a running process, or restarting to install while work is unsaved, corrupts the session or loses the edit.
  Check: installation happens at a quiescent moment or with explicit consent, and unsaved work survives the restart the update performs.
- **Versions ordered as strings.** Lexical comparison makes 1.10.0 older than 1.9.0, so the updater offers a downgrade as an upgrade, or stops offering anything at all.
  Check: version ordering uses a real semantic comparison, and downgrade is either refused or a deliberate, tested operation.
- **Migration chain assumes the previous release.** Users skip versions and update on their own schedule, so a chain that only handles N-1 to N breaks for anyone who was away.
  Check: migrations run from the oldest version still supported, and that path is exercised, not assumed.
- **Signing keys handled as configuration.** A key value, certificate, or notarization credential in a repo, a build script, or an inline CI variable has left custody, and an update-signing key is not a rotatable secret: losing it means the installed fleet can never be updated again, and leaking it means someone else can update it.
  Check: keys are references into the platform's secret store or an HSM, production and pre-release use separate keys or separate feeds, the diff neither contains a key value nor causes one to be printed, and any new secret is named for a human to create.
- **Architecture or OS floor changed in passing.** Dropping an architecture or raising the minimum OS silently strands users, who do not see an error and simply stop receiving updates.
  Check: shipped architectures and the minimum OS version are unchanged, or the change is escalated with the affected population named.
- **Fresh install, upgrade and uninstall treated as one path.** Migration code that assumes prior state breaks a fresh install; an uninstaller that leaves data behind reappears as corrupt state on the next install.
  Check: all three paths are distinct in the diff and each has been exercised.
- **Release built from a machine, not from the repo.** Artifacts produced with untracked local configuration or a floating toolchain cannot be reproduced, audited, or handed to anyone else.
  Check: the packaged build comes from the project's own scripted path with pinned toolchain and dependency versions.

## Escalation triggers (`needs-decision`)

- Changing the update feed, release channel, rollout strategy, or signing key configuration (also an ask-first boundary in the agent).
- Raising the minimum OS version or dropping a shipped architecture (also an ask-first boundary in the agent).

## What good looks like

- Every artifact a user receives is signed, verified before it runs, and recoverable by a roll-forward release rather than by a downgrade.
- Migrations are written against the oldest supported version rather than the last one shipped.
- The release path is a script in the repository, not knowledge in one person's shell history.
