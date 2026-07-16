# Seat agent anatomy

When to read: writing or rewriting the agent file itself.
The living exemplars are `plugins/backend/agents/backend-staff-engineer.md` and `plugins/platform/agents/platform-staff-engineer.md` (each bundled with its skill under the same `plugins/<discipline>/`); read them before this file means anything.

## Budget

Hard cap ~200-205 lines; the shipped seats land at 202-205.
Pay for additions by consolidating: merge ask-first rows, merge red flags, drop the weakest rationalization row.
Advisor seats land well under the cap; never pad to fill it.

## Frontmatter

```yaml
---
name: <seat-name>
description: >-
  <role in one line>. Use PROACTIVELY when delegating <discipline> work: <surfaces>.
  Detects the stack, routes to installed skills and to its <seat>-failure-modes checklists,
  implements within strict boundaries, self-verifies, and returns a structured completion report.
  Not the <sibling> seat (<what>), and <the identity never, e.g. "never deploys">.
model: opus
---
```

Always `description: >-`: plain multiline scalars silently break on ": " in continuation lines.
Implementer seats use `model: opus`; advisor seats may differ (security uses `fable` and a `tools:` allowlist) and those lines must survive edits.

## Section order (byte-for-byte family shape)

1. H1 title.
2. Intro paragraph: the seat's product in one sentence, "hired for judgment", conventions outrank preferences, final message MUST follow the report contract.
3. `## Operating loop`: 8 numbered steps. Step 1 restates the brief plus the blast radius (which <surfaces, consumers, contracts> the change can reach) and bails to `needs-decision` on ambiguity or ask-first actions. Steps 2-4 point at Steps 1-3 below. Then read-before-writing, small verifiable increments, gate + self-check, report.
4. `## Step 1: Detect the stack (always, before any edit)`: a signal table (file globs -> what it tells you), ending with the `CLAUDE.md` / `AGENTS.md` row ("outrank everything in this file except the never tier") and a "Different stack?" fallback paragraph.
5. `## Step 2: Route to installed skills`: inventory, invoke every matching skill, unmatched tech goes to the report as `claude-skill add <name>`.
6. `## Step 3: Open the failure-mode checklists`: states that the `<seat>-failure-modes` skill is bundled in this plugin (invoked as `<discipline>:<seat>-failure-modes`) and loads automatically with the agent, the "typical brief fires..." example, then the trigger table of bare domain names (no lookup paths, no not-installed fallback, since a plugin always ships its skill); the domains match the skill's router table in the same order (see `coherence-rules.md`).
7. `## Ways of thinking`: ~7 bold-led bullets of staff judgment (reversible vs irreversible, invisible consumers, why-not-mechanizable, the seat's own core stances).
8. `## Red flags: refuse to ship`: ~8 bullets, each a stop-and-fix or `needs-decision` if the brief forces it.
9. `## Boundaries`: three tiers. ✅ Always (5 bullets, last is "run the gate and self-check before reporting done"). ⚠️ Ask first ("stop and report `needs-decision` with your recommendation; do not proceed"). 🚫 Never: the seat identity invariants, sibling-surface exclusions with the owning seat named, secrets, lockfiles, `git commit`/`git push`, claiming unrun checks, editing CLAUDE.md.
10. `## Verification gate`: Static mandatory, ending "If anything fails: fix it, or report the failure honestly with its output. Never report done over a red check."; a mechanized-quality or runtime block with the seat's honesty wording ("not runtime-verified" or equivalent); bounded self-correction (3 distinct attempts, then `blocked`).
11. `## Pre-handoff self-check (definition of done)`: ~10 checkboxes; the first is always "Every checklist item from the failure-mode references you opened is resolved or escalated."
12. `## Common rationalizations`: intro carries the letter-vs-spirit clause ("violating the letter of a boundary while honoring your reading of its spirit is still violating it"), then a ~7-row Rationalization | Reality table.
13. `## Completion report`: fenced template with Status / Stack detected / Skills used ("invoked skills and failure-mode references read") plus Gaps, then sections: Changes, Verification, Self-check, Decisions and trade-offs, Pending ask-first items, Missing gates, Discovered gotchas, plus any seat-specific keeps. Under 30 lines, omit empty sections.
14. `## Composition`: invoke directly when; siblings with hand-across rule; after done (review is a separate step, orchestration belongs to the caller).

## Family style

Headings are `## Step 1: ...` with a colon, never a dash.
Arrows are `->`, never a unicode arrow.
No em or en dashes anywhere; semantic line breaks in prose.
Boundary tiers keep the ✅/⚠️/🚫 markers.
Report section names are exactly "Decisions and trade-offs" and "Pending ask-first items".
