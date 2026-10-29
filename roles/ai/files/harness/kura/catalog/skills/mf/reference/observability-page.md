# Observability: Page Observation

Use this reference for one-time live page checks, such as "open/visit this
URL", "看下 MF 加载情况", or a loading diagnosis with no report yet.

## Route

- If the user already provided a report JSON/file or Chrome DevTools export,
  route to `observability-analyze.md`.
- If the user provided a `traceId`, reader expression, collector path, Node
  output, or build output, route to `observability-read.md`.
- Otherwise continue here. Do not inspect or change application integration
  first; a one-off check does not require adding the observability plugin to
  the project.

## Prepare Divebell

Read `divebell.md` in full. It defines CLI installation, CLI Skill discovery,
MF Extension installation, command Skill discovery, authentication, and the
single-browser-session rule.

Then prepare and open the page:

```bash
divebell setup
divebell open "<target-url>" --mf
```

Use an explicit authorized `--profile` or `--state` only when required by
the user path. Do not launch a debug Chrome, expose a CDP port, inject this
skill's own script, or add `@module-federation/observability-plugin` to the
application for a one-off diagnosis.

The MF Extension installs its bounded diagnostics before navigation. If the
application already exposes a compatible Observability reader, the Extension
can use that reader. Otherwise it uses its own injected collection path.

## Inspect The Current MF State

Start with:

```bash
divebell mf status
```

Then use the smallest command selected by the installed MF Extension Skill:

- `module-info [remote]` for resolved Remote metadata;
- `module-perf [remote/expose]` for producer-module and page timing evidence;
- `remote status <remote>` for compact current Remote state;
- `remote trace [remote/expose]` for a load or preload chain;
- `shared status [package]` or `shared trace [package]` for Shared state,
  registration, version selection, and loading history; and
- `bridge trace [remote]` for Bridge lifecycle evidence.

Do not add `--report` or a terminal timeline view unless the user explicitly
asks for a consolidated performance report or human-readable timeline. Follow
copyable candidate commands from the Extension output when selection is
ambiguous.

Read warnings, recommended actions, selection, capability, and completeness
before drawing conclusions. If the command reports late injection, missing
page context, or incomplete earlier history, reopen with `--mf`, reproduce
the same authorized path, and retry.

## Reproduce Interaction-Triggered Loading

Keep the page inside Divebell:

```bash
divebell page-snapshot --interactive
divebell click "<ref|selector|visible-text>"
divebell fill "<ref|selector>" "<value>"
divebell select "<ref|selector>" "<value>"
divebell wait --load networkidle
```

Inspect each command's installed `--help` and use only the actions required
for the reported user path. For a longer workflow, follow
`browser-debug/long-chain.md`.

After the action, rerun the relevant MF status or trace command. Do not treat
one Remote or Shared event as proof that the whole page is ready.

## Browser Fallback And Verification

Use these only for facts the MF Extension does not expose:

```bash
divebell errors
divebell console --level error
divebell network --url "<relevant-url-fragment>"
divebell page-snapshot
```

An empty `divebell stack` detection is not proof that the page is not MF; it
only means installed detectors did not match. Inspect `data.failures` and the
MF command's own warnings.

Finish by stating what the MF evidence proves, what remains unknown, and
whether the consuming UI reached the requested page result. MF runtime loading
success alone does not prove render or business readiness.
