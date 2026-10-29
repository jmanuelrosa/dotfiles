# Single Divebell Capture

Open one page and collect only the evidence required for the diagnosis. Read
`../divebell.md` first.

## Open And Inspect

```bash
divebell setup
divebell open "https://example.com/dashboard" --mf --timeout 30000
divebell page-snapshot --interactive
divebell mf status
```

Use the smallest MF Extension command named by its installed Skill. Typical
choices are:

```bash
divebell mf remote status "<remote>"
divebell mf remote trace "<remote/expose>"
divebell mf shared status "<package>"
divebell mf shared trace "<package>"
```

Do not dump private MF globals when a structured Extension command answers the
question.

## Fallback Browser Evidence

Use built-in Divebell commands only when the MF result is incomplete or the
question concerns browser-level behavior:

```bash
divebell errors
divebell console --level error
divebell network --url "<remote-entry-or-manifest-fragment>"
divebell get-window "<specific-dotted-path>"
```

Inspect `divebell network --help` before requesting details for one network
entry. Use `get-window` or `eval` only for a specific, bounded value that
the MF Extension does not expose. Do not serialize all private runtime objects
as a substitute for Remote, Shared, Bridge, or trace commands.

Use `divebell screenshot` only when visual page state is relevant. MF runtime
success does not prove that the consuming UI rendered or became business-ready,
so verify the requested page result separately.
