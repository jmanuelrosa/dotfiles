# Packaging a new seat or agent

When to read: the agent and its skill are authored and need to be placed and wired.
Two packaging paths, decided in mode selection: a seat (it has a paired failure-modes skill) ships as a skills-dir plugin; a utility agent (no paired skill) stays a flat file with a registry row.

## Seat: a skills-dir plugin

A seat and its skill live in one plugin folder, so the coupling cannot drift:

```
roles/ai/files/claude/plugins/<discipline>/
├── .claude-plugin/plugin.json
├── agents/<seat>.md
└── skills/<seat>-failure-modes/        (SKILL.md + references/)
```

`<discipline>` is the seat name without the `-staff-engineer` suffix (backend, frontend, sre, dx).
Move the authored files in with `git mv` so history follows them; never leave a seat under the flat `agents/` or `skills/` trees.

### plugin.json

```json
{
  "name": "<discipline>",
  "description": "<Title> staff-engineer seat bundled with its <discipline>-failure-modes checklists.",
  "version": "0.1.0",
  "author": { "name": "Jose Manuel Rosa", "email": "josemanuel.rosamoncayo@gmail.com" },
  "groups": ["<discipline>", "<persona-or-domain>"]
}
```

`groups` lives here, not in a registry; the fish tooling reads it straight from `plugin.json`.
`claude plugin validate <plugin dir>` prints one benign warning ("Unknown field 'groups'. Claude Code ignores it at load time"); that is expected on every seat plugin, not a failure.

### No registry rows

A seat carries no `agent-registry.json` or `skill-registry.json` entry and no `dependency_only` flag: the skill ships with the agent because they share the folder, not because a resolver pulls it.
Do not add the discipline to `GLOBAL_CLAUDE_AGENTS`; seats are per-project.

### How it loads and installs

The folder auto-loads as `<discipline>@skills-dir`; the agent is `<discipline>:<seat>` and the skill is `<discipline>:<seat>-failure-modes`.
Install into a project with `claude-agent add <discipline>` (it symlinks the plugin folder into `.claude/skills/`, the same edit-once-use-everywhere model as flat agents).
A project-scope plugin loads only in a trusted workspace (the repo root has `hasTrustDialogAccepted: true`) and only when Claude Code is launched from that repo root; a freshly linked plugin needs a full restart, not `/reload-plugins`.

## Utility agent: flat file plus registry row

A utility agent (no paired skill) stays a flat file with a registry entry, unchanged:

`roles/ai/files/claude/agents/<name>.md` plus a `local_agents` entry:

```json
{
  "name": "<name>",
  "groups": ["<discipline>", "<persona-or-domain>"],
  "note": "Locally authored"
}
```

Add `dependencies: ["<skill>"]` only if it invokes a skill at runtime; add it to `GLOBAL_CLAUDE_AGENTS` in `roles/ai/defaults/main.yml` only if every project needs it.
Always edit the registry via a python3 round-trip with `json.dump(..., indent=2)`; never hand-edit.

## Groups vocabulary

Tags come from the controlled vocabulary in the repo CLAUDE.md's groups paragraph, in facet order: discipline, persona, technology, topic.
Reuse an existing tag before coining one; the tooling treats groups as opaque, so no code change is needed either way.
Coining is legitimate when the fleet already carries the tag (that is how `data` and `security` were coined): add the new tag to the matching facet list in CLAUDE.md as part of the same change.
The seat convention is `["<discipline>", "<persona-or-domain>"]` in `plugin.json`; the paired skill no longer carries its own group list, since it is not browsable on its own.

## Agent frontmatter gotcha

Multi-line `description` values must use `>-` folded scalars: a plain scalar breaks silently when a continuation line contains ": ", and style sweeps have reintroduced this before.
