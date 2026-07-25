# Claude Code setup review: task backlog

Date: 2026-07-25.
Source: `/cc-review` run (cc-staff-reviewer) against user scope `~/.claude/` (real files at `roles/ai/files/claude/`) and project scope `dotfiles/.claude/`, on Claude Code 2.1.220.
Evidence base: 150 `/insights` facet files (`~/.claude/usage-data/facets/`) plus the 2026-07-25 report, covering 538 sessions and ~394 commits since 2026-05-11.
Status: nothing below has been applied. Each task is self-contained so it can be picked up in its own session.

## How to use this file

Work one task per session. Each carries the files to touch, the change, and the evidence that justifies it, so a fresh session needs no other context.
Tick the checkbox and add the commit sha when done. Delete the task once it has landed on `main`.
Anything under [Not worth doing](#not-worth-doing) was considered and rejected with reasons: do not re-litigate it without new evidence.

## Ordering constraint

**T1 must land before T5.** A global scope rule in `CLAUDE.md` cannot win against a project memory that tells Claude the opposite in a 54-session repo. Everything else is independent.

## P0

### T1. Fix the push-path memory in addingwell-front

- [x] Applied - no-op, 2026-07-25. The targets do not exist: there is no `~/.claude/projects/-Users-jmanuelrosa-Developer-work-addingwell-front/` project directory (only the `front-e2e`, `front-sentry`, ... worktree slugs), no `reference_pr_push_path.md` / `feedback_no_autonomous_push.md` / `feedback_commit_via_skill.md` anywhere under `~/.claude/projects/*/memory/`, and the phrase "pre-emptively hand off" is in no memory file. The addingwell `CLAUDE.md` files carry no push-handoff guidance either. The only surviving push memory, `-Users-jmanuelrosa-Developer-personal-brick/memory/commit-pr-handoff.md`, is already correct (skills are `disable-model-invocation`, hand off to the user, never attempt raw `git push`). T5's blocker is lifted.
- **Files:** `~/.claude/projects/-Users-jmanuelrosa-Developer-work-addingwell-front/memory/reference_pr_push_path.md`, `~/.claude/projects/-Users-jmanuelrosa-Developer-work-addingwell-front/memory/feedback_no_autonomous_push.md`
- **Scope:** user (project memory, outside the dotfiles repo)
- **Effort:** S

The memory currently says: *"just run `/pr` and let it push. Don't pre-emptively hand off pushing to the user (that supersedes the old 'Claude can't push' guidance here)."*
That instructs an impossible action. `roles/ai/files/claude/skills/pr/SKILL.md:6` carries `disable-model-invocation: true`, so Claude cannot invoke `/pr`, and `hooks/git-skill-gate.sh:50` gates `git push` behind skill attribution in the transcript.
The fallback behaviour is to attempt the push directly, get blocked, and flail. Three facets record exactly that, including one where the MR shipped without the latest local commit (`b3ca809`).
It also contradicts two sibling memories in the same directory (`feedback_no_autonomous_push.md`, `feedback_commit_via_skill.md`), and with three conflicting memories the resolution is arbitrary.

Change: rewrite `reference_pr_push_path.md` to keep the literal push command as reference material for the skill, drop the "don't hand off" claim, and state that when the branch is ready Claude stops and tells the user to run `/pr`.
Then delete `feedback_no_autonomous_push.md`, which the corrected version subsumes.

### T2. Cap nested subagent spawn depth

- [ ] Applied
- **Files:** `roles/ai/files/claude/settings.json` (`env` block, around line 4)
- **Scope:** user
- **Effort:** S

Changelog 2.1.219 (2026-07-24) raised the default nested-subagent depth from 1 to 3. The `env` block has no cap, so the new default is live.
Agent fan-out is the largest friction class in the facets (29 `user_rejected_action` plus 22 `wrong_approach`), with fan-out named directly in at least one transcript.
Three surfaces fan out today: `research` (has `Agent` in allowed-tools, `model: opus`), `1-research` (three parallel researchers), and `feature-team` (dispatches to every installed seat, which is 13 in `addingwell`). A 13-way dispatch that can now nest two levels deeper on opus is a spend multiplier, and spend limits already cut investigations short.

Change: add `"CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1"` to the `env` block, restoring the depth the fleet was designed against.

## P1

### T3. Convert the Product Team pipeline into a plugin

- [ ] Applied
- **Files:** new `roles/ai/files/claude/plugins/product-team/`, plus `skill-registry.json` and `agent-registry.json` row removals, plus `CLAUDE.md` if the seat-plugin section needs a companion note
- **Scope:** user
- **Effort:** L

All 8 numbered stage skills plus `setup-strategy`, `idea-refine`, `product-lead`, and 5 product agents (`competitive-researcher`, `user-evidence-researcher`, `market-sizer`, `strategy-checker`, `pm-red-team`) carry `groups: ["global"]`, so they load in every session in every repo.
Measured cost: the 10 stage-and-setup skills are 5,708 of 13,250 bytes (43%) of global skill frontmatter, and the 5 product agents are 1,831 of 4,003 bytes (46%) of global agent frontmatter.
No facet shows the pipeline being used. The top-40 goal categories contain no product, PRD, or strategy entry (`project_management` = 3), and the 18 pipeline sessions were spent building it. The memory `project_product_team` still records the E2E dogfood as pending, 18 days on.
The pipeline is also inherently per-repo: it writes `docs/initiatives/`, needs `setup-strategy` scaffolding, and reads `STATUS.md` from the current repo. Globally loaded and locally applicable is backwards.

Change: package it as a plugin exactly like the staff-engineer seats (`.claude-plugin/plugin.json`, `agents/`, `skills/`), per the seat-plugin convention in `CLAUDE.md`. Drop the `global` tag from the 13 entries and remove their registry rows, since seat plugins carry no registry rows.
Keep `product-lead` global: it is the hub that reads `STATUS.md` and names the next command, so it should stay discoverable everywhere and is the correct entry point for `claude-agent add product-team`.
Side benefit: the registries express agent-to-skill dependencies but not skill-to-agent, so `1-research` currently cannot declare that it needs `competitive-researcher`. Bundling them dissolves that gap.
Net effect: global routing surface drops ~44%, and this is a deletion rather than an addition.

### T4. Stop four dependency-only skills from auto-firing

- [ ] Applied
- **Files:** `roles/ai/files/claude/skills/{grilling,idea-refine,domain-modeling,planning-and-task-breakdown}/SKILL.md`
- **Scope:** user
- **Effort:** S

Seven of 30 global skills lack `disable-model-invocation`. Four of those are `dependency_only` or agent-invoked, so auto-firing is pure downside:

| Skill | Auto-trigger | Explicit caller |
|---|---|---|
| `grilling` | "stress-test their thinking, or uses any 'grill' trigger phrases" | `/grill-me`, `/grill-with-docs` (both manual) |
| `idea-refine` | "Triggers on 'ideate', 'refine this idea', 'stress-test my plan'" | `setup-strategy`, `/0-refine-idea` |
| `domain-modeling` | "record an architectural decision" | `architect` agent (declared dependency) |
| `planning-and-task-breakdown` | "when a task feels too large to start" | `architect` agent (declared dependency) |

`grilling` and `idea-refine` collide head-on: both auto-fire on "stress-test my plan" while the real entry point is `/grill-me`.
`domain-modeling` auto-firing on "record an architectural decision" contradicts the recorded decision in `project_adr_convention_owned_locally`, which puts ADR authority in `product-lead` and `architect`, never in vendored `domain-modeling`.
`planning-and-task-breakdown` firing on "a task feels too large to start" matches ordinary work.

Change: add `disable-model-invocation: true` to those four `SKILL.md` files.
Leave `humanizer`, `skill-writer`, and `documentation-and-adrs` alone: their triggers are wanted, and `documentation-and-adrs` is not the ADR-convention authority the memory is about.

### T5. Add a scope-control section to the global CLAUDE.md

- [ ] Applied
- **Files:** `roles/ai/files/claude/CLAUDE.md`
- **Scope:** user
- **Effort:** S
- **Blocked by:** T1

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
