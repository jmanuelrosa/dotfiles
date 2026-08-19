# Closing the Claude / Pi parity gaps

## Context

`feature/pi-settings` made Pi a second harness over Claude's payload rather than a copy of it, and the rebase onto `main` brought in a large restructuring (`#75` right-sizing the always-loaded context, `#74` the token-spend work, the move of deep reference into `docs/internals/`).
Two things followed from that combination: some of what `main` added is Claude-only with no Pi path, and some of what this branch shares has drifted because `main` edited the Claude half.

An audit of the whole payload found thirteen gaps.
Four more turn out to be inherent to Pi's design and are recorded as non-gaps so nobody tries to close them.
The largest real gap is silent: a skill Claude Code restricts with `allowed-tools:` runs completely unconstrained under Pi, because Pi's loader never reads that key.

The intended outcome is that one payload, one tag and one policy drive both harnesses, and that where a difference is genuinely unbridgeable it is documented and pinned by a test rather than left to be rediscovered.

Everything below was read out of the repo or the installed Pi 0.84.2 under
`/opt/homebrew/opt/pi-coding-agent/libexec/lib/node_modules/@earendil-works/pi-coding-agent`.

## Verified findings

### Silent behavioural drift

| Gap | Evidence |
|---|---|
| 22 skills carry `allowed-tools:` that Pi ignores entirely, so a read-only skill gets an unrestricted shell | Pi's `dist/core/skills.js` reads only `name`, `description`, `disable-model-invocation`. 11 skills under `roles/ai/files/claude/skills/`, 11 under `plugins/product-team/skills/` |
| 8 agents pin `effort:` with no `thinking:`, so they run at Pi's session default | the 7 under `plugins/product-team/agents/` plus `plugins/security/agents/security-staff-engineer.md`, all linked into `.agents/agents/` by `claude_kit/pi.py:169` |
| The dual-key test cannot see any of them, because of a mis-scoped exemption | `test_pi_dialect.py:77` globs `*-staff-engineer.md` only, then `:78` drops any file carrying `tools:`. That exemption guards a *tools* collision and has no bearing on the *effort* pin, so it silently suppresses the check on 8 files |
| 9 skills also pin `effort:` with no `thinking:` | Not fixable by dual-keying: Pi reads no depth key for skills at all. Belongs to the `allowed-tools` gap |
| `cloud-readonly-gate.sh` is not bridged, though it is a `PreToolUse`/`Bash` hook on the event `guardrails.ts` already intercepts | `settings.json:251`; absent from `guardrails.ts` |

### Shared payload divergence

| Gap | Evidence |
|---|---|
| `rules/` is Claude-only, and two of its four files are agent-neutral | `roles/ai/tasks/main.yml:88` links only into `~/.claude/rules/` |
| `files/claude/AGENTS.md:5` points Pi at `rules/claude.md`, which Pi never receives | Pi gets `AGENTS.md`, no rules directory |
| Repo-root `AGENTS.md` (47 lines) has drifted from `CLAUDE.md` (79 lines), and Pi prefers `AGENTS.md` per directory | 1 `docs/internals` mention against 13 |
| The review policy reaches no Pi review flow, though `pi-review` is installed and reads a `REVIEW_GUIDELINES.md` | `files/pi/settings.json:34`; `loadProjectReviewGuidelines` in the package's `review.ts` |

### claude-kit lifecycle

| Gap | Evidence |
|---|---|
| `restore`'s early return exits before any Pi convergence, yet doctor's G19 remedy names `restore` as the fix | `restore.py:180` returns before `add.install_one` at `:213`; `checks.py:324` |
| `adopt` is Pi-blind although its target population is exactly G19's | `adopt.py:5`, `:29`; no `pi` import |
| No doctor check covers `.agents/agents/`, only `.agents/skills` | `checks.pi_skills_unreachable:301` is the sole Pi check |
| `restore` and `adopt` have zero Pi test coverage | no `pi` reference in `tests/test_restore.py` or `test_adopt.py` |

