# Subagent structure: registry+symlinks vs Claude Code plugins

Date: 2026-07-13.
Question: should the locally-authored subagents (`roles/ai/files/claude/agents/`) and their coupled skills be restructured as Claude Code plugins (one plugin per subagent, bundling the agent + its required skills), instead of the current registry + fish-tooling + Ansible-symlink model? Motivation: an agent should never ship without its skills, nor the skills without the agent, and the current wiring feels heavy to author.
Method: grilling session walking the decision tree one fork at a time, grounded in the current setup (`agent-registry.json`, `skill-registry.json`, `roles/ai/tasks/main.yml`, `claude-agent.fish`, `claude-skill.fish`) and in the official Claude Code plugin docs (create-plugins, discover-plugins, plugins-reference), verified 2026-07-13.

## Verdict up front

**Migrate only the staff-engineer fleet to per-agent skills-dir plugins. Leave everything else exactly as it is.**

- The "agent without skills / skills without agent" failure mode is already prevented today by the registry `dependencies` + `dependency_only` fields, the fish resolver (`_claude_agent_install_skill_deps`), and the Ansible `GLOBAL_CLAUDE_SKILLS_EFFECTIVE` expansion. Plugins are not needed to fix coupling.
- The only goal here is internal management + scaffolding, not distribution to other people. That removes plugins' single documented reason to exist, so the bar for adopting them is "does it make internal management enough better to pay the namespacing cost."
- The real pain is authoring: adding one staff-engineer touches ~4 edit sites across two registries and two resolvers, because an agent and its skill live in two separate trees (`~/.claude/agents/*.md` and `~/.claude/skills/*/`) and the coupling can only be expressed as a pointer.
- The one structural thing a plugin uniquely provides is physical colocation: a plugin folder can hold `agents/` and `skills/` together, so the coupling stops being a pointer and becomes impossible to break.
- The staff-engineer fleet is the single clean fit for this, and nothing else is. Everything else pays the plugin cost for no gain.

## Key facts about plugins that drove the decision (verified 2026-07-13)

- A plugin can bundle many agents and many skills plus hooks, MCP, LSP, monitors (`agents/`, `skills/`, `hooks/`, `.mcp.json` at plugin root). "One plugin per subagent" is a choice, not a constraint.
- Plugins **can** depend on other plugins (`dependencies` array with semver in `plugin.json` / marketplace entry). An earlier assumption that they cannot was wrong. Per-agent plugins + a shared "core" plugin is therefore possible, just more moving parts than it is worth here.
- Plugin skills are always namespaced `/(plugin-name):(skill)`, and plugin agents are scoped `(plugin-name):(agent)`. This is the unavoidable cost of any plugin flavor.
- **Skills-directory plugins** are the mechanism that fits this repo: any folder under a skills directory (`~/.claude/skills/<name>/` personal, `<repo>/.claude/skills/<name>/` project) that contains `.claude-plugin/plugin.json` auto-loads as `<name>@skills-dir`, with no marketplace and no install step, and is "discovered in place rather than copied into the plugin cache." That last property is what preserves the edit-once-use-everywhere symlink model.
- Claude Code ignores unrecognized fields in `plugin.json`, so a custom `groups` key can live there for the fish listing tooling.
- Project-scope skills-dir plugins require the workspace trust gate and load only from the launch directory's `.claude/skills/` (no walking up from subdirectories). `SKILL.md` edits are live in-session; `agents/` and `hooks/` edits need `/reload-plugins`.
- Project/user `.claude/agents/*.md` definitions override same-named plugin agents, so a migrated agent must drop its old flat `.md` + registry rows in the same step or the plain copy silently shadows the plugin one.

## Why the fleet, and only the fleet

The natural units are clusters, not individual agents, and they differ in ways that decide the answer:

| Cluster | Coupling | Invocation | Shared skills | Verdict |
|---|---|---|---|---|
| Staff-engineer fleet (backend, platform, frontend, ...) | 1:1 with its own `*-failure-modes` skill | model-invoked (auto-delegated), never slash-typed | none | **Migrate to per-agent skills-dir plugins** |
| Product pipeline (`/0`..`/7`, `product-lead`, research/PM agents) | tight cluster, skills dispatch each other's agents | `product-lead` is a slash-invoked hub; stages are slash-typed | `product-lead` (8), `grilling` (4), `domain-modeling` (2) | Keep as-is |
| Productivity skills (`/commit`, `/pr`, `humanizer`, ...) | standalone | slash-typed daily; `/commit` and `/pr` enforced by `git-skill-gate.sh` | n/a | Keep as-is |
| Vendored upstream skills (fastify, node, react, ...) | not agent-coupled, single skills | model-invoked | n/a | Keep as-is (needs `claude-skill` upstream sync) |

The fleet is unique on every axis that matters:
- 1:1 agent-to-skill means no shared-skill duplication and no need for cross-plugin dependencies.
- Model-invoked means the namespacing tax is invisible: nobody types `/backend-staff-engineer:backend-failure-modes`, and auto-delegation runs off the agent's `description` regardless of scoped name.
- It is the bulk of the hand-maintained churn: ~14 of 22 local agents and ~14 of 35 local skills are the fleet and its failure-mode skills. Colocating them removes the majority of the coupling declarations that cause the authoring pain.

