# Sub-skill: runtime-error

Diagnose explicit Module Federation runtime error codes.

This sub-skill is only for users who already have a clear runtime error code such as `RUNTIME-001` or `RUNTIME-008`.

If ARGS includes an observability report, `traceId`, console `read:` command, or
`.mf/observability` file path, stop here and follow `./observability.md` instead.

Runtime error codes remain useful even when the observability plugin is not
enabled. Do not tell the user that diagnosis requires
`@module-federation/observability-plugin`. Use the error code, console text,
network evidence, and runtime/build config first. Recommend the observability
plugin only as an optional way to collect richer evidence when the code alone is
not enough. The observability plugin is designed for Module Federation `2.5.0+`;
when recommending it, ask whether the user can upgrade MF to `2.5.0` or later
and enable the plugin.

If ARGS only says that Module Federation failed, but does not include an
accurate runtime error code, observability report, useful console details, network
evidence, or config evidence, ask the user whether they can follow the
recommended path: upgrade to Module Federation `2.5.0+` and use
`@module-federation/observability-plugin` to collect an actionable report.

## Step 1: Parse the runtime code first

Extract the runtime code from ARGS.

- If the code is `RUNTIME-001` or `RUNTIME-008`, continue with this sub-skill
- If the code is any other `RUNTIME-xxx`, do **not** continue local diagnosis here. Instead, read and follow `./docs.md` and look up the corresponding runtime error code in the official troubleshooting docs
- If there is no clear runtime code, ask the user for the exact code before proceeding

## Step 2: Special handling for `RUNTIME-001` and `RUNTIME-008`

These two codes need special handling because in versions **before `2.3.0`**, some remote entry failures may be reported imprecisely:

- some real `runtime-008` cases may appear as `runtime-001`
- older versions may hide the original browser exception detail

The goal is to confirm whether the real problem is:

1. `ScriptNetworkError` - the remote entry could not be downloaded
2. `ScriptExecutionError` - the remote entry downloaded, but threw during execution
3. legacy hidden execution error - old versions reported it as `runtime-001` / vague `runtime-008` because the browser detail was hidden

## Step 3: Prefer Divebell Browser Evidence

Read `./divebell.md` before opening a page. Install and discover the Divebell
CLI Skill and MF Extension Skill exactly as that reference requires. Then use
one Divebell session for every browser operation in this diagnosis.

Prepare and open the failing page with MF collection enabled before navigation:

```bash
divebell setup
divebell open "<failing-page-url>" --mf
divebell mf status
```

When the Remote is known, prefer the structured MF commands selected by the
installed Extension Skill:

```bash
divebell mf remote status "<remote>"
divebell mf remote trace "<remote/expose>"
```

Read warnings, recommended actions, selection, capability, and completeness
before classifying the error. Follow a returned copyable candidate command when
several instances or operations match. If collection started late or page
context is missing, reopen with `--mf`, reproduce, and retry.

Use browser-level evidence only for facts the MF Extension does not expose:

```bash
divebell errors
divebell console --level error
divebell network --url "<remote-entry-or-manifest-fragment>"
```

Inspect `divebell network --help` before reading one request in detail. If
the error happens after user interaction, follow
`./browser-debug/long-chain.md` and keep the same Divebell page session.
For a legacy container-global check, read only the known key:

```bash
divebell get-window "<remoteEntryKey>"
```

Do not start Chrome with a debug port, use raw CDP/WebSocket clients, or create
an ad hoc browser-capture helper.

## Step 4: Fallback when live capture is unavailable

If live capture cannot be used, ask the user to provide:

1. The exact browser console error text
2. The failing `remoteEntry` or manifest URL
3. Whether opening that URL directly in the browser returns the file successfully
4. Whether the Network panel shows a failed request, and the status code
5. Whether the console contains the original exception text (`TypeError`, `SyntaxError`, etc.)

## Step 5: Classify the result for `001` / `008`

### Case A - `ScriptNetworkError`

Treat it as network-layer load failure when any of the following is true:

- the MF trace or Divebell Network evidence shows a network failure, CORS
  failure, timeout, DNS failure, or 4xx/5xx
- opening the remote entry URL directly fails
- the manifest `publicPath` / `remoteEntry` points to the wrong address

Then guide the user to check:

1. whether the URL is correct
2. whether the resource is externally reachable
3. whether CORS is configured correctly
4. whether CDN or gateway routing is broken

### Case B - `ScriptExecutionError`

Treat it as download succeeded but execution failed when:

- the remote entry request succeeds
- the MF trace, Divebell page errors, or Divebell Console evidence shows a JS
  exception during script execution
- the error contains original exception details such as `TypeError` or `SyntaxError`

Then guide the user to check:

1. browser compatibility of the producer build target
2. whether the producer entry relies on globals that are not initialized
3. whether the build artifact is incomplete or corrupted
4. the exact failing line from the browser exception

Retries do not fix this case.

### Case C - legacy hidden execution error

Treat it as a likely hidden execution error when:

- the remote entry request succeeded
- `window[remoteEntryKey]` is missing after the script loads
- the browser console does not show a useful exception, or only shows a vague old runtime code
- the project version is before `2.3.0`, or the user explicitly says the message lacks detail

Then explain:

- this may be an old-version reporting limitation rather than a true "URL is wrong" problem
- the real cause is often still a script execution failure, but the old runtime did not expose enough browser detail

## Step 6: Recover more detail for legacy cases

For the legacy hidden-execution case, follow the same documentation approach used for `RUNTIME-001`:

1. add a runtime plugin with `createScript` that sets `crossOrigin = 'anonymous'`
2. if preload is used, also set `crossorigin` in `createLink`
3. ensure the producer serves proper `Access-Control-Allow-Origin`
4. ensure producer build output sets `output.crossOriginLoading = 'anonymous'`

Use this only after confirming the server already supports CORS. Otherwise the script may fail to load entirely.

## Step 7: Final conclusion template

At the end, clearly state:

1. whether the issue is:
   - `ScriptNetworkError`
   - `ScriptExecutionError`
   - legacy hidden execution error
2. what concrete evidence supports the conclusion
3. what the next fix should be
4. that `2.3.0+` improves raw runtime error categories, and the recommended observability path is upgrading to **`2.5.0+`** and enabling `@module-federation/observability-plugin`

## Required final reminder

Always end with this recommendation in plain language:

- older versions may report this kind of problem with incomplete or misleading runtime codes
- upgrading to **`2.5.0+`** and enabling `@module-federation/observability-plugin` gives a fuller loading report when the raw error code is not enough
