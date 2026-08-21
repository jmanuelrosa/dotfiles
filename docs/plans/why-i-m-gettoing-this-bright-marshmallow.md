# Exempt `ctx7` from the Claude Code bash sandbox

## Context

`bunx ctx7` fails with a bare `✖ fetch failed` in real sessions, across at least three unrelated repos (a Playwright work repo, a `better-auth` project, and `topo-weather-legend` on 2026-08-20).
Every time, the agent falls back to reading an installed package or to WebSearch and says so, which is the documented fallback working as intended, but it means the one tool `AGENTS.md` mandates for every docs question is the one tool that does not reliably run.

What the failure is not, verified on this machine:

- Not a missing allowlist entry. `context7.com` and `*.context7.com` are both in `sandbox.network.allowedDomains` (`roles/ai/files/claude/settings.json:343-344`), and `mcp.context7.com` (the second host the package contacts) matches the wildcard.
- Not a project-level override. None of the three failing repos has a `.claude/settings.json`.
- Not a regression from `enableWeakerNetworkIsolation`, which has been set since 2026-04-09, months before the failures.
- Not the npm install. The `✖` glyph is ctx7's own output, so the package resolved and ran; only its HTTPS request died.

What it is, structurally: **ctx7 is the only CLI `AGENTS.md` mandates that is not in `sandbox.excludedCommands`.**
`git`, `gh`, `glab`, `acli`, `sentry`, `bru-cli`, `ntn`, `pgcli`, `aws`, `gcloud`, `gsutil` and `bq` all run outside the sandbox; `bunx` and `npx` appear neither there nor in `permissions.allow`.
So ctx7's request is the only mandated network call subject to the sandbox's egress path, and node's and bun's global `fetch` (undici) ignore `HTTP_PROXY`/`HTTPS_PROXY`, which is exactly the shape of failure a proxied sandbox produces: `curl` and `gh` keep working, an undici `fetch` returns a causeless `fetch failed`.

That last link is inferred rather than measured: in this session egress is unfiltered (`curl https://example.com` returns 200 despite not being allowlisted) and `bunx ctx7 library astro` works, so the failure could not be reproduced here.
The fix does not depend on which sandbox mechanism bit, only on ctx7 no longer being inside it.

Intended outcome: a docs question gets answered from current docs rather than from a fallback, without widening the sandbox for anything other than ctx7.

## Approach

Treat ctx7 like every other mandated CLI: exempt it, narrowly, and permit it so it does not prompt.

### 1. `roles/ai/files/claude/settings.json`

Add two entries to `sandbox.excludedCommands` (currently `:378-390`), keeping the existing grouping (single-token CLIs, then patterned ones):

```json
"bunx ctx7 *",
"npx -y ctx7 *",
```

Add two entries to `permissions.allow` (`:25-46`), beside the other domain CLIs:

```json
"Bash(bunx ctx7:*)",
"Bash(npx -y ctx7:*)",
```

The allow entries are not optional. `autoAllowBashIfSandboxed: true` is what silently approves ctx7 today; once the command leaves the sandbox that auto-approval no longer applies and every call prompts, which is why `aws`, `gcloud` and friends each carry both an exclusion and an allow rule.

Deliberately **not** bare `bunx` / `npx`: that would run any package on the registry outside the sandbox. The two-token prefix follows the existing `aws *` / `gcloud *` precedent.

`sandbox.network.allowedDomains` is untouched, so `roles/ai/files/pi/sandbox.json` does **not** need regenerating: `excludedCommands` is deliberately not translated into Pi's config (`lib/python/tests/test_pi_sandbox.py:106-124` derives from the network and path halves only). No test asserts on `excludedCommands`, so `make test` stays green either way.

### 2. `roles/ai/files/claude/AGENTS.md`

Two sentences in the ctx7 bullet (`:22`), because the exemption carries a usage constraint the current wording does not:

- ctx7 must be the **leading token** of the bash command. `cd x && bunx ctx7 ...`, a pipe into it, or a ctx7 call spawned from inside a script is not exempt and lands back in the sandbox. This is the same constraint already recorded for `acli` at `docs/internals/acceptance-criteria.md:19`.
- Under Pi the exemption does not exist at all, since `pi-sandbox` has no per-command exclusion. The existing "if ctx7 returns no usable match, say so, then fall back to WebSearch/WebFetch" line already covers the behaviour; extend it so a `fetch failed` (not just an empty result) explicitly routes to the same fallback with the failure named.

### 3. Documentation counts that go stale silently

Three places hardcode the size and the rationale of the exclusion list, and nothing tests them:

- `docs/internals/pi-harness.md:28` says "Claude runs twelve CLIs outside its sandbox so they can reach their own credential stores". Becomes fourteen entries, and the rationale needs widening: ctx7 is exempt for **network egress**, not for a credential store.
- `lib/python/tests/test_pi_sandbox.py:24` repeats the same count and the same rationale in the module docstring.
- `roles/ai/files/claude/hooks/cloud-readonly-gate.sh:8` is scoped to the four cloud CLIs, so it stays accurate. No edit; listed only so it is not "fixed" by mistake.

Pre-existing and out of scope: `roles/ai/README.md:15` says "Three things do not translate" while `docs/internals/pi-harness.md:26` lists four. Worth a separate one-word fix, not folded into this change.

## Verification

1. `make test`, the only unattended target, must stay green (no suite asserts on `excludedCommands`).
2. Restart Claude Code. `settings.json` is symlinked into `$HOME`, so the file change is live immediately, but the sandbox config is read at startup.
3. In a **new session in a different repo** (one of the three that failed, e.g. `~/Developer/personal/topo-weather-legend`), run `bunx ctx7 library astro "routing"` and confirm real results rather than `✖ fetch failed`. This is the actual acceptance test: it must be a repo other than `dotfiles`, since ctx7 already succeeds here.
4. Confirm the exemption stayed narrow: in the same session, a different npm package via `bunx` should still be sandboxed and should still prompt.
5. Confirm no prompt regression: ctx7 should run without a permission prompt, the way `gh` does.
6. `make check-role ROLE=ai`, a dry-run, expects no changes beyond the already-symlinked files.
