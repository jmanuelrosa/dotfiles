# A decision layer beside pi's sandbox, Design Doc

**Status:** Implemented
**Author:** José Manuel Rosa Moncayo
**Date:** 2026-09-04
**Scope:** `roles/ai/files/pi/settings.json`, `roles/ai/files/pi/permission-system/config.json` (new), `roles/ai/tasks/main.yml`, `lib/python/tests/test_pi_permissions.py` (new), `lib/python/tests/test_pi_sandbox.py`, `docs/internals/pi-harness.md`, `roles/ai/README.md`

## Summary

Pi confines what a command may touch but has no view of what a command *is*. `@gotgenes/pi-permission-system` adds that second layer: allow / ask / deny rules over bash command shape, tool names, MCP servers and file paths. It is installed beside `pi-sandbox`, not instead of it, and its config is derived from the same `roles/ai/files/claude/settings.json` that already produces `sandbox.json`, so one hand-edited statement of policy continues to serve both harnesses, and 98 Claude rules that reached pi as nothing start being enforced.

## Motivation

Claude Code is hard to talk out of a destructive command because it runs two independent layers. Its `sandbox` block decides which paths and domains a subprocess can reach at the OS level, and its `permissions` block decides whether a particular action is permitted at all: 29 allow rules and 153 deny rules covering command shape, tool names and MCP servers. Neither layer subsumes the other, since the sandbox would happily let `git push --force` through, because force-pushing touches only paths the agent already owns.

Pi today has the first layer and not the second. `roles/ai/files/pi/sandbox.json` is derived by `derive()` at `lib/python/tests/test_pi_sandbox.py:112`, and that derivation carries only the *path* half of Claude's permissions: `Read(...)` patterns become `denyRead`, `Edit(...)` patterns become `denyWrite`, and everything else is dropped. Counting the deny list as it stands, that is 42 `Edit` rules and 38 `Read` rules translated, and 64 `Bash(...)` patterns plus 9 bare tool and MCP names silently discarded. Add the 25 `Bash(...)` entries and 2 bare web tools in the allow list and 100 of 182 rules have no representation in pi at all. This design carries 98 of them; the two web tools are dropped because pi registers neither.

The consequences are concrete and already written down. `lib/python/tests/test_pi_sandbox.py:36-38` records the gap verbatim, naming a permission package as the thing that would carry those rules "if that ever earns its keep". `docs/internals/pi-harness.md:33` repeats it. Meanwhile the deny list contains the rules that matter most when an agent is wrong rather than malicious: `git push --force *`, `git reset --hard *`, `rm -rf *`, `sudo *`, `diskutil eraseDisk`, `gh pr merge *`. In Claude those are refusals. In pi they are ordinary commands that happen to stay inside the sandbox.

A second, smaller motivation: pi-permission-system withholds a tool from the model entirely when every pattern under its surface resolves to `deny`. The four `mcp__*` denies and five bare tool denies (`Workflow`, `Artifact`, `ScheduleWakeup`, `ReportFindings`, `ShareOnboardingGuide`) currently cost pi nothing but also protect nothing; under the new layer they disappear from the tool list before the agent's first turn.

## Non-goals

- **Replacing `pi-sandbox`.** The package's own scope section names isolation as a non-goal: "This is a decision layer, it decides and records; a sandbox contains." Removing `pi-sandbox` would trade OS confinement for rules. Both stay.
- **Closing the Cursor-provider bypass.** `defaultProvider: cursor` routes tool calls through Cursor's host tools unless `PI_CURSOR_EXPOSE_BUILTIN_TOOLS` is exported, and a host tool emits no `tool_call`. The new layer inherits that blind spot exactly as `pi-sandbox` and `guardrails.ts` do, and the `⚠️ gates off` footer badge already reports it. Nothing here changes that.
- **The two untranslatable sandbox gaps.** `excludedCommands` and `$TMPDIR` are limitations of `@carderne/sandbox-runtime`. A decision layer does not touch them; both paragraphs in `docs/internals/pi-harness.md` stay.
- **Hand-authoring a pi-only policy.** No rule is written directly into the pi config. If a rule should exist, it goes in Claude's settings and is derived.
- **The authorizer chain.** `@gotgenes/pi-permission-model-judge` and the `authorizerChain` seam are out of scope; `authorizerChain` stays `[]`.
- **Removing `guardrails.ts`.** Its four bridged `PreToolUse` hooks are intent friction (the git-skill gate, the em-dash gate, the rtk rewrite), not allow/deny policy. It keeps its `tool_call` handler.

