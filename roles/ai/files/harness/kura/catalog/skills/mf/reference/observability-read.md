# Observability: Read Reports

Use this reference when the user has a trace id, browser reader expression,
collector output, Node/SSR output, build output, Chrome DevTools export, or an
already opened live MF page.

## Route By Source

- For a live page with no report yet, use `observability-page.md`.
- For a supplied report JSON/file or Chrome DevTools export, read the artifact
  directly and continue with `observability-analyze.md`.
- For a current live page, trace id, or reader expression, use the Divebell MF
  Extension path below.
- For local collector, Node/SSR, or build files, use the corresponding
  file-based path below. These do not require browser evaluation.

Do not write a CDP/WebSocket reader, launch debug Chrome, or switch to
Playwright, Puppeteer, Cypress, Electron, or another browser tool.

## Live Page And Trace Fast Path

Read `divebell.md` in full and follow the installed CLI and MF command Skills.
The page must have been opened before navigation with MF diagnostics:

```bash
divebell open "<target-url>" --mf
divebell mf status
```

A `traceId` from an earlier closed page cannot be reconstructed by reopening
the site. If no current authorized page or stored record still exposes that
trace, ask for the uploaded `onReport` record or an exported report instead
of claiming the trace was read.

If the required loading only occurs after interaction, reproduce it through
Divebell and keep the same page session. Then choose the smallest installed MF
command:

```bash
divebell mf remote status "<remote>"
divebell mf remote trace "<remote/expose>" --trace-id "<trace-id>"
divebell mf shared status "<package>"
divebell mf shared trace "<package>" --trace-id "<trace-id>"
divebell mf bridge trace "<remote>"
```

Only include selectors and options supported by the installed
`divebell mf --help`. If the target type is unknown, start with `mf status`
and follow one returned candidate command instead of guessing.

Read warnings, recommended actions, selection, capability, and completeness
first. A missing historical event is not proof that the operation never
happened. If evidence started late or page context is missing, reopen with
`--mf`, reproduce, and retry before concluding.

## Reader Expressions

Prefer a structured MF Extension command when it covers the supplied
`getReport`, `getLatestReport`, `getReports`, or `findReports` intent.
The Extension returns bounded, serializable evidence and avoids exposing
private runtime objects.

If the user supplied a reader expression that the installed MF command cannot
represent, execute only that authorized expression through Divebell:

```bash
divebell eval "<supplied-reader-expression>"
```

Preserve the expression exactly and quote it safely for the current shell. Do
not construct a temporary reader script, inspect arbitrary scopes, or dump the
whole `window.__FEDERATION__` object. Save the returned JSON as the raw report
and continue with `observability-analyze.md`.

If browser output is intentionally disabled and the Extension cannot expose the
requested record, ask for the application's `onReport` upload payload,
explicit export, or stored report. Do not infer a full report from a console
`traceId` alone.

## Local Collector

Use this only when the application explicitly enables
`ObservabilityPlugin({ collector: true })`, configures
`collector: { enabled: true, port }`, or the user asks for a repeatable local
collector loop.

Start the existing non-browser collector before opening or reloading the page:

```bash
node skills/mf/scripts/observability-collector.js --port 17891
divebell open "<target-url>" --mf
```

Use the configured port. If another port is required, the application config
must use the same value. After reproducing the user path through Divebell, read:

```text
.mf/observability/collector/latest-session.json
.mf/observability/collector/<sessionId>/latest-report.json
.mf/observability/collector/<sessionId>/latest.json
.mf/observability/collector/<sessionId>/events.jsonl
```

Read `latest-report.json` first. Use `latest.json` or `events.jsonl` for a
pending trace or event ordering. Stop the collector after analysis unless the
user asks to keep collecting.

Do not start this collector for a page without matching application collector
configuration, and do not treat no collector payload as proof of MF health.

## Chrome DevTools Export

If the user provides JSON exported from the Module Federation Chrome
extension's Loading Trace tab, treat that file as the report source and route
to `observability-analyze.md`. The user's manual Chrome extension workflow
does not authorize controlling that tab with another browser tool.

## Node Or SSR

Read `.mf/observability/latest.json` first. Use
`.mf/observability/events.jsonl` only when multiple traces or event ordering
are needed.

`latest.json` is the formatted latest complete report.
`events.jsonl` is an append-only event stream keyed by `traceId`.

## Build

Read `.mf/observability/build-report.json` for build failures and
`.mf/observability/build-info.json` for successful build facts.

## Analysis Boundary

After obtaining the evidence, continue with `observability-analyze.md`.
Keep current state separate from captured history, and keep MF runtime success
separate from UI render or business readiness.
