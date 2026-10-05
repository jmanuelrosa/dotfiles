# Local data and migrations

When to read: the brief or diff touches local persistence: databases, key-value stores, changes to persisted state shape, logout, or account switch.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Schema change without a migration.** Persisted state changed shape; the old data on a user's device fails to decode and the app crashes on launch, every launch, until they reinstall.
  Check: every change to a persisted shape migrates from every schema version still shipped, not just the latest; there is no "nobody has old data".
- **Migration blocking the launch path.** A long migration or backfill on startup gets killed by the OS watchdog, leaving state half-converted.
  Check: migrations are incremental and resumable; anything heavy runs off the critical launch path and survives being killed mid-run.
- **Newer data meets older code.** A staged rollout, an update rollback, or a reinstalled older build can run old code against state a newer version wrote.
  Check: decoders tolerate unknown fields, and version-stamped stores refuse gracefully instead of crashing.
- **Partial-write corruption.** The OS kills the process mid-write; a multi-step save to a non-transactional store leaves state that never loads again.
  Check: multi-step writes are atomic, transactional, or journaled; a kill at any point leaves a loadable state.
- **Logout leaves the previous user behind.** Sign-out clears the token but not the caches; the next account sees the previous user's data.
  Check: logout and account switch enumerate and clear every store keyed to identity, and the claim is verified by switching accounts.
- **Unbounded local growth.** Caches, logs, and media accumulate forever; storage-full then breaks every write path in the app.
  Check: every store the diff adds or grows has a size bound or eviction policy, and the storage-full failure path is handled.
- **Backup and restore surprises.** OS backup restores data onto a new device where device-bound assumptions (keys, hardware identifiers, install state) no longer hold.
  Check: each store deliberately opts in or out of backups; device-bound state and secrets are excluded.
- **Incidental serialization.** Persisting in-memory objects directly couples the stored format to code layout; the next refactor breaks every device's data.
  Check: persisted formats are explicit and schema-owned, never the accidental shape of a class.

## Escalation triggers (`needs-decision`)

- Changing a persisted-state schema beyond what the brief explicitly asked for (also an ask-first boundary in the agent).
- Any destructive cleanup of existing on-device data, however wrapped.
- Starting to persist a new category of sensitive data (also fires permissions-and-privacy and mobile-security).

## What good looks like

- Stores are versioned, and the upgrade path from every live version is tested.
- A process kill at any moment leaves data the next launch can load.
- Logout provably resets the device to a stranger's state.