Namespacing would actively hurt the other clusters (rewriting `/0-refine-idea`, the product pipeline's cross-dispatch, and the `/commit` + `/pr` hook), for no benefit, so they stay on the current model.

## The current tooling survives (the three worries)

Moving the fleet to skills-dir plugins does not cost the `claude-agent` ergonomics that are worth keeping:

- **Listing / grouping / Television picker survive.** They are properties of the fish scripts, not the registry. `claude-agent list` globs the `plugins/` directory, reads each `plugin.json` for `name` / `description` / `groups`, and checks symlink status for the `(linked)` marker. The fleet's registry rows disappear entirely; `plugin.json` becomes the single metadata source (decision: read `plugin.json` directly, no slim fleet registry).
- **Edit-once-use-everywhere survives.** Skills-dir plugins are read in place, not copied. Symlink the dotfiles plugin folder into `~/.claude/skills/` (every project) or `<repo>/.claude/skills/` (that project only); editing the source in dotfiles is reflected everywhere. This is the same `ln` model used today, and the repo already symlinks plain skills into `~/.claude/skills/` successfully.
- **Granular per-project selection survives and is unchanged conceptually.** "Granular per-project" vs "use everywhere" is just where the symlink points, not a contradiction. `claude-agent add backend-staff-engineer platform-staff-engineer` keeps working; it symlinks the plugin *folder* into `<repo>/.claude/skills/` instead of a single `.md` into `<repo>/.claude/agents/`, and the failure-mode skill comes along for free because it lives inside the folder. The `_claude_agent_install_skill_deps` resolver deletes itself.

## Rollout plan (three reversible gates)

1. **Prove the linchpin first. DONE, PASSED (2026-07-13).** A throwaway plugin folder (`plugin.json` + `agents/smoke-agent.md` + `skills/smoke-failure-modes/SKILL.md`) symlinked into `~/.claude/skills/smoke-agent` was detected *through the symlink*: `claude plugin list` showed `smoke-agent@skills-dir` with `Status: ✔ loaded` and `Path: ~/.claude/skills/smoke-agent`, and `claude plugin details` reported the inventory `Agents (1) smoke-agent` + `Skills (1) smoke-failure-modes`. No install, no cache copy. The fallback (`claude-agent new` scaffold, no plugins) is therefore not needed. Three facts the test also settled, all relevant to the build:
   - `claude plugin list` and `claude plugin details <name>@skills-dir` work as one-shot CLI reads, so the fish tooling can shell out to them for status/inventory instead of re-deriving from a registry.
   - `claude plugin details` prints a per-component **token cost** (the smoke plugin was ~94 tok always-on), a readout the registry never surfaced.
   - `claude plugin validate` treats the custom `groups` key as a non-fatal **warning** ("Claude Code ignores it at load time"), confirming `plugin.json` is a safe home for listing metadata. Expect that warning on every fleet plugin; it is benign.
2. **Pilot one seat. DONE, PASSED (2026-07-13, branch `feature/fleet-skills-dir-plugins`).** Converted `backend-staff-engineer` into `roles/ai/files/claude/plugins/backend/` (`plugin.json` + `agents/backend-staff-engineer.md` + `skills/backend-failure-modes/`), removed its two registry rows and the flat files (`git mv`), updated the agent's Step 3 prose to the bundled namespaced skill, updated `feature-team`'s seat-inventory step, and taught `claude-agent` (list/add/remove, plain and `--group`) to handle plugin folders. Verified in a sandbox: `claude plugin validate` passes (only the benign `groups` warning); `claude-agent list` shows `backend (plugin) [backend, engineering]` with no double-listing and `backend-staff-engineer` gone as a flat agent; `--group backend` and `--group engineering` both include it; `add backend` symlinks `plugins/backend` into `.claude/skills/backend`; `remove backend` deletes the link. The plugin seat and the still-registry-based rest of the fleet coexist.
   - One fish gotcha fixed: `$c_cyan[$grp]` parses as variable indexing; use the `$c_cyan""[$grp]""` empty-string-separator idiom (same as `claude-skill.fish`).
   - Out of pilot scope, tracked for gate 3: the Television agent picker (`claude-agents.toml` + `_tv_claude_list`) still reads `agents/*.md` and previews `agents/<name>.md`, so it won't see plugin seats until updated; the `ai` role Ansible must also symlink plugin folders; the remaining seats still migrate.
3. **Migrate the rest and wire the tooling. DONE, PASSED (2026-07-14, branch `feature/fleet-skills-dir-plugins`).** Converted the remaining 13 seats (`frontend, design, platform, sre, cloud, data, analytics, gtm, qa, database, security, mobile, dx`) into `plugins/<disc>/`, each bundling its agent + `<disc>-failure-modes` skill, with groups carried into `plugin.json` from the old registry rows. Dropped all 13 agent rows and 13 skill rows from the registries (9 non-fleet `local_agents` remain: `cc-staff-reviewer`, `architect`, and the Product Team agents). Rewrote each agent's Step 3 to the bundled `<disc>:<disc>-failure-modes` form and de-pathed the trigger tables. Landed the two `claude-agent` fixes surfaced by the trust incident: `plugins_target`/`agents_target` now anchor to the git repo root (not CWD, which had produced a misleading `(plugin, linked)` report), and plugin `add`/`remove` print a trust + relaunch reminder. Taught the Television agent picker about plugin seats (`_tv_claude_list` enumerates `plugins/`, `_tv_claude_toggle` and `claude-agents.toml` preview/edit resolve the plugin folder, all repo-root-anchored). Updated the seat-inventory steps in `feature-team` and `architect` and the `README` bench prose to the plugin model.
   - **No Ansible change needed.** None of the 13 seats are in `GLOBAL_CLAUDE_AGENTS` (that list is `cc-staff-reviewer`, `architect`, and the Product Team agents), so the `ai` role's global symlinks never touched the fleet or its failure-mode skills. The fleet is per-project only, installed on demand by `claude-agent`; there is no dead resolver to prune because `_claude_agent_install_skill_deps` still serves the non-fleet agents that declare skill dependencies.
   - Verified: `claude plugin validate` passes (benign `groups` warning) on the new plugins; `claude-agent list` / `list --group` show all 14 seats as plugins with no double-listing; the Television picker lists, filters, and toggles them.
   - **Open follow-up (not in this migration):** `agent-writer`, the skill for authoring a NEW seat, still documents the old flat-agent + registry-wiring flow. Updating it to emit a plugin folder (and refreshing `references/registry-wiring.md`) is tracked separately so future seats follow the plugin pattern.

## The project-scope trust gate (verified 2026-07-13, the "agent doesn't show up" incident)

A migrated seat symlinked into a real project (`work/addingwell/api/.claude/skills/backend`) did not appear in `/plugin list`, `/reload-plugins`, or a fresh `claude plugin list`, even though `claude-agent list` reported it `(plugin, linked)`. Root-caused end to end; the chain matters because every early guess (symlink, permission mode) was wrong:

- **The gate is persisted workspace trust, nothing else.** Project-scope `@skills-dir` plugins load only when the repo has `hasTrustDialogAccepted: true` in `~/.claude.json` (keyed on the git repo root). All the user's work repos were `false`. Isolation test confirmed it is not the symlink: a *real* (non-symlink) plugin folder in an untrusted project also failed to load; the identical folder at **user scope** (`~/.claude/skills/`, which has no trust gate) loaded fine. Claude Code now prints an explicit warning for this: "N project-scope plugin directory ... was not loaded because this workspace was not trusted when plugins were scanned."
- **Permission mode is a different knob from trust.** `--dangerously-skip-permissions` skips tool *prompts* but never sets the trust flag, so bypass-launching leaves project plugins permanently unloaded; `-p` non-interactive mode actively disables trust and keeps the gated config ignored. This is why the seat never loaded in the user's normal (bypass) workflow.
- **Trust is one-time, persisted per repo**, applied by accepting "Yes, I trust this folder" once, or non-interactively by setting `projects["<repo root>"].hasTrustDialogAccepted: true` in `~/.claude.json` (this is the one place the docs name that file/field). Home-directory launches are the exception: trust is held for the session only and never written to disk.
- **Two more load conditions**, independent of trust: launch from the **repo root** (project `@skills-dir` plugins do not walk up from a subdirectory), and a **brand-new plugin folder needs a session restart**, not `/reload-plugins` (reload only re-reads already-scanned plugins and picks up `agents/`/`hooks/` edits; the folder that first appeared mid-session showed only after trust + relaunch).
- **Resolution:** after `hasTrustDialogAccepted: true` + relaunch from root, `claude plugin list` reported `backend@skills-dir  Scope: project  Status: ✔ loaded` and the bundled agent + skill became available. The project-scope, symlinked, editable-in-place, per-repo-granular model is proven working, at the cost of one trust-accept per repo.
- **Design consequence:** per-project granularity (the user's core requirement) is only achievable at project scope, and project scope carries the one-time trust step; user scope is the only trust-free option but loads everywhere. Decision: keep project scope, absorb the one-time trust, surface it in the tooling (see gate 3).

## Scope and non-goals

- In scope: the staff-engineer fleet agents and their `*-failure-modes` skills only.
- Explicitly untouched: the product pipeline, `/commit`-style productivity skills, vendored upstream skills, and the `claude-skill` / `claude-agent` tooling for all of the above.
- Not a goal: distributing any of this to other people or to a marketplace. If that ever changes, revisit, because it would re-open the namespacing and marketplace decisions.
- Naming: decided on the discipline (`backend` -> agent `backend:backend-staff-engineer`), not the redundant agent-name form (`backend-staff-engineer:backend-staff-engineer`). `claude-agent add <discipline>` is the install command (e.g. `claude-agent add backend`, not `... backend-staff-engineer`).
