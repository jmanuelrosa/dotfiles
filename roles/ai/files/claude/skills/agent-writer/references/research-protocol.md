# Research protocol

When to read: before launching the two researchers in Step 3.
Launch both in the background, in parallel, before authoring starts; author against the canon while they run and fold their deltas in when they report.

## Researcher (a): `<seat>-ladder-researcher`

**Question:** what distinguishes staff-level judgment in this discipline, right now.

**Sources:** public engineering ladders (GitLab, Dropbox, Etsy, Monzo, Medium's Snowflake, Rent the Runway, CircleCI, Buffer, Khan Academy, Financial Times; staffeng.com and progression.fyi index dozens more) and current job postings at 8-12 companies known for the discipline (pick names the discipline respects, not generic FAANG filler).

**Deliverable:** discipline-specific judgment themes, each translated into a behavior a coding agent can actually exhibit, plus the 12-24 month shifts reshaping the discipline (new defaults, consolidating tools, AI-era risks).
Tell it explicitly to skip generic staff themes (communication, mentorship, influence).

## Researcher (b): `<seat>-pack-researcher`

**Question:** which concrete checks does a strong model still skip under completion pressure.

**Sources:** community agent packs (wshobson/agents, VoltAgent/awesome-claude-code-subagents, anthropics/claude-plugins-official) plus checklist-rich non-Claude catalogs.
The catalogs are the gold: rule sets that machine-check the discipline (zizmor, actionlint, hadolint, kube-score, strong_migrations, squawk, dbt_project_evaluator, eslint-plugin-jest, sqlfluff, OWASP ASVS, OpenSSF Scorecard) plus official best-practice docs with named failure semantics.

**Deliverable:** candidate checks seeded with 10-15 traps you already suspect, each flagged NOVEL vs LIKELY-REDUNDANT against the sibling failure-modes skills and installed stack skills.
Tell it to reject tutorials, tool-version-specific API usage, and arbitrary numeric gates, and to keep published standards with their source named.
For defensive-security seats, both briefs stay strictly defensive: assessment and hardening, never exploitation technique.

## Mechanics

Background agents deliver via teammate-message notifications; end the turn and get re-invoked rather than polling TaskOutput.
If a researcher dies mid-response ("connection closed mid-response" or similar), SendMessage it to resend its final deliverable; it recovers with its research intact.
Do not relaunch: a fresh researcher repeats the work and loses the report.

## Folding research in

Research amends the draft, it does not restructure it: new checks slot into existing references, new themes sharpen Ways of thinking bullets, shifts inform escalation triggers.
The final message states what was adopted and what was deliberately rejected, with one line of why per rejection.
No research doc is committed; the reports live and die in the session.
