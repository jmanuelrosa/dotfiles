# Bridge the rtk rewrite into Pi

## Context

`rtk` reaches Claude Code only.
Claude has two touchpoints, `RTK_HOOK_AUDIT` at `roles/ai/files/claude/settings.json:11` and the `PreToolUse` one-liner at `:257`, plus a statusline segment at `roles/ai/files/claude/statusline.sh:279-290`.
Nothing under `roles/ai/files/pi/` mentions rtk, and it is absent from `docs/internals/pi-harness.md`.

Both Pi migration plans listed "rtk hook" under *Not portable, stays Claude-only* (`docs/plans/2026-08-13-pi-as-main-agent.md:29`, `docs/plans/2026-08-16-pi_as_main_agent_b874eaf6.plan.md:45`).
Those same lines called `cloud-readonly-gate.sh` unportable, and the later parity audit (`2026-08-18-amazing-now-with-all-wild-kettle.md`) reversed that and bridged it.
rtk was never revisited, so the gap is an oversight rather than a standing decision.

Outcome: a Pi session with `RTK_ENABLE` set gets the same command rewrites and the same visible opt-in state as a Claude session, with the gate ordering Claude's hook array guarantees.

## Why this lands in guardrails.ts and not a new extension

Pi loads extensions with `readdirSync` and no sort (`dist/core/extensions/loader.js:518`), then runs every `tool_call` handler in load order, returning early only on `block` (`dist/core/extensions/runner.js:701-721`).
herdr installs its own extension into the same directory (`roles/ai/tasks/main.yml:140-143`), so the directory is not even exclusively ours.

Claude's ordering is load-bearing: rtk is the **last** hook in the `PreToolUse` Bash array, after the three gates.
A standalone `rtk.ts` cannot reproduce that.
If it won the race, `git-skill-gate.sh` and `cloud-readonly-gate.sh` would receive `rtk git status` instead of `git status` and could stop matching, silently disarming both gates.

Folding the rewrite into `guardrails.ts`'s existing single `tool_call` handler makes the order a property of the code rather than of the filesystem.

## Changes

### 1. `roles/ai/files/pi/extensions/guardrails.ts`

**Extract the spawn core.**
`runHook` (`:92-131`) already holds every fail-open guarantee worth having: a `settled` flag with `clearTimeout`, a `SIGKILL` timeout, `child.on("error")` resolving allow, and a swallowed stdin `EPIPE`.
Pull that into `spawnJson(exec: string, args: string[], payload: unknown): Promise<{ code, stdout, stderr }>`, leaving `runHook` to own the `existsSync(script)` guard at `:94-96` and the `HookVerdict` mapping (`blocked: code === 2`).
Keep the literal `stdio: ["pipe", "pipe", "pipe"]` in the extracted core: `test_pi_guardrails.py:138-162` asserts that exact string is present in the source.

**Add `rtkRewrite(command: string, cwd: string): Promise<string | undefined>`.**
Verified contract, measured against `/opt/homebrew/bin/rtk`:

| stdin | exit | stdout |
|---|---|---|
| `{"tool_name":"Bash","tool_input":{"command":"ls -la"},"cwd":"/tmp"}` | 0 | `{"hookSpecificOutput":{...,"updatedInput":{"command":"rtk ls -la"},"permissionDecision":"allow"}}` |
| same with `echo hi` or `npm test` | 0 | empty |

So exit status carries nothing; the discriminator is an empty stdout. Parse `hookSpecificOutput.updatedInput.command` and return `undefined` on empty stdout, a parse failure, a missing `updatedInput`, or a value equal to the input.
Reuse the `askedForPermission` parsing shape at `:150-161`, which already reads `hookSpecificOutput` defensively.

Two details:
- Gate on `process.env.RTK_ENABLE` being non-empty before spawning, mirroring the `[ -n "$RTK_ENABLE" ]` semantics at `settings.json:257` and the `os.environ.get("RTK_ENABLE")` check at `statusline.sh:288`. Any non-empty value is on.
- Pi's settings have no `env` block, so `RTK_HOOK_AUDIT` cannot be set the way Claude sets it. Pass it in the spawn env: `{ ...process.env, RTK_HOOK_AUDIT: "1" }`.

No `command -v rtk` equivalent is needed for the rewrite path. A missing binary is `ENOENT` on spawn, which the extracted core's `child.on("error")` already turns into a no-op.

**Call it last in the bash branch** of `guard` (`:271-305`).
Today the branch ends by returning `blockResult(await runHook("pre-commit-verify.sh", ...))`.
Bind that verdict, return early if it blocked, then apply the rewrite by mutating in place and return `undefined`:

```ts
event.input.command = rewritten;
```

`ToolCallEventResult` is only `{ block?, reason?, terminate? }` (`types.d.ts:779-789`) and its own doc comment says to mutate `event.input` instead, so there is no return channel for a rewrite.
The `tool_input` const at `:272` holds the original command and all three gates have already consumed it, so they are unaffected.

