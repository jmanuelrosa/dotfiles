# Failure visibility

When to read: any new window, flow, helper process, or background task; and whenever the brief or diff touches crash reporting, logging, symbol upload, or the telemetry and consent path.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **The silent crash path.** A path that throws in a packaged build without reaching the crash tracker is invisible, because desktop users do not file reports: they quit and stop launching.
  Check: every new failure path reports to the app's existing crash tracker with enough context to act on, wired through the setup already present rather than a parallel one.
- **Only the main process reported.** A crash in a renderer, helper, or background process that was never wired to the tracker surfaces as a hang or a blank window with no report anywhere.
  Check: every process the change touches or creates reports its own crashes, and the report names which process died.
- **Native crashes uncollected.** A language-level error reporter records nothing when the process dies inside native code, which is where the crashes that matter most happen. Collecting those needs a separate crash handler, started in the owning process before any window exists, writing minidumps to an endpoint that can read them.
  Check: the native crash handler is initialized early enough to catch a crash during startup, and the diff does not assume the JavaScript or Swift error path covers a hard process death.
- **Context-free reports.** A crash with no build, no OS, and no preceding action is a ticket nobody can act on.
  Check: reports answer what happened, why, when, and to whom: app version and build, OS version, update channel, the window or action, a correlation or trace id where a backend request exists, and the install variant, since a store-packaged, sandboxed, or emulated-architecture install fails in ways a directly-distributed native one cannot.
- **Swallowed errors.** A catch that shows a message and moves on, where the caller needed to know, hides a real defect behind a working-looking app.
  Check: every catch either handles meaningfully or reports; a user-visible failure is also a tracked one.
- **Symbols that do not match the shipped artifact.** Users run the stripped, optimized build, and its stack traces are unreadable without symbols from that exact build. Lookup keys on a build identifier the compiler mints, so the failures that matter are a rebuild between generating symbols and shipping (a new identifier, and the uploaded symbols now describe a binary nobody runs) and stripping after the symbols were produced.
  Check: symbol files upload for every binary the change produces, they come from the same build as the shipped artifact rather than a rebuild of it, and a deliberate test crash resolves to real function names.
- **Logs nobody can retrieve.** Desktop support has no device console, so the app is the only thing that can collect its own diagnostics; a log with no defined location, no rotation, and no size bound either fills a disk over a months-long install or vanishes because it was written somewhere the OS clears.
  Check: logs go to the platform's log location, are rotated and bounded, and the app can produce a diagnostic bundle (logs plus versions and install variant) the user can actually send.
- **Personal data in reports, including paths.** Tokens and emails are the obvious leak; on desktop a filesystem path usually contains the user's real name, and paths are in every stack trace and breadcrumb.
  Check: scrubbing covers every new breadcrumb and context field, home directory paths included; no whole objects are dumped.
- **Telemetry ahead of consent.** The ordering is the trap rather than the checkbox: a crash handler must start before anything can crash, and consent is usually known late, so the reporter is routinely initialized and collecting before the gate it is supposed to be behind.
  Check: the reporter's initialization is separated from its permission to send, nothing leaves the machine before consent is established, and crash reports fall under a consent decision too, since a minidump carries memory and paths.
- **Events lost offline.** A machine with no connection drops exactly the crashes that explain the bug.
  Check: the tracker's offline queue is intact, and a crash captured with no connection is sent on the next launch that has one.

## Escalation triggers (`needs-decision`)

- Adding a crash or analytics SDK, or changing sampling, consent, or release-tracking configuration.
- Instrumentation the brief needs for which the app has no existing pattern.

## What good looks like

- Every question the next triage asks (which build, which OS, which process, which user action) is answerable from the report alone.
- Symbols exist for the exact signed artifact the user is running, and someone has confirmed it with a test crash.
- Report volume stays boring: breadcrumbs bounded, personal data and home paths scrubbed, consent honored.
