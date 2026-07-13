# Skill Scout Specification

## Intent

`skill-scout` recommends which skills from the local catalog are worth adding to the current project, then offers to install the chosen ones.

Its purpose is to turn the flat skill registry into project-aware advice: it analyzes the working directory's tech stack and needs, ranks relevant skills, and excludes anything already available so the user only sees actionable, novel recommendations.

## Scope

In scope:

- Analyzing the current project (manifests, configs, structure, CLAUDE.md/README) to infer technologies and needs.
- Matching registry skills holistically by name, groups, and `SKILL.md` description.
- Excluding globally-installed (`~/.claude/skills/`) and `dependency_only` skills; marking project-linked (`.claude/skills/`) skills as already present.
- Presenting a confidence-tiered report (skill, why, description, groups).
- Installing selected skills via the `claude-skill add` CLI.

Out of scope:

- Authoring, editing, or merging skills (that is `skill-writer`).
- Managing the registry itself, syncing upstream, or removing skills.
- Recommending skills outside the tracked registry.
- Re-implementing dependency resolution, download, or symlinking: these are delegated to `claude-skill add`.

## Users And Trigger Context

- Primary users: humans and agents deciding which skills to add to a project.
- Common user requests: "which skills should I add?", "recommend skills for this repo", "what skills fit this codebase?", "scout skills for my project", "setting up a project, what skills are useful?".
- Should not trigger for: creating/writing/improving a skill (→ `skill-writer`), listing all skills (→ `claude-skill list`), adding one named skill directly (→ `claude-skill add`), info queries about a specific skill, or removing a skill.

## Runtime Contract

- Required first actions:
  - Verify `$DOTFILES_DIR` is set; stop with a clear message if not.
  - Build the candidate set from the registry, dropping globally-installed and `dependency_only` skills and marking project-linked ones.
  - Analyze the working directory before ranking.
- Required outputs:
  - A confidence-tiered report (Strong match / Worth considering) where every recommended line carries name, groups, a project-specific Why, and the description; already-linked skills listed separately and never offered.
  - When the user selects skills: a one-line summary of what was linked.
- Non-negotiable constraints:
  - Never recommend a globally-installed or `dependency_only` skill.
  - Never offer to re-add a project-linked skill.
  - Installation is gated behind explicit user confirmation (AskUserQuestion); the analysis/report phase is read-only.
  - Surface auto-pulled dependencies before adding a skill that declares them.
  - Do not return an empty report: when the stack has no catalog tech skills, fall back to language-agnostic skills inferred from gaps and CLAUDE.md.
- Expected bundled files loaded at runtime: none beyond `SKILL.md` (single inline skill).

## Source And Evidence Model

Authoritative sources:

- `$DOTFILES_DIR/roles/ai/files/claude/skill-registry.json`: names, groups, `dependencies`, `dependency_only`.
- Each skill's `SKILL.md` frontmatter under `$DOTFILES_DIR/roles/ai/files/claude/skills/<name>/`: descriptions.
  Step 1 emits name + groups + description in one pass (bulk `grep`), so Step 4 does no per-skill reads; block-scalar descriptions (3 skills) are read individually only if shortlisted.
- The current project: `package.json` (JS/TS tags), Swift/iOS markers, repo structure/gaps, and `CLAUDE.md`/`README.md`.
- `~/.claude/skills/`: globally-installed set (exclude).
- `.claude/skills/` in the working directory: project-linked set (mark).
- The `claude-skill` CLI: the install path.

Data that must not be stored: secrets, tokens, private paths, or customer data encountered while analyzing a project.

## Reference Architecture

- `SKILL.md` contains the full five-step runtime workflow, the candidate-catalog jq snippet, the analysis signals, the report format, and the install step.
- `SPEC.md` contains this maintenance contract.
- No `references/`, `scripts/`, or `assets/`: the skill is small, single-path inline guidance and needs no routed depth.

Execution shape: inline-guidance (primary); argument-driven and prompt-chaining (secondary mechanics).
Simpler shapes were considered; no reference split is warranted at the current size.

## Validation

- Lightweight validation:
  - Run `uv run ~/.claude/skills/skill-writer/scripts/quick_validate.py roles/ai/files/claude/skills/skill-scout`.
  - Confirm `skill-registry.json` still parses and `claude-skill list` shows `skill-scout` with its groups.
- Acceptance gates:
  - Validator passes with no errors.
  - Exclusion and marking rules behave correctly in a real project run.
  - The report carries skill, why, description, and groups for every entry.

## Known Limitations

- Dotfiles-coupled: requires `$DOTFILES_DIR` and the on-disk registry; not portable to machines without this dotfiles checkout.
- Tech-specific matching covers **JS/TS and Swift/iOS only**, the only ecosystems the catalog has skills for.
  Other stacks (Rust, Go, Python, Ruby, …) receive only language-agnostic recommendations.
  Revisit Step 2 if the catalog gains skills for a new ecosystem.
- Descriptions are available only for downloaded skills; undownloaded registry skills fall back to groups-only.
- The install picker uses AskUserQuestion, capped at four options per question; beyond ~16 recommendations the printed report is the complete list and extras are added manually.
- Matching is heuristic over names, groups, and descriptions; it can miss a relevant skill or over-rank a weak one.

## Maintenance Notes

- Update `SKILL.md` when the workflow steps, candidate-catalog query, analysis signals, report format, or install behavior change.
- Update `SPEC.md` when intent, scope, trigger context, runtime contract, evidence model, validation, or limitations change.
- The jq prelude (`dn` / `allskills` / `visibleskills`) is duplicated in three places: `_claude_skill_jqlib` in `roles/shell/files/fish/functions/claude-skill.fish`, the `jqlib` literal in `roles/shell/files/fish/functions/_tv_claude_list.fish`, and Step 1 of this skill's `SKILL.md`.
  Keep all three in sync when the registry shape changes.
