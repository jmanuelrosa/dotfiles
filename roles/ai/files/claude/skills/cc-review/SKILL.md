---
name: cc-review
description: Run the cc-staff-reviewer over my Claude Code setup (user + project scope)
disable-model-invocation: true
---
Maintenance review of my Claude Code configuration.

1. Check for /insights data in ~/.claude/usage-data/ (facets/*.json preferred, else report.html).
   If neither exists, tell me to run /insights first, but offer to proceed config-only.
2. Use the cc-staff-reviewer subagent to review my setup at BOTH scopes — user (~/.claude)
   and the current project (.claude/ found from cwd). State which scope it actually detected.
3. Return its prioritized P0–P2 report, the action table, and the top-3 next moves verbatim.

Do not modify any files — this is advisory only.
