# Restore the guardrails under pi's cursor provider

## Context

`/skill:commit` and `/skill:pr` fail in pi with what looks like a `git-skill-gate.sh` refusal.
Pi's own explanation (the Cursor bridge does not set `attributionSkill`) is wrong, and the real fault is larger than the two skills.

What the evidence on this machine actually shows:

- `~/.pi/agent/settings.json` sets `defaultProvider: cursor` / `defaultModel: composer-2-5`.
  Under the Cursor SDK provider, Cursor's **native** host tools handle shell, files, grep and edits.
  `PI_CURSOR_EXPOSE_BUILTIN_TOOLS` defaults to `false`, so pi's own `bash`, `write` and `edit` are hidden from Cursor and never emit a pi `tool_call` event
  (`pi-cursor-sdk/docs/cursor-tool-surfaces.md`, `src/cursor-pi-tool-bridge-env.ts`).
- `guardrails.ts` listens only to `tool_call` for `bash` / `write` / `edit`.
  So under the cursor provider **all five bridged gates are inert**: `git-skill-gate.sh`, `em-dash-gate.sh`, `cloud-readonly-gate.sh`, `pre-commit-verify.sh` and the rtk rewrite.
  Proof: `blockResult` appends `In pi those skills are /skill:commit and /skill:pr` to every `is blocked outside` message, and that string appears zero times across every session in `~/.pi/agent/sessions/`.
- What actually failed: the `apply.py` and `git add && git commit` calls came back as `Tool error (Cursor activity, call cursor-replay-...): Cursor shell did not complete / missing completion`, with no output at all,
  while read-only calls (`git status`, `git diff --stat`) completed with full output.
  `missing completion` is `DISCARDED_INCOMPLETE_TOOL_CALL_REASON`: the Cursor SDK started the call and never delivered a completion.
  The model filled that silence by inventing the `attributionSkill` story, then repeated it after reading the hook source.
- The stamp mechanism is fine. Running the real `activeSkills` from `guardrails.ts` in node against the persisted branch of the failing session returns `["commit"]`, so the hook would have allowed the commit had it ever run.

Intended outcome: under the cursor provider, git, file and shell work routes through pi's own tools, so every gate fires as designed and pi-sandbox applies; and when it does not, the session says so out loud instead of failing silently.

Why the Cursor shell never completes for mutating commands, given read-only ones do, points at Cursor's own approval path having no surface in pi.
That last hop is inference; everything above it is read from the session and debug files.

## Approach

Three coordinated changes. The exposure is the lever, the steering makes the model use it, the footer makes a session where neither worked visible.

### 1. Expose pi's builtins to Cursor

Add to `roles/shell/files/fish/config.fish`, beside the other `set -gx` exports:

```fish
set -gx PI_CURSOR_EXPOSE_BUILTIN_TOOLS 1
```

Cursor then sees `pi__bash`, `pi__read`, `pi__write`, `pi__edit`, `pi__grep`, `pi__find`, `pi__ls` on the loopback MCP bridge.
A bridged call is real pi execution: the bridge queues the request, emits a real pi `toolCall`, and waits for the matching `toolResult`, which is exactly the event `guardrails.ts` hooks.

`roles/ai/files/pi/settings.json` has no `env` block, which is why this cannot live with the rest of the pi payload and why `guardrails.ts` already passes `RTK_HOOK_AUDIT` on its own spawn.
`config.fish` is the established home for a global export, and the variable is inert outside pi.

**Known limit, state it rather than paper over it.**
Exposure only *offers* `pi__bash`; it cannot retire Cursor's native shell.
`--no-tools`, `--tools` and `--exclude-tools` act at pi's registry boundary and explicitly do not disable Cursor SDK host tools.
So the gate is best-effort under this provider, not enforced. Step 3 exists because of that.

### 2. Steer the model onto the bridged tools

Add a section to `roles/ai/files/pi/APPEND_SYSTEM.md`, after `## Actions`:

- Any `git`, `gh` or `glab` command, and any write or edit, goes through the `pi__*` bridged tools rather than the Cursor-native shell or editor.
- State the reason in one line, because a rule with no reason is the first thing a model drops under pressure: the guardrails only see the bridged path.
- Do not enumerate the hooks here. Naming them invites the model to reason about whether a given command is gated; the rule is unconditional.

### 3. Say so when the gates are not enforced

In `roles/ai/files/pi/extensions/guardrails.ts`, add a second footer segment beside `rtkStatus`.

- New key, namespaced the way `RTK_STATUS_KEY` already is (last writer wins on a string key, and herdr ships an extension into the same directory).
- A `gateStatus(ctx)` helper reading `ctx.model` for the provider and `process.env.PI_CURSOR_EXPOSE_BUILTIN_TOOLS`.
  Nothing at all on a pi-native provider, where the gates are enforced and a segment would only add noise; a dim warning when the provider is cursor and the exposure is off.
- Register on `model_select` as well as `session_start`. `session_start` alone goes stale the moment `/model` switches provider mid-session, and a stale "gates on" reading is worse than no reading.
- Same failure posture as the rest of the file: wrapped in try/catch, never throws, a footer segment is never worth interrupting a session for.

### 4. Record it

- `docs/internals/pi-harness.md`: a subsection under the hooks material stating that the bridged gates only see pi's own tools, that the cursor provider bypasses them unless builtins are exposed, and that exposure is best-effort because Cursor's host tools cannot be turned off from pi.
- `CLAUDE.md` line 47 mentions `RTK_ENABLE` as the ai role's opt-in; add `PI_CURSOR_EXPOSE_BUILTIN_TOOLS` alongside it in one clause.

### 5. Tests

`lib/python/tests/test_pi_guardrails.py` already drives the extension's private functions in node via the `DRIVEN` tuple and `run_in_node`.

- Add `gateStatus` to `DRIVEN` and cover the three cases: cursor provider with the exposure off, cursor provider with it on, non-cursor provider.
- Assert `set -gx PI_CURSOR_EXPOSE_BUILTIN_TOOLS 1` is present in `roles/shell/files/fish/config.fish`, in the same spirit as the existing assertion that `npm:pi-sandbox` is in `packages`.
- Assert the `pi__*` routing rule is present in `APPEND_SYSTEM.md`, so a future rewrite of that file cannot silently drop the one instruction the exposure depends on.

## Verification

1. `make test` for the pytest suites, unattended.
2. Open a new fish shell, `env | grep PI_CURSOR_EXPOSE_BUILTIN_TOOLS` returns `1`.
3. `pi` in a scratch git repo, then `/cursor-tools`. Confirm the callable-surface snapshot lists `pi__bash`.
4. **The regression this exists for.** Ask for a bare `git commit -m "x"` *outside* any skill.
   Expect a refusal ending in `In pi those skills are /skill:commit and /skill:pr`.
   That exact tail is the only proof the gate ran rather than the command merely failing.
5. Run `/skill:commit` end to end on a real change and confirm the commit lands.
   The `missing completion` error must not appear; a bridged call completes through pi.
6. Footer: with the exposure unset (`env -u PI_CURSOR_EXPOSE_BUILTIN_TOOLS pi`), the warning segment is visible. With it set, it is gone. On a non-cursor model (`pi --model xai/grok-4.6`), it is gone.
7. `make check-role ROLE=shell` for the config.fish change.