## Background

### What pi enforces today

`roles/ai/files/pi/settings.json:41` declares `npm:pi-sandbox`, and `roles/ai/tasks/main.yml:256` symlinks the derived `pi/sandbox.json` into `~/.pi/agent/`. The extension hooks `tool_call` (`src/extension.ts:278-343`) and applies filesystem and network policy: a `write`/`edit` outside `allowWrite` prompts, one inside `denyWrite` is refused, a `read` outside `allowRead` prompts, and bash runs inside an OS sandbox.

What it does not do is look at the command. Every one of the 64 `Bash(...)` deny patterns describes command shape, and shape is not something a path-confinement layer can match on.

### What `@gotgenes/pi-permission-system` enforces

Version 27.1.1, an npm package that registers itself as a pi extension. Three states, `allow` (silent), `deny` (refusal with a reason) and `ask` (interactive prompt), over surfaces that map almost one-to-one onto Claude's rule vocabulary:

| Surface | Matches on |
|---|---|
| `bash` | each top-level command in a chain, with `*` / `?` wildcards |
| `path`, `path_read`, `path_write` | cross-cutting file paths, for every tool and bash alike |
| `external_directory` | whether the action reaches outside the session cwd |
| `read`, `write`, `edit`, `grep`, `find`, `ls`, any tool name | per-tool, optionally with path patterns |
| `mcp` | MCP server and tool names |
| `skill` | skill names |

Four behaviours make it a real gate rather than a suggestion. It **hides denied tools before the agent starts**, so no turn is spent probing. It **fails closed** since 16.0.0: an internal gate error blocks, and an unparseable bash command resolves to `ask` rather than falling through. It **decomposes chains**, so `cd /repo && rm -rf x` evaluates both halves, including command substitutions and process substitutions, and the most restrictive result wins. And a `path` deny **cannot be overridden by a per-tool allow**, matching both the referenced path and its symlink-resolved form.

Two semantics differ from Claude's and drive the design below. Within a surface map, **last matching rule wins**, where Claude's rules are order-free with deny beating allow. And a doubled star is not a globstar: a single `*` already crosses directory separators, and the doubled form is documented as equivalent to it.

### Claude's rules, by shape

Verified against the current `roles/ai/files/claude/settings.json`:

| Rule form | Count | Example |
|---|---|---|
| `Bash(cmd:*)` (allow only) | 25 | `Bash(rg:*)`, `Bash(gh:*)` |
| `Bash(literal args)` (deny only) | 64 | `Bash(git push --force *)`, `Bash(rm -rf *)` |
| `Read(pattern)` | 38 | `Read(~/.ssh/**)` |
| `Edit(pattern)` | 44 | `Edit(**/.env)`, plus two `.env.example` allows |
| bare tool name | 5 | `Workflow`, `ScheduleWakeup` |
| `mcp__server` | 4 | `mcp__notion`, `mcp__supabase` |
| bare web tool | 2 | `WebFetch`, `WebSearch` (allow) |

The 64 bash denies are already written in space-separated form, which is pi-permission-system's pattern syntax verbatim. The colon form appears only in the allow list, where `Bash(rg:*)` means "`rg` with any arguments" and translates to `"rg *"`. There is no `ask` array in this settings file, so every derived rule is an `allow` or a `deny`.

### Tool names under the Cursor provider

A concern worth closing early: `shellTools` exists for extensions that replace `bash` with a differently-named tool, and if pi-cursor-sdk did that, all 64 bash rules would miss. It does not. `BUILTIN_NATIVE_CURSOR_TOOL_NAMES` at `pi-cursor-sdk/src/cursor-native-tool-names.ts:5` is `["read", "bash", "edit", "write", "grep", "find", "ls"]`, the same names pi uses. With `PI_CURSOR_EXPOSE_BUILTIN_TOOLS=1` (exported at `roles/shell/files/fish/config.fish:81`) the bridge exposes pi's own `bash`, which is the tool the gates see. **`shellTools` stays empty.**

## Design rules

