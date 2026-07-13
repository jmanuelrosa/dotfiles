---
name: feature-team
description: Run a feature through the staff-engineer team - architect spec, plan approval, parallel dispatch to the installed seats, verification, integration report
disable-model-invocation: true
---
Orchestrate the staff-engineer seats through a full feature pipeline.
You (the main conversation) are the team lead: you dispatch, monitor, and integrate.
Delegate the tasks, not the judgment.

ARGUMENTS: the feature brief.
If empty, ask for it before anything else.

1. **Restate the brief** in one sentence and confirm scope.
   If it is fuzzy (multiple readings, unstated constraints), stop and suggest running /grill-me on it first; offer to continue with the current brief only if I decline.
2. **Inventory the seats.** List `.claude/agents/` and `~/.claude/agents/`.
   Report which staff-engineer seats are installed.
   If the work clearly needs a seat that is missing (tests → qa, migrations → database, pipelines → platform, IaC → cloud, data/dbt → data/analytics, SLOs → sre), give me the exact `claude-agent add <seat>` command and wait; frontend/backend cover their slices when no specialist is installed.
3. **Design.** Dispatch the architect subagent with the brief.
   It returns a spec at docs/specs/ plus dispatch briefs per seat.
   If it returns `needs-decision`, bring me the decision brief, collect my answer, and re-dispatch.
4. **Approval gate.** Show me the spec's objective, acceptance criteria, owner split, and decision items (reference the spec file, don't paste it whole).
   Wait for my explicit approval before any implementation.
   It is cheaper to fix a bad plan than bad code.
5. **Dispatch in parallel.** For each slice, spawn the owning seat in a single message so they run concurrently.
   Each dispatch prompt must carry: the goal (one sentence), the spec path and sections to read, the files it owns, the acceptance criteria numbers, and any pre-authorizations from the spec (schema changes, new dependencies).
   Enforce one-file-one-owner: if two briefs claim the same file, fix the split before dispatching.
   Dispatch dependent slices only after the slices they depend on report done.
6. **Verification gate.** Read each completion report.
   A seat reporting `blocked` or `needs-decision` comes back to me with its question before its dependents run.
   Confirm every report's verification section shows real command output; anything "not runtime-verified" gets listed for me.
   Then suggest /code-review on the combined diff.
7. **Integration report.** End with: per-seat status table, acceptance criteria met/unmet, pending ask-first items, gotchas the seats proposed for CLAUDE.md, and the suggested next step (/code-review, then /commit).
   Do not commit; that is mine to run.

Single-seat tasks don't need this pipeline - delegate directly instead.
Use this skill when the work spans two or more seats or needs the architect's spec first.
