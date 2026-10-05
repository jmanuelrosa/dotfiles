# Local data and migrations

When to read: the brief or diff touches where the app stores data, a persisted format or schema, a local database or preference store, cache handling, or anything read at launch.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Paths assembled instead of requested.** Writing next to the binary, at the root of the home directory, or into a path built from string concatenation breaks on a read-only or shared install, escapes the OS backup story, and survives uninstall.
  Check: data, cache, and log locations come from the platform's own directory APIs, and the diff constructs no absolute path by hand.
- **The data directory derived from a display name.** Frameworks commonly build the user-data path from the product name or application id, so renaming the product is a one-line diff that moves every existing user's settings, history and credentials somewhere the app no longer looks, with no error and no migration.
  Check: a change to the product name, application id, or packaging format is treated as a data migration, with an explicit read of the old location; nothing about where data lives is a side effect of renaming something.
- **Cache and data confused.** Regenerable content stored as data bloats backups and sync forever; irreplaceable content stored as cache is deleted by the OS under disk pressure without warning or error.
  Check: the diff classifies what it writes as data, cache, or transient state, and puts each where that platform expects it.
- **Schema changed without a path from every shipped version.** Users skip releases and update on their own schedule, so a decode failure at launch is a crash loop whose only user-discoverable fix is a reinstall that destroys their data.
  Check: migration runs forward from the oldest version still supported, and a migration that fails leaves the original intact and readable rather than half-rewritten.
- **Format change that only migrates forward.** Halting a bad rollout leaves users on the previous binary, which now opens data the new one rewrote, so a one-way migration turns a rollback into a second outage.
  Check: the change is additive behind a version marker the older binary ignores, so a rolled-back build still reads the store; where that is impossible, the destructive step is split across two releases and the diff says so.
- **Writes that are not atomic.** Writing in place means a crash, a forced quit, a full disk, or an update restart leaves a truncated file where the entire application state used to be.
  Check: writes go to a temporary file and are atomically replaced, every write path handles a disk-full or permission error rather than reporting success for data that was never stored, and where the home directory can be a network mount, the rename you rely on is confirmed atomic there.
- **No recovery from corrupt state.** One unparseable file makes the app unlaunchable, with no message, no logging, and no route back for a user who cannot open a terminal.
  Check: load paths handle unparseable, empty, and partially written state by quarantining the file, falling back to a default, and telling the user, never by crashing.
- **Concurrent writers unmanaged.** Two windows, a second instance, or a background agent writing the same store interleave their writes and silently lose whichever landed first, and a migration is the worst thing for two processes to run at once.
  Check: the store is single-writer by construction or guarded by the platform's locking, the single-instance lock is acquired before the data layer opens rather than after (or both instances have already opened it), and migration is gated against concurrent runners.
- **Migration that can run twice.** A migration keyed on anything other than a persisted schema version, or that is not safe to re-enter after a mid-way crash, corrupts on the second attempt.
  Check: migration is version-keyed, idempotent, and leaves a consistent state if the process dies part-way through.
- **Secure storage assumed available.** Tokens in a preference file are readable by every process running as that user, but the fix degrades quietly too: OS-backed storage maps to a real keychain on some platforms and, where no secret service is present, can fall back to a keyless obfuscation with a fixed salt and password that is encoding rather than encryption.
  Check: credentials go to the platform credential store, the availability check runs first, and the unavailable case fails closed instead of falling back to app-data; nothing in app-data is sensitive.

## Escalation triggers (`needs-decision`)

- Changing a persisted schema beyond what the brief asked for, or changing where user data lives (also an ask-first boundary in the agent).
- Introducing a second store, sync mechanism, or serialization format alongside one the project already uses.

## What good looks like

- Every write is atomic, and every read assumes the file on disk may be garbage.
- Migration is a versioned, idempotent forward chain from the oldest supported release, not a step from the previous one.
- Where data lives is asked of the operating system rather than assembled from a string.