- **One hand-edited policy file.** `roles/ai/files/claude/settings.json` stays the only place a rule is written. Both pi configs are derived, both are committed, both fail a test on drift.
- **Two layers, two files, two jobs.** `sandbox.json` says which paths and domains are in scope. `permission-system/config.json` says whether a particular action on an in-scope path may proceed. Neither absorbs the other's rules.
- **Order is load-bearing in the generated file.** Because last-match-wins replaces deny-beats-allow, each surface map is emitted as fallback first, then allows, then denies. `Bash(pgcli:*)` is allowed and `Bash(pgcli)` is denied in the same Claude file; only the ordering makes that come out right.
- **A doubled star is not a globstar here.** `to_sandbox_pattern` prepends a slash to `**/` patterns because pi-sandbox resolves relative patterns against cwd. This package has no such behaviour and treats `*` as already recursive, so it needs its own translator rather than a reuse.
- **Where the sandbox holds, do not also ask.** Claude sets `sandbox.autoAllowBashIfSandboxed: true`, which is this config stating the principle in its own words: a sandboxed action does not earn a prompt on top. pi-sandbox confines `bash`, `write` and `edit` to `allowWrite` and prompts outside it, so those three surfaces are `allow` here and this layer contributes only the deny lists. That is Claude parity read as intent rather than as literal prompt count, and it also avoids two prompts for one edit. Flipping `write` and `edit` to `ask` is the one-line change if literal parity is preferred.
- **The project boundary still asks.** `external_directory` is `ask`, because Claude sets no `additionalDirectories` and prompts for a path outside the tree. The one exception is `piInfrastructureReadPaths`, which covers the harness reading its own installed trees and no project path, asserted by a test.
- **The version is pinned, and the pin is chosen from what will install.** Every other entry in `packages` rides latest. This one does not, because the package ships fail-closed breaking changes (16.0.0, 22.0.0, 27) that turn a silent allow into a prompt or a block. An unattended `pi update` should not be able to change what your shell is allowed to run. The pin is 27.1.1 rather than the registry's `latest` because `~/.npmrc` sets `min-release-age=7`, npm's supply-chain cooldown, which makes any version published in the last week unresolvable: a pin taken from `latest` fails `pi install` with `ETARGET` until it has aged past the window. The two constraints agree more than they conflict, since a security layer is the last package that should run week-old code unquarantined.
- **A reason needs a pattern to hang on.** A surface value is an action string or a map of patterns, so `{"action": "deny", "reason": ...}` written straight against a tool name is not the third thing it looks like: it parses as a map whose patterns are the literal words `action` and `reason`, and the config is rejected. Because a rejected global scope enforces none of these denies, the malformation is silent in the worst direction, so a wholly denied tool is emitted as `{"*": <denial>}` and a test asserts no surface states an action without a pattern. The shape is also what the package resolves against: every surface evaluates its tool-level state against the `*` catch-all, with no per-kind branch (`src/permission-manager.ts:263-269`).
- **Shallow by construction.** This design adds no abstraction of its own; the depth (chain decomposition, symlink resolution, wrapper flooring, fail-closed handling) lives in the package. The repo contributes a translation function and a drift test, which is the same shape `test_pi_sandbox.py` already has.

## Design

### 1. Package registration

`roles/ai/files/pi/settings.json`, in the existing `packages` array beside `npm:pi-sandbox`:

```json
"packages": [
  "git:github.com/earendil-works/pi-review",
  "npm:@tintinweb/pi-subagents",
  "npm:pi-cc-patch",
  "npm:pi-cursor-sdk",
  "npm:pi-sandbox",
  "npm:@gotgenes/pi-permission-system@27.1.1",
  "npm:pi-ask-user",
  "npm:pi-mcp-adapter"
]
```

A versioned spec is pinned and skipped by `pi update --extensions` / `--all` (pi `docs/packages.md:63`), which is the property being bought. Moving the pin is `pi install npm:@gotgenes/pi-permission-system@<new>` plus the settings edit, deliberately. Pick the new version from what has aged past `min-release-age`, not from `latest`, and revalidate the config against that version's shipped schema before committing the move:

```bash
npx --yes ajv-cli@5 validate --spec=draft2020 --strict=false \
  -s node_modules/@gotgenes/pi-permission-system/schemas/permissions.schema.json \
  -d roles/ai/files/pi/permission-system/config.json
```

The package also advertises native `@gotgenes/pi-subagents` integration. This repo runs `@tintinweb/pi-subagents`, so per-agent policy forwarding is not assumed to work; nothing in this design depends on it.

### 2. The derived config

