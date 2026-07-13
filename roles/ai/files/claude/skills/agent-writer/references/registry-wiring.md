# Registry wiring

When to read: wiring a new agent and its paired skill into the registries.
Always edit both JSON files via a python3 round-trip with `json.dump(..., indent=2)`; never hand-edit.

## skill-registry.json

The paired skill goes into `local_skills`:

```json
{
  "name": "<seat>-failure-modes",
  "groups": ["<discipline>", "<persona-or-domain>", "review"],
  "dependency_only": true,
  "note": "Locally authored"
}
```

`dependency_only: true` hides it from browsing surfaces (`claude-skill list`, the Television picker) and makes `claude-skill add <name>` refuse it directly, pointing at the parent agent; it stays synced and is pulled automatically as a dependency.
Beware the structure when querying: `repos` is a dict keyed by repo name, each with a `skills` list whose names derive from the `upstream_path` basename; `local_skills` is a flat list of dicts with `name`.

## agent-registry.json

The agent's `local_agents` entry gains (or is created with) `dependencies` naming skills, not agents:

```json
{
  "name": "<seat>",
  "groups": ["<discipline>", "<persona-or-domain>"],
  "dependencies": ["<seat>-failure-modes"],
  "note": "Locally authored"
}
```

The `ai` role folds each global agent's skill dependencies (plus one level of those skills' own deps) into `GLOBAL_CLAUDE_SKILLS_EFFECTIVE`, and `claude-agent add` installs the closure into a project, deliberately bypassing the `dependency_only` refusal.
`claude-agent list` then shows `<seat> (needs: <seat>-failure-modes)`: that line is a verification-sweep check.

## Groups vocabulary

Tags come from the controlled vocabulary in the repo CLAUDE.md's groups paragraph, in facet order: discipline, persona, technology, topic.
Reuse an existing tag before coining one.
Coining is legitimate when the agent registry already carries the tag (that is how `data` and `security` were coined): add the new tag to the matching facet list in CLAUDE.md as part of the same change.
The tooling treats groups as opaque, so no code changes are needed either way.
The failure-modes family convention is `[discipline, persona-or-domain, "review"]` for the skill and `[discipline, persona-or-domain]` for the agent.

## Global availability

Agents that should exist in every project go into `GLOBAL_CLAUDE_AGENTS` in `roles/ai/defaults/main.yml`; their skill closure ships automatically.
Per-project seats (the staff engineers) stay out of the global list and are installed with `claude-agent add <seat>`.

## Agent frontmatter gotcha

Multi-line `description` values must use `>-` folded scalars: a plain scalar breaks silently when a continuation line contains ": ", and style sweeps have reintroduced this before.
