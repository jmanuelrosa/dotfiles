# Claude

Management system for Claude Code skills, agents, and MCP servers. Skills and agents live in this directory and are linked into projects via the `claude:skill` and `claude:agent` fish functions (`add`/`remove` subcommands).

This document covers how to **add new skills and agents to the dotfiles repo** itself, so they become available for linking.

## The Tracked/Local Rule (Skills)

Every skill in this repo is either:

- **Tracked** — synced from an upstream GitHub repo, declared under `repos` in [skill-registry.json](skill-registry.json), or
- **Local** — authored (or consolidated) here, declared under `excluded` in [skill-registry.json](skill-registry.json).

**Never both, never neither.** The `excluded` array is not just a "skipped" list — it's the authoritative inventory of local skills. If a skill exists on disk but doesn't appear in either place, that's a bug.

## Adding Skills

### Option A — Local skill

1. Create the directory with a `SKILL.md`:

   ```
   roles/ai/files/claude/skills/my-skill/
     SKILL.md
   ```

   Or, for grouped skills:

   ```
   roles/ai/files/claude/skill-groups/<group>/my-skill/
     SKILL.md
   ```

2. Declare it in `excluded` in [skill-registry.json](skill-registry.json) with a reason:

   ```json
   { "name": "my-skill", "reason": "Locally authored" }
   ```

   Common reasons: `"Locally authored"`, `"Consolidated from multiple sources"`, `"No external source"`.

### Option B — Track from an upstream repo

1. Add an entry to [skill-registry.json](skill-registry.json) under the appropriate repo key:

   ```json
   {
     "upstream_path": "skills/some-skill",
     "local_path": "skills/my-local-name",
     "name": "my-local-name"
   }
   ```

2. Run `claude:skill update <name>` to pull it down.

## Adding Agents

### Local agent

Create the file directly:

```
roles/ai/files/claude/agents/my-agent.md
```

The agent registry is currently empty, so no `excluded` declaration is required yet. If it grows, follow the same tracked/local rule as skills.

### From an upstream repo

1. Add an entry to [agent-registry.json](agent-registry.json):

   ```json
   {
     "upstream_path": "agents/some-agent.md",
     "name": "my-agent"
   }
   ```

2. Run `claude:agent update <name>` to pull it down.

## Registry Format

### skill-registry.json

```json
{
  "version": 1,
  "repos": {
    "owner/repo": {
      "branch": "main",
      "skills": [
        {
          "upstream_path": "skills/some-skill",
          "local_path": "skills/local-name",
          "name": "local-name"
        }
      ]
    }
  },
  "excluded": [
    { "name": "skill-name", "reason": "Locally authored" }
  ]
}
```

- **`repos`** — keyed by `owner/repo`. Each repo has a `branch` and a `skills` array. Each skill maps `upstream_path` (path in the upstream repo) → `local_path` (path under this directory) with a `name` used by `claude:skill` commands.
- **`excluded`** — **authoritative inventory of local skills.** Every local skill directory under `skills/` or `skill-groups/` must appear here. Use `reason` to document why it's local (locally authored, consolidated, etc.).

### agent-registry.json

```json
{
  "version": 1,
  "repos": {
    "owner/repo": {
      "branch": "main",
      "agents": [
        {
          "upstream_path": "agents/some-agent.md",
          "name": "my-agent"
        }
      ]
    }
  },
  "excluded": []
}
```

- **`agents` array** — maps `upstream_path` → `name` (the `.md` filename without extension in `agents/`).
- **`excluded`** — reserved for local agents when the registry starts being used.

## Directory Structure

```
roles/ai/files/claude/
  skills/                 # Individual skills (directories with SKILL.md)
  skill-groups/           # Grouped skills (group/skill-name/)
  agents/                 # Agent .md files
  skill-registry.json     # Tracked upstream + local (excluded) inventory
  agent-registry.json     # Tracked upstream agents
```

## Resources

- https://skills.sh/