### Trust and reporting

| Gap | Evidence |
|---|---|
| `.agents/skills` is itself a Pi trust trigger, so claude-kit's own work makes Pi prompt | `trust-manager.js:158`: any `<dir>/.agents/skills` that exists and is not `~/.agents/skills` requires trust |
| Pi's trust store does not exist on this machine | no `~/.pi/agent/trust.json`; `defaultProjectTrust` defaults to `ask`. Claude has 14 entries, 7 trusted |
| The role installs herdr's Claude integration but not its Pi one | `roles/ai/tasks/main.yml:117` gates on `'claude: current'`; `herdr integration status` reports a `pi` integration, live at v8, installed by hand |

### The live machine is worse off than the branch implies

None of the branch's Pi work has ever run, and one pre-existing bug is why.

- `~/.pi/agent/settings.json` still points into the **old** `~/Developer/dotfiles` checkout, whose copy has a **trailing comma** and is invalid JSON (line 23).
  Pi therefore loads no settings at all: no `packages`, no model pins, no theme.
- Because `packages` never loaded, **`@tintinweb/pi-subagents` was never installed**.
  `~/.pi/agent/npm/node_modules/@tintinweb/` is empty and Pi's own `package.json` lists only `pi-cc-patch` and `pi-cursor-sdk`.
  The name is correct (`@tintinweb/pi-subagents@0.17.0` exists), so nothing needs renaming: the whole agents half is inert rather than wrong.
- `~/.pi/agent/SYSTEM.md` is still a live symlink into the old checkout, the exact case the removal task at `main.yml:230` exists to clear.
- This branch's `settings.json` is valid and `test_pi_dialect.py:186` parses it, so the bug cannot recur here.
  Applying the role is what repairs the machine, which makes `make run-role ROLE=ai` a required verification step.

### Three constraints that shape the design

**Pi has no "ask" tier in a `tool_call` handler.** It returns only `{ block, reason?, terminate? }`. Partly revised in passing: `pi-sandbox` does prompt, from its own handler through `ctx.ui.custom`, so an interactive tier is possible for an extension that wants one. `guardrails.ts` does not take it, because a prompt that cannot be shown must still fail open and that is a larger change than this pass wanted.
`cloud-readonly-gate.sh` is three-tiered, and its broadest tier is `permissionDecision: "ask"`, which has no counterpart.

**The tool vocabularies differ, so enforcement must be inverted.** Pi's built-ins are exactly seven (`bash`, `edit`, `find`, `grep`, `ls`, `read`, `write`), read from `dist/core/tools/`.
Mapping Claude to Pi produces dead entries; the question at a call is always "this Pi tool is being invoked, does the active skill permit it?", so the map need only be total over those seven.

**Pi and Claude key trust differently, and it cannot be unified.** Pi's store is a flat `{absolute_path: boolean}` map with ancestor inheritance, written under `proper-lockfile`, keyed on `realpathSync(cwd)`.
Claude keys on the git repo root (the main checkout for a worktree) and deliberately does *not* realpath.
So the same project yields different keys in the two stores, by design on both sides.

### Non-gaps, recorded so they are not "fixed"

- **MCP servers.** Neither harness has any; Pi ships no MCP by design.
- **Status line.** Pi's footer already carries model, provider, thinking level, context percentage, cache hit rate, cwd with branch and cost. `velocity.ts` is deliberately the one segment Claude has and Pi lacks.
- ~~**Permissions and sandbox.**~~ **Recorded here as a non-gap and it was wrong.** Three real pi-coding-agent extensions exist, and the correction is written up in `docs/internals/pi-harness.md`. `pi-sandbox` confines bash at the OS level through a fork of Anthropic's own `sandbox-runtime` and applies allow/deny lists to read, write and edit, so Pi does have a permission model; it is not Claude's, so `files/pi/sandbox.json` derives one from the `sandbox` block plus the path half of the `permissions` block. `pi-sandbox` was chosen over `pi-permissions` on adoption (about 1096 weekly downloads against 23), even though the latter speaks Claude's specifier syntax exactly. `guardrails.ts` itself remains intent friction rather than a security boundary; the confinement is what changed.
- **Plan mode.** `plan-date-stamp.sh` has nothing to bridge to.

