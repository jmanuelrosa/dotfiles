# Artifacts and releases

When to read: the brief or diff touches build artifacts, package publishing, releases, version tags, or provenance.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Non-idempotent publish.** A release job that fails halfway (some artifacts pushed, tag missing) cannot be rerun: the retry double-publishes or wedges on already-exists errors.
  Check: every publish step is skip-if-exists or atomic, and the whole job is rerun-safe from any failure point.
- **Mutable released versions.** Re-tagging an existing version changes what that version means for everyone who already pulled it, and breaks any integrity checking downstream.
  Check: released versions are immutable; a fix is a new version, never a moved tag.
- **Version with two sources of truth.** A version derived independently in multiple places (VCS tag, manifest file, CI computation) drifts until artifacts disagree about their own identity.
  Check: one source of truth for the version; everything else derives from it in the same run.
- **Tested and shipped artifacts differ.** A release that rebuilds from a branch head instead of promoting the tested artifact ships something the pipeline never saw.
  Check: build once, test that artifact, promote that same artifact; the release step performs no fresh build.
- **Whole-workspace artifacts.** Uploading the workspace captures env files, credentials, and junk, and hands them to anyone with read access to the run.
  Check: artifact paths are explicit allowlists with deliberate retention, never a directory glob over the workspace.
- **No provenance.** An artifact with no traceable link to the commit and run that produced it cannot be audited or trusted after an incident.
  Check: artifacts carry the commit and pipeline run that built them (metadata, labels, or an attestation where tooling exists).
- **Retention pruning what rollback needs.** Aggressive artifact cleanup deletes the previous release; the rollback path returns not-found exactly when it is needed.
  Check: retention explicitly keeps what rollback and audit require.

## Escalation triggers (`needs-decision`)

- Changing artifact names, registry paths, or tag schemes other systems consume (also an ask-first boundary in the agent).
- Introducing signing or provenance infrastructure the team must then operate.

## What good looks like

- One build, one artifact, promoted unchanged through every stage, traceable to its commit.
- Releases are built by the pipeline in an isolated job, never on a workstation.
- Any release job can be rerun after any partial failure without damage.
- Version numbers are boring: single-sourced, immutable once published.