**Residual risk to record in the docblock, not fix:** another extension's `tool_call` handler running after ours sees the rewritten command. That is the same exposure Claude has, where rtk is last in the array but nothing after the array is ordered against it.

**Add a `session_start` handler for the footer segment.**
Mirror `statusline.sh:279-290`'s three states exactly: nothing when `rtk` is off `PATH`, `✂️ rtk` when `RTK_ENABLE` is set, `✂️ rtk off` otherwise.

- API is `ctx.ui.setStatus(key, text)` (`types.d.ts:79-80`), sync, `void`, additive across extensions, `undefined` clears. Not `setFooter`, which replaces the whole footer.
- Namespace the key as `dotfiles-rtk`, following the reasoning already written at `velocity.ts:37-39`. Statuses are a keyed map where last writer wins, and herdr shares the directory. It sorts before `dotfiles-velocity`, so it renders to its left.
- Colour through `ctx.ui.theme.fg(...)` as `velocity.ts:98-111` does; dim the `off` state.
- Fire on every `session_start` reason, unlike velocity's `FRESH` set: this reads env, which cannot change mid-session, so one write per session is both sufficient and correct on resume.
- For the PATH check, walk `process.env.PATH.split(":")` with `existsSync`. `existsSync` is already imported at `:40`, and this avoids a spawn for a display string.
- Wrap in `try { } catch { }` per `velocity.ts:141-143`. A footer is never worth interrupting a session for.

Keep `export default` as the only export (`:310`), and keep the outer `try/catch` at `:312-319` as the single fail-open net.

**Update the module docblock** to say the extension now does two jobs, and why the rewrite lives here rather than in its own file.

### 2. `lib/python/tests/test_pi_guardrails.py`

Extend rather than add a new suite, since the code lives in `guardrails.ts`.
Follow the file's existing source-as-string style, which reads the text once in the module-scoped `source` fixture (`:64-66`) and asserts with substrings and narrow regexes.

- `RTK_ENABLE` is read before the spawn.
- The invocation is `hook`, `claude`, not `check`: the dry-run target skips rtk's audit side effects and would make `RTK_HOOK_AUDIT` dead weight.
- `RTK_HOOK_AUDIT` appears in the source, and its value matches `settings.json:11`.
- The rewrite is applied by assigning `event.input.command`, and `updatedInput` is the key read.
- **Ordering, the point of the whole change:** the index of the rewrite call in the source is greater than the index of each of `git-skill-gate.sh`, `cloud-readonly-gate.sh` and `pre-commit-verify.sh`.
- The status key is namespaced and matches the glyphs in `statusline.sh`.

Add `rtkRewrite` to the `DRIVEN` tuple at `:189` so the runner half (`:174-314`) can exercise it in node, and `pytest.skip` when `shutil.which("rtk")` is absent, matching how that half already skips on a missing `pi` or `node`.

New comments must avoid em and en dashes: `test_no_hook_logic_is_reimplemented` (`:123-135`) asserts their absence, and `em-dash-gate.sh` gates the write.

No `pytest.ini` change. `lib/python/tests` is already a testpath, and nothing enumerates `roles/ai/files/pi/extensions/`.

### 3. `docs/internals/pi-harness.md`

Add a `##` section after `## Permissions and the sandbox`, which is where the gate-ordering discussion already lives (`:37`).
It needs to cover: rtk is a rewrite and not a gate, so it is the one thing here that mutates a call rather than refusing it; why it sits inside `guardrails.ts`; that `RTK_HOOK_AUDIT` moves from a settings `env` block to the spawn env because Pi has no `env` block; and that the footer segment mirrors the Claude statusline rather than inventing a state.

`CLAUDE.md:47` stays accurate as written, since `RTK_ENABLE` remains a manual per-shell export for both harnesses.

## Verification

1. `make test` for the extended suite. This is the only unattended target, and it covers both halves of `test_pi_guardrails.py`.
2. Confirm the symlink resolves without a playbook run: `roles/ai/tasks/main.yml:326-333` globs `files/pi/extensions/*.ts`, and configs are symlinks, so editing `guardrails.ts` takes effect in `~/.pi/agent/extensions/` immediately.
3. Manual, rewrite on: `RTK_ENABLE=1 pi`, ask for `ls -la`, confirm the executed command is `rtk ls -la` and the footer shows `✂️ rtk`.
4. Manual, rewrite off: plain `pi`, same request, confirm the command runs unrewritten and the footer shows `✂️ rtk off`.
5. Manual, gates intact and this is the regression the design exists to prevent: with `RTK_ENABLE=1`, ask for a bare `git commit` outside `/skill:commit` and confirm `git-skill-gate.sh` still refuses it. A refusal that stopped arriving would mean the rewrite is landing before the gate.
6. Manual, fail-open: with `RTK_ENABLE=1` and `rtk` temporarily off `PATH` (`env PATH=/usr/bin:/bin pi`), confirm commands still run and the footer segment disappears rather than reading `off`.