## Implementation

Ordered so nothing depends on a later step.

### 1. Close the dual-key hole

Fix the test first and let it name the files.

- `lib/python/tests/test_pi_dialect.py`: rebase `dual_keyed()` on the real invariant, **any agent file pinning `effort:` must pin an equal `thinking:`**, over `agent_files()` rather than the seat glob.
  Drop the `tools:` filter from that predicate and keep a separate, explicitly named exemption for the un-bridged `tools:` allowlist, so the advisor's Claude-only tool names stay documented without suppressing the depth check.
  Replace the `>= 15` floor with a count that cannot pass vacuously.
- Add `thinking:` equal to the existing `effort:` on the 8 agents named above.
- Fix `skills/agent-writer/references/seat-agent-anatomy.md`, the template that teaches the pins and itself shows `effort:` without `thinking:`, or the next seat repeats the gap.

### 2. Root AGENTS.md becomes a symlink

- Replace repo-root `AGENTS.md` with a committed **relative** symlink to `CLAUDE.md`.
- `test_suites.py` scopes its committed-symlink assertions to the `dotkit` links, so nothing breaks, but its docstring calling those "the first committed symlinks in this repo" is stale (12 exist under `.claude/skills/`) and should stop claiming exclusivity. Same claim in `docs/internals/testing-layout.md`.

### 3. The two neutral rules reach Pi by moving into AGENTS.md

Measured first, counting only what this repo controls, at 4 bytes per token.

| Layer | Today | After |
|---|---|---|
| Claude: `AGENTS.md` + `rules/*.md` | ~3776 tok | ~3776 tok (same content, different file) |
| Pi: `AGENTS.md` + `APPEND_SYSTEM.md` | ~1441 tok | ~2849 tok |

Pi goes from 38% to 75% of Claude's layer and still carries less, while Claude's total does not move.
Neutrality was checked, not assumed: `skill-precedence.md` (~797 tok) has **zero** Claude-specific references; `context-hygiene.md` (~611 tok) has five (`Explore`, `general-purpose`, `subagent`, `/clear`).

**Move both files' content into `roles/ai/files/claude/AGENTS.md` and delete them from `rules/`.**
That file is already symlinked to both `~/.claude/CLAUDE.md` and `~/.pi/agent/AGENTS.md`, so both harnesses get it with no new task, no generated file and no second copy to drift.
`rules/` is then left holding only genuinely Claude-only policy, `claude.md` and `code-review.md`.

For the five Claude-specific terms, follow the convention `AGENTS.md` already uses for the `commit` / `/commit` / `/skill:commit` split: name the concept and parenthesise the harness-specific spelling.
Also fix `AGENTS.md:5`, which points Pi at `rules/claude.md`.

Rejected: concatenating into `APPEND_SYSTEM.md` needs `ansible.builtin.assemble` and gives up live-edit; converting rules to on-demand skills changes Claude from always-on to invoked, which is the opposite of what a rule is.

`main`'s `afc9e42` cites cutting 11.9k to 7.5k, which counts a wider surface than the table above and is not comparable to it.

### 4. Enforce allowed-tools in guardrails.ts

Build on what is already there: `activeSkills(ctx)` reads `<skill name="...">` from user messages, and `blockResult` shapes the refusal.

