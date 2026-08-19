# More explicit pi failure detail

## Context

Pi's default provider is Cursor (`defaultProvider: cursor` in `roles/ai/files/pi/settings.json`, via the `npm:pi-cursor-sdk` package).
When a Cursor-backed tool call fails, pi-cursor-sdk shows a generic activity card: `"<Tool> did not complete"` plus one of four canned reason strings (`missing completion`, `aborted`, `SDK run failed`, `run ended during drain`).
That's the whole message the user sees, e.g. "Cursor shell did not complete", no underlying exception, no stack trace, nothing actionable.

Traced this into the installed package at `~/.pi/agent/npm/node_modules/pi-cursor-sdk/src/`:

- `cursor-incomplete-tool-visibility.ts` builds that exact headline from `activityTitle` plus a fixed reason enum. It never carries the real error.
- `cursor-sdk-event-debug.ts` is a maintainer debug channel, off by default, gated on `PI_CURSOR_SDK_EVENT_DEBUG`. Its `recordError()` writes `{label, message, stack, value}` to a per-turn `errors.jsonl` when enabled.
- Confirmed the two are connected for the case that matters: at the exact call sites that set the "SDK run failed" reason (`cursor-provider-run-finalizer.ts`, `cursor-provider-turn-finalize.ts`, `cursor-provider-turn-send.ts`), there's a companion `sdkEventDebug?.recordError(...)` call right next to it. So turning debug capture on does put the real message and stack for this exact failure mode on disk, it's just off by default, and the artifact directory defaults to `.debug/cursor-sdk-events` under the current working directory, which would litter every project pi runs in.

This package lives under `~/.pi/agent/npm/node_modules/`, installed by pi itself from its own `packages` list, so it isn't vendored in this repo and can't be patched here. The fix has to work through the env vars it already reads, wired up from this repo the same way `CTX7_TELEMETRY_DISABLED` is (`roles/ai/README.md`): the tool is an `ai`-role concern, but the export lives in the `shell` role's fish files, per existing precedent.

The user chose an opt-in wrapper (not always-on, to avoid unbounded debug-file growth in `~/.pi/agent/`) plus a convenience command to read the latest captured error back.

## Approach

Two new fish functions, `roles/shell/files/fish/functions/pi_debug.fish` and `roles/shell/files/fish/functions/pi_last_error.fish`. No task changes needed: `roles/shell/tasks/main.yml`'s "Symlink fish functions" step already globs `files/fish/functions/*.fish`, so any new file is picked up and linked idempotently on the next run.

### `pi_debug`

A thin wrapper that launches `pi` with Cursor SDK failure capture turned on for that invocation only, directed at a fixed location outside any project tree:

```fish
function pi_debug --description "Launch pi with Cursor SDK failure detail capture enabled: message and stack instead of a generic '... did not complete'"
    env PI_CURSOR_SDK_EVENT_DEBUG=1 PI_CURSOR_SDK_EVENT_DEBUG_DIR="$HOME/.pi/agent/cursor-sdk-debug" pi $argv
end
```

`PI_CURSOR_SDK_EVENT_DEBUG_DIR` must be set explicitly: left unset, pi-cursor-sdk defaults to `.debug/cursor-sdk-events` relative to cwd, which would show up as untracked files in whatever project pi is running in. Pointing it at `~/.pi/agent/cursor-sdk-debug` keeps it beside every other piece of pi's own state.

### `pi_last_error`

Finds the most recently written `errors.jsonl` under that debug directory (layout is `<base>/sessions/<session-key>/turn-NNN-<timestamp>/errors.jsonl`, one directory per turn, per pi-cursor-sdk's own `cursor-sdk-event-debug-session.ts`) and prints the last recorded error's label, message and stack through `_ui`, the shared fish output vocabulary (`roles/shell/files/fish/functions/_ui.fish`). Uses `jq`, already relied on elsewhere in this repo's fish tooling (`_tv_jira.fish`) without being declared as a package dependency, since it ships with the system.

```fish
function pi_last_error --description "Print the most recent pi-cursor-sdk failure captured by pi_debug"
    set -l debug_dir "$HOME/.pi/agent/cursor-sdk-debug"
    set -l latest (find "$debug_dir/sessions" -name errors.jsonl -type f 2>/dev/null | xargs -I{} stat -f '%m %N' {} 2>/dev/null | sort -rn | head -n 1 | cut -d' ' -f2-)

    if test -z "$latest"
        _ui warn "No captured pi-cursor-sdk errors under "(_ui path "$debug_dir")
        _ui note "Launch pi via pi_debug to capture failure detail next time"
        return 1
    end

    _ui title "🔎 Last pi-cursor-sdk error"
    _ui item (_ui path "$latest")
    _ui blank
    tail -n 1 "$latest" | jq -r '"\(.error.label): \(.error.message)\n\(.error.stack // "no stack")"'
end
```

Each JSONL line is `{ts, elapsedMs, turn, error: {label, message, stack, value}}`; the filter reads `.error.message` and `.error.stack` accordingly.

### Docs

- `roles/ai/README.md`: add a bullet next to the existing Cursor-models bullet (line 10) explaining the failure-visibility gap and pointing at `pi_debug` and `pi_last_error`, cross-referencing the shell role the way the `CTX7_TELEMETRY_DISABLED` bullet already does.
- `docs/internals/pi-harness.md`: add a short paragraph under the Cursor-model material recording why this lives in `shell`'s fish functions rather than pi's own config (the package isn't vendored here, so the env vars are the only lever), and naming the four canned reason strings so a future reader recognizes them instead of re-deriving this from `node_modules`.

## Verification

- `fish -n roles/shell/files/fish/functions/pi_debug.fish` and same for `pi_last_error.fish`, syntax check, no vault or become password needed.
- `make check-role ROLE=shell`, confirms the two new files symlink cleanly with no diff on a second run (idempotency).
- Manually seed a fake turn directory (`mkdir -p ~/.pi/agent/cursor-sdk-debug/sessions/test/turn-001-x && echo '{"ts":"now","elapsedMs":1,"turn":1,"error":{"label":"run_wait","message":"boom","stack":"at x"}}' > .../errors.jsonl`) and run `pi_last_error` to confirm formatting and the `_ui` glyphs render, then remove the fake directory.
- Real end-to-end check: run `pi_debug`, deliberately hit a Cursor-backed tool failure, and confirm `pi_last_error` afterward surfaces a real message and stack rather than "missing completion" alone.
