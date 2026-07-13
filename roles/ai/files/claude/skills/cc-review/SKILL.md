---
name: cc-review
description: Run the cc-staff-reviewer over my Claude Code setup (user + project scope)
disable-model-invocation: true
---
Maintenance review of my Claude Code configuration.

1. Check for /insights data in ~/.claude/usage-data/ (facets/*.json preferred, else report.html).
   If neither exists, tell me to run /insights first, but offer to proceed config-only.
2. Use the cc-staff-reviewer subagent to review my setup at BOTH scopes: user (~/.claude) and the current project (.claude/ found from cwd).
   State which scope it actually detected.
3. Return its prioritized P0-P2 report, the adoption opportunities, the proposed new artifacts, the action table, and the top-3 next moves verbatim.
4. If the report lists adoption opportunities or proposed new artifacts, ask me which to take with AskUserQuestion (multiSelect; one option per item, description = the why + how in one line).
   Skip the question entirely when there are none.
5. Act on each accepted item here in the main conversation: config changes directly (settings.json, frontmatter, rule files); new skills via /skill-writer; settings/hooks via the update-config skill.
   Show what changed.
   If a changed file is a symlink into my dotfiles repo, say so and offer /commit there (new locally authored artifacts belong in that repo's registries).
   Drop declined items without ceremony.

The subagent never modifies files.
In this conversation, modify files only for items I explicitly accepted in step 4.