- **Widen skill resolution.** `activeSkills` is narrowed to `GATED_SKILLS`, and a test pins that set against `git-skill-gate.sh`. Add a second resolver rather than changing it, so the existing gate stays byte-identical.
- **Data source: parse on demand from the tag's `location`.** Pi's expansion carries `location`, so the SKILL.md path is in the session, needing no manifest and going stale never. Cache per session in a `Map` keyed by location.
- **Composition: union of the active skills' allowlists**, and a skill with no `allowed-tools` imposes no restriction. This mirrors Claude, where an unrestricted skill does not restrict, and avoids an intersection blocking a tool a legitimately active skill needs.
- **Map only the seven Pi names:** `read`→`Read`, `write`→`Write`, `edit`→`Edit`, `bash`→`Bash`, `grep`→`Grep`, and `find`/`ls`→`Glob` (a read-only listing is no escalation over a glob).
- **No active skill means no enforcement**, or this becomes a global allowlist Pi never had.
- **Unknown tool names allow, and the reason is recorded.** Extension tools (including whatever `pi-subagents` registers for dispatch) are not ours to name, and denying by default would break a skill that legitimately dispatches. This is the honest limit of the mechanism, and it is why the file keeps calling itself intent friction.
- Fail open on every error, as the rest of the file does.
- Extend `lib/python/tests/test_pi_guardrails.py`: the mapping is total over the seven Pi tools, the union rule, the no-skill case, the unknown-tool default, and the existing "no hook logic reimplemented in TypeScript" fingerprints still hold.

### 5. Bridge cloud-readonly-gate, with ask mapping to block

The hook reads only `tool_name` (must be `Bash`) and `tool_input.command`, which is exactly the payload `guardrails.ts` already sends, so the spawn itself is trivial.

The decision is the middle tier: **`ask` maps to `block`**, with the reason naming the command so the user can run it themselves.
Pi is then stricter than Claude on this one gate, which is the defensible direction, since the four cloud CLIs already run outside Claude's sandbox and Pi has no confirmation step to fall back to.
State the residual plainly: the gate documents itself as fail-closed for cloud commands while `guardrails.ts` must fail open, so a machine where the hook cannot run has cloud commands ungated in Pi.

### 6. Leave the git-skill-gate matcher alone, and say why

Checked rather than assumed, and it reverses the obvious fix.
`main()` blocks `--no-verify` with exit 2 **before** computing which subcommands are gated, so that block applies to any command; everything else exits 0 when `gated` is empty, so non-git commands self-guard.

Claude's three `if` matchers therefore catch `--no-verify` only inside `git`, `gh` and `glab` calls, while Pi catches it anywhere.
Narrowing Pi would **remove** protection. No code change: record it in `docs/internals/pi-harness.md`, and note the one real cost, a `python3` spawn per bash tool call, as a latency item to measure.

### 7. claude-kit lifecycle

- **`restore`**: converge Pi before the early return at `restore.py:180`, so the state G19 fires on is actually fixed by the command G19's remedy names. Leave the `--dry-run` path alone, which correctly converges nothing.
- **`adopt`**: converge too. Its docstring says it writes `claude-kit.json` and nothing else, so widen the docstring with the reason rather than letting the behaviour contradict it. Its stated population is precisely the projects missing the link.
- **New doctor check** for `.agents/agents/`, the per-file agent links `converge_agents` maintains, which today are reported only at the moment `add` or `remove` runs. Mirror G19: `NOTE` severity, same message shape, silent when the project has no plugins installed.
- **Tests**: add Pi assertions to `tests/test_restore.py` and `tests/test_adopt.py` (both currently have none), and extend Group P in `tests/test_pi.py` for the new check.

### 8. Trust and herdr

- **herdr**: add a second install task gated on `'pi: current' not in herdr_integration.stdout`, reusing the existing single `herdr integration status` register. The extensions task adds per-file links without pruning, so herdr's real file in that directory is not at risk. Confirmed, no change needed there.
- **Pi trust**: `claude-kit trust` should **read and report** Pi's store alongside Claude's, and **write it only behind an explicit flag**.
  Reading is free and answers the question the user actually has.
  Writing is deliberately narrow: the file is lock-protected by `proper-lockfile`, so refuse and print the alternative when a lock is held rather than forcing a write into another tool's file, exactly as `remove` refuses to leave its project.
  Key the entry on `realpath(project)`, never on Claude's git-root key.
  Do **not** set `defaultProjectTrust: "always"`: Pi's trust gates executing project extensions, and blanket-trusting every directory to silence a prompt our own tooling causes is the wrong trade.