New file at `roles/ai/files/pi/permission-system/config.json`. A directory rather than a bare `permission-system.json`, because the package expects `config.json` inside a directory named after itself, and because the package writes its logs into that same directory at runtime. The repo contributes only the one file.

Shape as generated, elided at every `...`. The real file is 672 lines because each deny carries its originating rule as a reason:

```json
{
  "debugLog": false,
  "permissionReviewLog": true,
  "yoloMode": false,
  "shellTools": {},
  "authorizerChain": [],
  "piInfrastructureReadPaths": [
    "/opt/homebrew/*/@earendil-works/pi-coding-agent/*",
    "~/.pi/agent/*",
    "~/.claude/*"
  ],
  "permission": {
    "*": "allow",
    "read": "allow", "grep": "allow", "find": "allow", "ls": "allow",
    "write": "allow", "edit": "allow",
    "bash": {
      "*": "allow",
      "find *": "allow", "rg *": "allow", "gh *": "allow", "...": "...",
      "git push --force *": { "action": "deny", "reason": "denied by Claude Code policy: Bash(git push --force *)" },
      "rm -rf *": { "action": "deny", "reason": "denied by Claude Code policy: Bash(rm -rf *)" },
      "...": "..."
    },
    "path_read": { "*": "allow", "~/.ssh/*": { "action": "deny", "reason": "..." }, "...": "..." },
    "path_write": { "*": "allow", "...": "...", "*/.env.sample": "allow", "*/.env.example": "allow" },
    "external_directory": "ask",
    "mcp": { "*": "allow", "notion*": { "action": "deny", "reason": "..." }, "...": "..." },
    "Workflow": { "*": { "action": "deny", "reason": "..." } },
    "...": "..."
  }
}
```

Final surface counts: `bash` 89 keys (one fallback, 24 allows, 64 denies), `path_read` 39, `path_write` 45, `mcp` 5, plus five bare tool denies. `piInfrastructureReadPaths` names the Homebrew pi install because pi ships as a brew formula here and the agent reads pi's own docs from that tree, which is the package's own documented example, plus the two agent payload directories this repo owns and symlinks into place. A project path never belongs there, because this knob bypasses the boundary gate.

### 3. The translation table

One function, `derive_permissions(settings)`, living in a new `lib/python/tests/test_pi_permissions.py` beside its sibling: same placement, same docstring-as-specification convention, same regeneration one-liner in the module docstring.

| Claude rule | pi surface | pi pattern | Notes |
|---|---|---|---|
| `Bash(cmd:*)` | `bash` | `cmd *` | allow list only; the trailing `*` also matches bare `cmd` |
| `Bash(git push --force *)` | `bash` | `git push --force *` | verbatim; the deny list is already in this syntax |
| `Read(~/.ssh/**)` | `path_read` | `~/.ssh/*` | the doubled star collapses to one |
| `Read(**/.env)` | `path_read` | `*/.env` | `*` already recurses, and keeping the slash is what stops it also matching `settings.env` |
| `Edit(**/.env)` | `path_write` | `*/.env` | |
| `Edit(**/.env.example)` | `path_write` | `*/.env.example` | allow, emitted in a fourth band after the denies |
| `mcp__notion` | `mcp` | `notion*` | prefix, so both the server and its tools |
| `Workflow` | `Workflow` | (none) | string form, `"deny"` |
| `WebFetch` / `WebSearch` | (none) | (none) | dropped: not pi tools |

The whole path translation is `pattern.replace("**", "*")`. That reads as too simple until you check the corpus: every Claude path rule spells the globstar as either a leading `**/` or a trailing `/**`, never `***`, and in this dialect `**` is documented as the same token as `*`. So collapsing it is not an approximation, it is removing a duplicated character.

Directional path surfaces (`path_read` / `path_write`) rather than the bare `path` key, because Claude already separates the two: `Edit(**/.env.example)` is allowed while `Read(**/.env)` is denied, and a bare `path` key expands into both directions, which would flatten that distinction.

Each `deny` is emitted in object form with a `reason`, so a refusal tells the agent why instead of dying opaquely. The reason is generated from the rule (`"denied by Claude Code policy: Bash(rm -rf *)"`), not hand-written per rule.

### 4. Ordering within a surface

Every surface map is emitted in four bands:

