# Claude Code setup review: task backlog

Date: 2026-07-25.
Source: `/cc-review` run (cc-staff-reviewer) against user scope `~/.claude/` (real files at `roles/ai/files/claude/`) and project scope `dotfiles/.claude/`, on Claude Code 2.1.220.
Evidence base: 150 `/insights` facet files (`~/.claude/usage-data/facets/`) plus the 2026-07-25 report, covering 538 sessions and ~394 commits since 2026-05-11.
Status: T1 (applied as a no-op, since its target memory files do not exist on disk) and T3 have landed on `main` and were deleted per the rule below; T2 and T4 were rejected and are recorded under [Not worth doing](#not-worth-doing). T5 onward are open and none of them block each other. Each task is self-contained so it can be picked up in its own session.

## How to use this file

Work one task per session. Each carries the files to touch, the change, and the evidence that justifies it, so a fresh session needs no other context.
Tick the checkbox and add the commit sha when done. Delete the task once it has landed on `main`.
Anything under [Not worth doing](#not-worth-doing) was considered and rejected with reasons: do not re-litigate it without new evidence.

## P1

### T5. Add a scope-control section to the global CLAUDE.md

- [ ] Applied
- **Files:** `roles/ai/files/claude/CLAUDE.md`
- **Scope:** user
- **Effort:** S

Scope over-reach is the dominant friction class at 51 events (29 `user_rejected_action` plus 22 `wrong_approach`), more than double the next class, and `/insights` names it the defining pattern.
The correction is already written down, in `~/.claude/projects/-Users-jmanuelrosa-Developer/memory/feedback_respect_scope.md`, but that memory loads only for the 6 sessions whose cwd maps to `-Users-jmanuelrosa-Developer`. It does not load for dotfiles (230), addingwell-front (54), or addingwell (50).
This belongs in `CLAUDE.md` rather than a skill or a hook: the model must weigh it every turn, and "did you expand scope" is not deterministically checkable.

Change: add a `## Scope control` section, four lines, grounded in the actual facet examples:

- A read-only request (discovery, investigation, feasibility, analysis) produces a findings document with citations, never an implementation plan and never edits.
- Before fanning out agents, or changing more than three files, state the plan in one sentence and wait.
- Do not delete or rewrite documentation samples, defaults, or adjacent code that the request did not name.
- When a stated constraint conflicts with a technical reality, name the tension and ask which gives. Do not resolve it by adding a component.

This is the only `CLAUDE.md` addition the review recommends. It replaces nothing, and the file is 41 lines so there is room.

### T6. Re-check the branch immediately before committing

- [ ] Applied
- **Files:** `roles/ai/files/claude/skills/commit/scripts/apply.py` (around lines 82-92), `roles/ai/files/claude/skills/commit/SKILL.md` (steps at lines 33-42) if the plan JSON needs a new field
- **Scope:** user
- **Effort:** S

`SKILL.md:33-40` confirms the branch at step 2, `:42` handles staging, and `apply.py:82-92` stages and commits. Nothing between step 2 and the commit re-reads `git branch --show-current`.
A facet records the consequence: the commit landed on the wrong branch when HEAD moved between confirmation and commit, needing a corrective fast-forward.
`version_control` is the largest goal category (82 sessions), so this skill carries more traffic than anything else in the setup.

Change: record the confirmed branch in the plan JSON and have `apply.py` fail before the first `git add` if `git branch --show-current` no longer matches. A deterministic check belongs in the script that already owns the operation, not in a new hook and not in a `CLAUDE.md` line.
The companion friction (a first commit sweeping in pre-staged files) needs no change: `SKILL.md:42` already says the candidate is the staged set and never to auto-stage. That was a deviation from the skill, not a defect in it.

## P2

### T7. Close the registry drift

- [ ] Applied
- **Files:** `roles/ai/files/claude/skill-registry.json`, `roles/ai/files/claude/skills/agent-nestjs-skills/`, `roles/ai/files/claude/skills/playwright-best-practices-skill/`
- **Scope:** user
- **Effort:** S

Both skills exist on disk with no `skill-registry.json` row, so `claude-skill list`, `update`, `outdated`, and the Television picker cannot see them, and neither is ever synced from upstream.
`playwright-best-practices-skill` is installed in four `addingwell/front*` worktrees, so it is load-bearing and silently unmaintained.
`agent-nestjs-skills` is installed in zero projects and is covered by `nodejs-backend-patterns` plus `node`.

Change: register `playwright-best-practices-skill` with `groups: ["quality","qa","playwright","testing"]`, and delete `agent-nestjs-skills`.

### T8. Replace Write(path) permission rules in /commit

- [ ] Applied
- **Files:** `roles/ai/files/claude/skills/commit/SKILL.md` (allowed-tools), and the memory `project_permission_rule_anchoring`
- **Scope:** user
- **Effort:** S

Changelog 2.1.210 added a startup warning for `Write(path)`, `NotebookEdit(path)`, and `Glob(path)` permission rules, directing use of `Edit` or `Read` instead. The `/commit` allowed-tools carries `Write(//tmp/claude/**)` and `Write(//private/tmp/claude/**)`.

Change: convert both to `Edit(...)`. The `//` anchoring stays correct, only the tool name changes.
Also update the example line in the `project_permission_rule_anchoring` memory, which was verified on 2.1.210, the exact release that added the warning.

### T9. settings.json hygiene

- [ ] Applied
- **Files:** `roles/ai/files/claude/settings.json` (line 344, and the `mcp__supabase` / `mcp__Supabase` deny entries near lines 179-182)
- **Scope:** user
- **Effort:** S

`DISABLE_AUTOUPDATER=1` at `settings.json:8` makes `autoUpdatesChannel: "stable"` at line 344 inert. Claude is Homebrew-managed, so the autoupdater is correctly off.
The `mcp__supabase` and `mcp__Supabase` deny entries guard a server configured nowhere.

Change: delete line 344 and the two `supabase` deny entries.
Separately, `brew list` shows both the `claude` and `claude-code@latest` casks installed. Pick one in the `brew` role.

### T10. Drop the redundant notion MCP server

- [ ] Applied
- **Files:** `~/.claude.json` (the `work/addingwell/front` project block)
- **Scope:** user (outside the dotfiles repo)
- **Effort:** S

`settings.json:179-182` denies `mcp__notion` and `mcp__Notion`, and the global `CLAUDE.md` mandates the `ntn` CLI with "never MCP for them". `~/.claude.json` still configures a `notion` MCP server for `work/addingwell/front`, which costs a connection attempt each session and can never be used.

Change: remove the server config. Keep the deny entries as the tripwire.

### T11. Fix the em dash in skill-recap.sh

- [ ] Applied
- **Files:** `roles/ai/files/claude/hooks/skill-recap.sh:7`
- **Scope:** user
- **Effort:** S

The docstring on line 7 separates the filename from "Stop hook for Claude Code" with a literal U+2014, so the house-style tooling violates house style. The em-dash gate is delta-based, so replacing that one character will not trip it.

## Adoption opportunities

These are separate from the fixes above: features shipped in the last six weeks that fit the observed usage. The first needs a config change, the other two are habits.

### T12. Try sandbox.filesystem.disabled

- [ ] Applied
- **Files:** `roles/ai/files/claude/settings.json` (`sandbox` block)
- **Scope:** user
- **Effort:** S

Shipped in 2.1.216: skips filesystem isolation while keeping network egress control.
The worst single friction event in the period was a write-deny on `settings.json` breaking a git checkout mid-branch-switch, leaving a half-rewound tree. That is structural rather than bad luck: the dotfiles repo (230 sessions, the top project) contains `roles/ai/files/claude/settings.json`, which the sandbox filesystem layer protects from writes, so any branch switch touching it can corrupt the working tree. The same layer produced the blocked unlink during a fast-forward, the lockfile-write denials, and the `.env` read blocks, roughly 40 events in total.
The blunt version has already been reached for once: `work/addingwell/front-sentry/.claude/settings.local.json` sets `sandbox.enabled: false`. This is the surgical version.

Change: add `"filesystem": { "disabled": true }` inside the `sandbox` block, retaining `network`.
The trade: write-confinement to `.` and `$TMPDIR` is lost, along with the `sandbox.filesystem.denyRead` list. The 66-entry `permissions.deny` is a separate layer and already covers every path in `denyRead` (`~/.ssh`, `~/.gnupg`, `~/.aws`, `~/.npmrc`, `~/.netrc`, `~/.config/gcloud`, and `~/.terraform.d/**` covers the tfrc file), so credential protection survives, network egress control survives, and `cloud-readonly-gate.sh` is unaffected.
Revert by deleting the key.

### T13. Use /fork and /subtask on long investigations

- [ ] Adopted
- **Scope:** habit, no config
- **Effort:** S

2.1.212 changed `/fork` to copy the conversation into a new background session, and replaced the in-session subagent with `/subtask`.
Friction class 3 is long investigations dying to spend limits or interruption with no written deliverable: 14 facets came back `partially_achieved` and 11 `unclear_from_transcript`.
Forking the expensive branch into a background session keeps the main thread responsive and survives an interrupt in the parent, which fits the observed overlapping-session pattern.

### T14. Stack slash-skill invocations

- [ ] Adopted
- **Scope:** habit, no config
- **Effort:** S

2.1.199 allows stacked invocations such as `/skill-a /skill-b do XYZ`, loading up to 5 leading skills.
22 of 30 global skills carry `disable-model-invocation`, so nearly everything is driven by name, and the product pipeline is 8 sequential stages. `/4-tech-shape /grill-me` in one prompt replaces two round-trips.

## Not worth doing

Considered and rejected. Do not redo without new evidence.

- **`.claude/rules/` at either scope.** Global `CLAUDE.md` is 41 lines and the project one is ~180. A rule file without `paths` frontmatter loads at launch at the same priority and token cost as `CLAUDE.md`, so an unconditional split saves nothing, and there is no path-scoping win: dotfiles is one Ansible convention set and the global standards are language-agnostic.
- **Project-scope artifacts in dotfiles**, despite it being the top repo at 230 sessions. The global set (`agent-writer`, `skill-writer`, `agent-audit`, `cc-review`, `skill-scout`, `cc-staff-reviewer`) is exactly the authoring loop this repo needs, and this repo is where that set is authored. A project copy would shadow the thing it copies.
- **Touching the 14 seat plugins.** They look inert (absent from `enabledPlugins` and `installed_plugins.json`) but they are project-installed by design via `claude-agent add`, and 13 are live in `work/addingwell/` and `3bitslost/pickleballontime/`.
- **Touching the em-dash gate.** One rejection in 150 sessions is a correctly tuned hook, not friction.
- **`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1`** (was T2, rejected 2026-07-25 after checking it against the 2.1.220 binary and the official changelog). `=1` disables *nesting*, not subagents, and all three fan-out surfaces dispatch from the main conversation at depth 1: `research`, `1-research`, and `feature-team`, whose own text says "You (the main conversation) are the team lead: you dispatch". The 13-way seat dispatch the task worried about is breadth, not depth, so the cap does not touch it. Nothing in the fleet exercises depth 2 either: `architect` already declares `disallowedTools: Agent`, the registry agents carry narrow `tools:` lists without `Agent`, and no seat prompt mentions spawning or delegating. The task's evidence is also T5's event pool re-counted (the same 29 `user_rejected_action` plus 22 `wrong_approach`), with exactly one transcript naming fan-out. The one measurable effect would be a context regression: hitting the cap prints "Subagent nesting limit reached (depth N). Complete this task directly using your tools instead of spawning another agent.", so a subagent that would offload a wide read sweep to `Explore` reads inline in its own window instead. Breadth, the actual spend driver, is governed by `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` (default 20) and `CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION`. If a bound is ever wanted, the surgical version is `disallowedTools: Agent` on the seats that should never delegate, matching `architect`, not a global env kill switch.
- **`disable-model-invocation: true` on `grilling`, `idea-refine`, `domain-modeling`, `planning-and-task-breakdown`** (was T4, rejected 2026-07-25). The diagnosis is fine but the change is not applicable: all four are vendored, two from `mattpocock/skills` and two from `addyosmani/agent-skills`, and `_claude_skill_update` syncs with `rm -rf "$dst"` followed by `rsync`, a full replace, so the next `claude-skill update` silently reverts the edit. Worse, `claude-skill outdated` decides "behind" by running `diff -rq` between upstream and the local copy, so a local frontmatter line would make all four report behind permanently, degrading the one signal that says when upstream actually moved. There is no way to set it from outside the file either: 2.1.220 reads `disable-model-invocation` only from `SKILL.md` frontmatter, with no `disabledSkills` or `skillSettings` key anywhere in the binary. The task's framing is also off. Recomputing the effective global set the way `roles/ai/tasks/main.yml` does gives 19 skills, not 30: `grilling`, `domain-modeling`, and `planning-and-task-breakdown` are in it (pulled in as declared dependencies of `grill-me`, `grill-with-docs`, and `architect`), but `idea-refine` is not, and after T3 it is a project-scoped `product-team` plugin dependency rather than a global skill. The durable fix was considered and dropped: a `frontmatter_overrides` field on registry entries, applied after rsync, with the diff run against an overlaid copy of upstream so `outdated` stays honest. That adds an override layer to shared sync tooling to serve four entries, and 51 of the 54 vendored skills lack the flag precisely because auto-firing is the point for a tech skill. If the `grilling` / `idea-refine` collision ever actually bites, upstream it: `grilling` and `domain-modeling` are the only two vendored skills carrying `dependency_only: true`, which is exactly the argument a PR to those repos would make. Do not fork a vendored skill locally.
- **`sandbox.network.strictAllowlist`** (2.1.219). It denies non-allowlisted hosts without prompting, which would convert ~40 sandbox prompts into hard failures.
- **`Notification` hooks** (2.1.198). They add nothing over the existing `agentPushNotifEnabled` plus `preferredNotifChannel: ghostty`.
- **A git dry-run hook** (suggested by `/insights`). `git-skill-gate.sh`, `pre-commit-verify.sh`, and `/commit`'s own staging gate already cover it, and both real failures live inside `/commit`'s logic. T6 fixes one in three lines; a hook would be a second enforcement layer for a problem the first layer should catch.
- **An agent-upgrade slash command** (suggested by `/insights`). `agent-writer` with its `references/`, plus `agent-audit` and `cc-staff-reviewer`, already are that pipeline, and all are global.
- **An agent-authoring section in `CLAUDE.md`** (suggested by `/insights`). It would duplicate `agent-writer`'s `SKILL.md` into always-loaded context. The procedure belongs in the skill.

## What the review found healthy

Recorded so a future session does not "improve" it.

- The four-layer git enforcement: `git-skill-gate.sh`, `pre-commit-verify.sh`, `disable-model-invocation` on `/commit` and `/pr`, and the `CLAUDE.md` git section. All four agree, with enforcement on the hook and advice in `CLAUDE.md`.
- `cloud-readonly-gate.sh`: three-tier block/ask/allow, fail-closed, with the reason `exit 2` overrides a `Bash(aws:*)` allow written into the docstring. Called the best artifact in the setup.
- `em-dash-gate.sh`: delta-based so existing files stay editable, fail-open on malformed input, dash chars `\u`-escaped so the hook can edit itself.
- Cost posture: `/commit` and `/pr` carry `model: sonnet` against a global `opus` default, so the largest goal category runs cheap.
- `groups: ["global"]` as the single source of truth, derived in Ansible with `stat` plus `assert` failing the playbook on a registry typo (`roles/ai/tasks/main.yml:200-218`).
- `skill-recap.sh` emitting `systemMessage` so the recap costs zero model context.
