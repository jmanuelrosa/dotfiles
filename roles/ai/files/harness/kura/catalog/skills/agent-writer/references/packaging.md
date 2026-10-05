# Packaging a new seat or agent

When to read: the agent and its skill are authored and need to be placed and wired.
Two packaging paths, decided in mode selection: a seat (it has a paired failure-modes skill) ships as a catalog bundle; a utility agent (no paired skill) stays a flat file with a registry row.

## Seat: a catalog bundle

A seat and its skill live in one bundle folder, so the coupling cannot drift:

```
roles/ai/files/harness/kura/catalog/bundles/<discipline>/
├── bundle.json
├── agents/<seat>.md
└── skills/<seat>-failure-modes/        (SKILL.md + references/)
```

`<discipline>` is the seat name without the `-staff-engineer` suffix (backend, frontend, sre, dx).
Move the authored files in with `git mv` so history follows them; never leave a seat under the flat `agents/` or `skills/` trees.

### bundle.json

```json
{
  "name": "<discipline>",
  "description": "<Title> staff-engineer seat bundled with its <discipline>-failure-modes checklists.",
  "version": "0.1.0",
  "author": { "name": "Jose Manuel Rosa", "email": "josemanuel.rosamoncayo@gmail.com" },
  "groups": ["<discipline>", "<persona-or-domain>"]
}
```

`groups` lives here, not in a registry. Optional catalog skills the seat expects at runtime go in `requires.skills` (for example `frontend-design` on the design bundle).

### No registry rows

A seat carries no `agent-registry.json` or `skill-registry.json` entry and no `dependency_only` flag: the skill ships with the agent because they share the folder, not because a resolver pulls it.
Do not tag the discipline `global`; seats are per-project.

### How it loads and is provisioned

Projects install with `kura add <discipline> --type bundle` in an initialized repo. Kura links the agent to `.claude/agents/<seat>.md` (and Pi's agent root) and the failure-modes skill to the harness skill roots under bare names (`backend-failure-modes`, not a prefix).
After adding a bundle, trust the workspace (`kura trust --on`) and restart the harness from the repo root if artifacts do not appear immediately.

## Utility agent: flat file plus registry row

A utility agent (no paired skill) is a flat file with a registry entry:

`roles/ai/files/harness/kura/catalog/agents/<name>.md` plus a `local` entry in `kura/catalog/agent-registry.json`:

```json
{
  "name": "<name>",
  "groups": ["<discipline>", "<persona-or-domain>"],
  "note": "Locally authored"
}
```

Add `dependencies: ["<skill>"]` only if it invokes a skill at runtime. Add `"global"` to its groups if it belongs in both harnesses' global agent views; bare `kura sync` also projects its skill dependencies.
Always edit the registry via a python3 round-trip with `json.dump(..., indent=2)`; never hand-edit.

## Groups vocabulary

Tags come from the controlled vocabulary in the repo CLAUDE.md's groups paragraph, in facet order: discipline, persona, technology, topic.
Reuse an existing tag before coining one; the tooling treats groups as opaque, so no code change is needed either way.
Coining is legitimate when the fleet already carries the tag (that is how `data` and `security` were coined): add the new tag to the matching facet list in CLAUDE.md as part of the same change.
The seat convention is `["<discipline>", "<persona-or-domain>"]` in `bundle.json`; the paired skill no longer carries its own group list, since it is not browsable on its own.

## Agent frontmatter gotcha

Multi-line `description` values must use `>-` folded scalars: a plain scalar breaks silently when a continuation line contains ": ", and style sweeps have reintroduced this before.