1. the `"*"` fallback
2. every `allow` rule for that surface, in Claude's order
3. every `deny` rule for that surface, in Claude's order
4. any `allow` that exists to carve an exception out of a deny

Bands 1 to 3 recover Claude's deny-beats-allow under last-match-wins. One live case proves it is not theoretical: `Bash(find:*)` is allowed while `Bash(find / *)`, `Bash(find ~ *)`, `Bash(find ..)` and `Bash(find .. *)` are denied, so `find . -name x` resolves allow and `find / -name id_rsa` resolves deny. Emitted the other way round, both come out permissive.

Band ordering is not enough for one case, because two rules can translate to the *same key*. `Bash(pgcli:*)` is in Claude's allow list and `Bash(pgcli *)` is in its deny list, and both become the pattern `pgcli *`. A JSON object cannot hold two actions for one key, and emitting both would produce a duplicate key whose winner depends on the parser. Claude resolves the conflict as a deny, so the derivation drops any allow whose translated pattern collides with a deny, and a test asserts `pgcli` and `pgcli --dsn x` both resolve to deny.

Band 4 is the inversion. `Edit(**/.env.sample)` and `Edit(**/.env.example)` are allows, and under last-match-wins an allow can only except a deny by coming after it. Worth being precise about what they do today: Claude's deny list names `.env`, `.env.local`, `.env.staging` and six more by name but has no generic `**/.env.*` rule, so nothing currently shadows either carve-out and both are inert. They are carried anyway, in their own band, so that adding a broader `.env.*` deny to Claude later does not silently swallow them. A test pins the band to exactly those two patterns, the same shape as `test_the_read_carve_outs_are_exactly_the_files_bash_cannot_work_without` in `test_pi_sandbox.py`, where a grant arriving without a written reason fails the suite.

### 5. Ansible wiring

Two edits in `roles/ai/tasks/main.yml`:

- Add `{{ HOME }}/.pi/agent/extensions/pi-permission-system` to the directory list at `:46-48`. The package writes its logs there, so the directory must exist and must not be a symlink into the repo.
- A symlink task for the single file, following the pattern of the block at `:242-264`:

```yaml
- name: Symlink pi permission-system config
  ansible.builtin.file:
    src: "{{ role_path }}/files/pi/permission-system/config.json"
    dest: "{{ HOME }}/.pi/agent/extensions/pi-permission-system/config.json"
    state: link
    force: true
```

The existing extension task at `:327-334` globs `files/pi/extensions/*.ts` and is unaffected: the new config lives under `files/pi/permission-system/`, not under `files/pi/extensions/`, so it cannot be swept into the glob.

No project-scoped config is shipped. Since 22.0.0 a project config loads only once pi trusts the directory, and a per-repo policy is a second place a rule can live, which the first design rule forbids.

### 6. Tests

`lib/python/tests/test_pi_permissions.py`, mirroring its sibling. 24 tests, all passing, and the full suite stays green at 1925 passed.

The one that does the real work is `resolve()`, a local reimplementation of the package's last-match-wins lookup. Asserting a deny is *present* in the file proves nothing, because a later allow can shadow it. So the destructive commands are checked by resolution rather than by membership:

- `git push --force origin main`, `git reset --hard HEAD~1`, `rm -rf build`, `sudo softwareupdate`, `diskutil eraseDisk`, `gh pr merge 12` and `find / -name id_rsa` each resolve to `deny`
- `rg pattern src`, `gh pr list`, `find . -name x` and `bunx ctx7 library fish` each resolve to `allow`, so the allow half survives the band ordering too
- `pgcli` and `pgcli --dsn x` resolve to `deny`, the collision case
- `~/.ssh/id_ed25519`, `~/.aws/credentials`, `~/.gitconfig` and `~/.zsh_history` resolve to `deny` on `path_read`, which is the read-layer split recovered
- `notion`, `notion_search`, `Supabase` and `supabase_query` resolve to `deny` on `mcp`, so denying a server reaches the tools it registers

The rest are structural: the drift gate, every Claude `Bash(...)` deny reaching the `bash` surface, the five bare tool denies reaching their own surface, no surface stating an action without a pattern to hang it on, the `path_write` band tail being exactly the two carve-outs, no doubled star and no unexpanded `$VAR` surviving, every deny carrying its originating rule as a reason, `yoloMode` off with an empty `authorizerChain`, `shellTools` empty, the pin matching a version regex, `pi-sandbox` still declared beside it, and the play linking the config.