### 9. REVIEW_GUIDELINES.md for pi-review

Narrower than it first looked.
The recorded decision in `docs/internals/code-review-policy.md:32` is about **`REVIEW.md`**, the filename hosted Code Review reads, and it even anticipates writing one when that consumer becomes reachable.
`REVIEW_GUIDELINES.md` is a different filename for a different consumer, so this extends the doc rather than superseding a decision, and `test_review_policy.py`'s assertion that no `REVIEW.md` reaches `~/.claude` is untouched.

- `pi-review` only reads the file from a directory that also contains a `.pi` **directory**, then stops walking. This repo has no `.pi/`, so one must exist for the file to be read at all.
- Add `.pi/` and a `REVIEW_GUIDELINES.md` symlink to `rules/code-review.md` at this repo's root: one source, zero drift.
- Do **not** teach `claude-kit` to create root-level files in every project. Document the two-file recipe in `docs/internals/code-review-policy.md` instead, and let each repo opt in.
- Accept that a few Claude-only sentences (the `/code-review` effort levels) ride along. `pi-review`'s own rubric defers to project guidelines, and one source beats a trimmed copy that drifts.

### 10. Docs and housekeeping

- `docs/internals/pi-harness.md`: the enforcement mechanism and its unknown-tool limit, the cloud gate's ask-to-block mapping, the deliberate git-gate breadth, the trust key divergence, and replace the "one gap remains" line now that the review gap is closed.
- `roles/ai/README.md` and the deep-reference table in `CLAUDE.md` for the new check and the herdr task.
- Drop `lastChangelogVersion` from `files/pi/settings.json`: it is Pi-owned churn state (tracked at 0.84.1, installed 0.84.2) that this repo gains nothing from pinning. Update the 0.84.1 citation in `claude_kit/pi.py:11`.

## Out of scope, flagged

The 12 committed symlinks under `.claude/skills/` hold **absolute** paths into the other checkout (`~/Developer/dotfiles/...`).
They resolve only because that checkout exists and would dangle on any clone, which contradicts the documented design that project symlinks are never committed.
It predates this branch, but it is the directory `.agents/skills` points at, so Pi's project skills here resolve into the wrong tree.
Worth its own change.

## Verification

`make test` is the only unattended target and must stay green (1584 tests today).
`make lint` and `make syntax` need the vault password and are run by hand.

Because none of the Pi work has ever executed here, tests are not sufficient:

1. `make check-role ROLE=ai` to see the diff before applying.
2. `make run-role ROLE=ai`, which repairs the machine: repoints `settings.json` at valid JSON, clears the superseded `SYSTEM.md` link, repoints `skills` at `~/.claude/skills`.
3. `pi config` starts without a `SyntaxError`, and `~/.pi/agent/npm/package.json` gains `@tintinweb/pi-subagents` once `packages` is readable.
4. An agent from `~/.pi/agent/agents` is listed in a Pi session, and one of the 8 newly dual-keyed agents runs at its pinned depth rather than the session default.
5. `herdr integration status` reports `pi: current` with no hand install.
6. In a Pi session, a skill carrying `allowed-tools:` refuses a tool outside its allowlist; a tool call with no active skill is untouched; and a deliberately broken hook path still lets work proceed.
7. A read-only `aws describe-*` proceeds; a mutating one is refused with the command named.
8. `claude-kit doctor` in a project whose `.agents/skills` was deleted by hand reports G19, and `claude-kit restore` now actually fixes it.
9. `/review` in a Pi session reflects the `blocker` / `important` / `nit` / `pre-existing` vocabulary.