One of those is retrospective. The first version of this work emitted a bare tool deny as `{"action": "deny", ...}` against the surface name, which the shipped schema rejects and which would have invalidated the whole global scope, enforcing none of the 98 rules. The tests as first written all passed, because they asked what each rule decided and never whether the file the package would read was well-formed. Validating the committed config against the package's own schema is what found it, so that command is now recorded beside the pin above, and the shape has a test of its own.

Two docstrings were falsified by this work and rewritten: `test_pi_sandbox.py` claimed the 64 bash rules "have no counterpart here", and its read-layer bullet described a loosening that `path_read` now closes.

### 7. Documentation

The permissions section of `docs/internals/pi-harness.md` becomes "Permissions: two layers, like Claude's": `pi-sandbox` contains, `pi-permission-system` decides, each with its derived file and its drift test. The four "cannot carry" bullets drop to three, since the bash-rules bullet is now false; `excludedCommands` and `$TMPDIR` survive unchanged, and the read-layer-split bullet gains a closing sentence, because `path_read` refuses what pi-sandbox only prompted. Four paragraphs are added for the new layer: what it matches on, the four load-bearing translation facts, why it is the one pinned package with its own config directory, and why `pi-permission-modes` was rejected, so the next reader does not re-litigate the survey. `roles/ai/README.md` gets a single bullet describing both layers in place of the old sandbox-only one.

Not done, and worth naming: `roles/ai/README.md` still says "Four ship" of the pi extensions where six do. That predates this work and correcting it means rewriting an unrelated sentence, so it is left alone rather than folded into this diff.

## Runtime behaviour matrix

Rows are what the agent attempts; columns are what happens before and after.

| Attempt | Before (pi-sandbox only) | After |
|---|---|---|
| `rg foo src/` | runs | runs, silently |
| `git push --force origin main` | runs | refused, naming `Bash(git push --force *)` |
| `rm -rf build/` | runs, since `build/` is inside `allowWrite` | refused |
| `sudo softwareupdate` | fails at the OS sandbox, opaquely | refused, with a reason the agent can report |
| `cd /repo && rm -rf x` | runs | refused; the chain is decomposed and the most restrictive half wins |
| `echo $(rm -rf x)` | runs | refused; command substitution is evaluated too |
| `find . -name x` | runs | runs, silently (`Bash(find:*)`) |
| `find / -name id_rsa` | runs | refused (`Bash(find / *)`) |
| edit a file in the project | runs, silently | unchanged: `edit` is `allow`, the sandbox still holds the boundary |
| write outside `allowWrite` | prompts, at the sandbox | prompts, at the sandbox; then `external_directory` also asks |
| read `~/.ssh/id_ed25519` | **prompts**, since the read tool never consults `denyRead` | refused |
| read `~/.gitconfig` | allowed, the bash carve-out leaking to the read tool | refused, while `git commit` still reads it |
| write `.env` | refused (`denyWrite`) | refused by both layers |
| write `.env.example` | allowed; no rule matches it in either harness | allowed, and now explicitly, in the carve-out band |
| an `mcp__notion` call | runs | refused, naming the rule; the `mcp` tool stays visible because its surface has an allow fallback |
| a `Workflow` call | runs | tool withheld before the first turn, since its whole surface is `deny` |
| a command the parser cannot read | runs | prompts, fail-closed since 16.0.0 |
| any of the above under Cursor host tools, exposure off | ungated | ungated, and the `⚠️ gates off` badge says so |

Two rows are worth reading twice. `read ~/.gitconfig` is the read-layer split recovered: pi-sandbox has to hand git that file at the syscall level so commits work, and its one `filesystem` block cannot then hide it from the read tool. This layer's `path_read` gate is token-based for bash, so it refuses `cat ~/.gitconfig` and the `read` tool while `git commit`, which never names the path, is untouched. And the `mcp__notion` row corrects an assumption from the draft: a tool is withheld from the model only when *every* pattern under its surface resolves to `deny`, so the four MCP denies block calls rather than hiding the tool, while the five bare tool names do disappear.

## Alternatives considered

- **Replace `pi-sandbox` with the permission system.** The original request. Rejected because the package names isolation as an explicit non-goal and defers it to "an agent sandbox, which this package's scope decisions are exported to rather than duplicated in". Swapping would trade OS-level confinement of network and filesystem for command-shape rules, which is a net loss. Claude Code is strong because it runs both; so should pi.
- **Hand-author a pi-native policy file.** Faster to write, and immediately a second place a rule can live. The repo has already paid for that lesson once, which is why `sandbox.json` is derived and drift-tested rather than maintained.
- **Ride latest, unpinned, like every other package.** Rejected on the package's own changelog: four breaking releases, several of them fail-closed corrections that convert a silent allow into a prompt. A `pi update` should not be able to change what commands run. `min-release-age=7` in `~/.npmrc` independently rules it out anyway, since `latest` is unresolvable for its first week.
- **Exempt the package from the npm cooldown via `min-release-age-exclude`.** Would have kept the pin on 31.0.1. Rejected as backwards: the cooldown exists so a compromised publish is caught before it is installed, and the package that decides what the shell may run is the last one to hand that guarantee up. Waiting is cheap here because 27.1.1 already carries every gate this design relies on, verified against its shipped schema rather than assumed.
- **`"*": "ask"` and `"bash": {"*": "ask"}`.** Closest to Claude's *literal* prompt behaviour for an unlisted command. Rejected because Claude does not actually prompt for unlisted bash here: `sandbox.autoAllowBashIfSandboxed: true` auto-approves anything the sandbox confines, and pi-sandbox confines bash the same way. An `ask` fallback would therefore be stricter than the harness it is copying, with 25 commands allowlisted and everything else prompting. It is also unverified whether a blocking prompt resolves cleanly when the caller is the Cursor SDK agent waiting on an MCP round-trip.
- **`pi-permission-modes`, one package doing both jobs.** The strongest alternative in the ecosystem, and the closest thing in it to Claude Code's actual UX. It bundles an OS sandbox (upstream `@anthropic-ai/sandbox-runtime` rather than the `@carderne` fork) with a policy engine, parses bash with a real tree-sitter AST instead of wildcards, hides tools per mode, and ships switchable modes on `alt+m` (Default, Plan, Build, YOLO) with a tighten-only project config, which is a structurally stronger property than trust-gating a whole file. Rejected on four counts, the first decisive. It **disables its sandbox entirely in a git worktree**, by its own documentation, because bubblewrap cannot bind `.git/hooks` under a file; `wt add` is a primary workflow here and `wt.fish` already carries a bespoke per-worktree grant to keep pi-sandbox working there, so this would trade a working sandbox for prompts in the most common working directory. Its value is concentrated in TUI interactions (mode cycling, the network chip, `/net` approvals) that the Cursor bridge does not deliver, and `defaultProvider` is `cursor`. It was six weeks stale against a host that ships weekly, at 267 weekly downloads against 8,568. And its config is mode-shaped, four modes each carrying a full policy, where Claude's is one flat list, so deriving it would put invented judgment into the generator.
- **`pi-verdict`, a model classifier for the gray zone.** Routes anything the rules do not settle to a classifier that sees conversation context, which is genuinely closer to how Claude Code's auto mode decides. Rejected because it trades determinism, the property this whole design rests on, for per-call latency, token cost and nondeterminism. It also says plainly that it is "a permission gate, not a sandbox," so it replaces neither layer. Worth revisiting only if the deterministic policy proves insufficient in practice. Its own published landscape research rates `@gotgenes/pi-permission-system` as the deterministic reference with fail-closed behaviour, which is useful third-party confirmation of the choice.
- **`pi-better-sandbox`.** Confines writes only, leaving reads and network entirely open, and is opt-in per session. Strictly less than pi-sandbox already provides.
- **`pi-permission-suite`.** A fork of `@gotgenes/pi-permission-system` adding four approval modes, last published in July. A stale fork of the upstream being chosen anyway.
- **`@trim21/personal-pi-extensions`.** Bubblewrap-based, so inert on darwin.
- **Write our own permission engine.** Rejected on other people's scar tissue. `@gotgenes/pi-permission-system` has shipped four breaking releases, each a fail-closed correction for a discovered bypass. `pi-verdict` publishes a rule-layer audit reporting 8 of 8 bypasses reproduced against its own first design. All the difficulty sits in one place, deciding what a shell string will actually do: wrapper flooring for `bash -c`, `eval`, `sudo`, `env`, `xargs` and `find -exec`; command substitution in redirect targets; interpolating versus quoted heredocs; symlink canonicalization on both the referenced and resolved spelling. Writing that here means rediscovering every one of those without their test corpora. The line this repo already draws is the right one: `guardrails.ts` is homegrown and deliberately fail-open intent friction, while anything that has to hold against an adversarial string is someone else's battle-tested engine.
- **Symlink the whole `permission-system/` directory into `~/.pi/agent/extensions/`.** One task instead of two. Rejected: the package writes `logs/*.jsonl` into that directory, which would land unredacted bash command strings inside the git tree.
- **A project-scoped `.pi/extensions/pi-permission-system/config.json` in this repo.** Rejected: a second place a rule can live, and since 22.0.0 it only loads behind project trust, so it would be silently inert in an untrusted checkout.

## Testing decisions

The test boundary is the derived file, not the package. What is asserted is that the translation produces the policy Claude states: that every Claude deny reaches a pi surface, that ordering preserves deny-beats-allow, and that the committed file matches what the function generates. What the package does with that file is its own test suite's problem.

Prior art is `lib/python/tests/test_pi_sandbox.py` in full: derivation function in the test module, module docstring as the specification, regeneration one-liner in the docstring, a single equality test as the drift gate, then named tests for each invariant that would otherwise be silent. The new module follows it closely enough that the two read as a pair, and it registers under the existing `lib/python/tests` root in `pytest.ini` with no config change.

## Open questions

Two questions from the draft are now settled and recorded in Design rules: the bash fallback stays `allow` because `autoAllowBashIfSandboxed` says Claude's does too, and the 25 `Bash(cmd:*)` allows are carried so the derivation is total rather than partial. What remains:

- **`permissionReviewLog` records bash command strings unredacted** into `~/.pi/agent/extensions/pi-permission-system/logs/`. It ships `true`, because an audit trail of every gate decision is the thing that makes a policy reviewable, and the play deliberately creates a real directory there rather than a link into the repo so the log cannot land in git history. But this repo denies the agent `~/.zsh_history` for exactly this shape of risk. Proposal, not yet done: add `Read(~/.pi/agent/extensions/pi-permission-system/logs/**)` to Claude's deny list, so both derivations carry it and the log exists without being readable by the agent that generated it.
- **`external_directory: ask` has not met a real session yet.** `piInfrastructureReadPaths` covers the pi install and the two agent payload trees, which should absorb the routine cases, but `~/.cursor` is not in that list and a first session in an unfamiliar project is where an unexpected prompt storm would show up. Watch which prompts actually fire before adding `external_directory_read` allows, since every entry there is a real widening.
- **Whether an `ask` prompt resolves under the Cursor provider.** `external_directory` is the only surface that can produce one today, so this is now a live question rather than a hypothetical. `pi-cursor-sdk` ships `cursor-mcp-timeout-override.ts`, which suggests the round-trip timeout is a known pressure point. Verification is one deliberate out-of-tree read in a Cursor-provider session.
- **Per-agent policy forwarding is untested.** The package advertises native `@gotgenes/pi-subagents` integration and this repo runs `@tintinweb/pi-subagents`. Nothing in this design depends on it, but a subagent's `ask` may simply not reach the parent UI.

## Appendix, affected files

**Modified**

- `roles/ai/files/pi/settings.json`, pinned package spec added to `packages`
- `roles/ai/tasks/main.yml`, the review-log directory in the `state: directory` loop, a rewritten comment on the `pi/sandbox.json` entry, and a new `Symlink pi permission-system config` task
- `lib/python/tests/test_pi_sandbox.py`, two docstring paragraphs this work falsified
- `docs/internals/pi-harness.md`, the permissions section, rewritten as two layers
- `roles/ai/README.md`, one bullet describing both layers

**Created**

- `roles/ai/files/pi/permission-system/config.json`, 672 lines, derived, committed, drift-tested
- `lib/python/tests/test_pi_permissions.py`, the derivation and its specification, 24 tests

**Deferred**

- `roles/ai/files/claude/settings.json`, one `Read(...)` deny for the review-log directory, pending the first open question

**Read only**

- `~/.pi/agent/npm/node_modules/pi-cursor-sdk/src/cursor-native-tool-names.ts`, confirms `shellTools` is unnecessary
- `~/.pi/agent/npm/node_modules/pi-sandbox/src/extension.ts`, the layer this one sits beside
- `roles/shell/files/fish/functions/wt.fish`, the per-worktree sandbox grant that ruled out `pi-permission-modes`
