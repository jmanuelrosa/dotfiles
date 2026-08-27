---
name: to-plan
description: Research (via subagent), draft, and iteratively review a plan before implementation. Use for cross-cutting changes that need alignment before code — new subsystems, DSLs, permission models, architecture shifts, refactors spanning many files. Exploration runs in a subagent to keep main context clean; produces `docs/design/<name>.md` and walks through it step-by-step.
disable-model-invocation: true
---

# Plan

Research a problem space, produce a written design doc, walk the user through it one step per turn, iterate on pushback, lock it in, *then* implement.

## When to use

Trigger when the request is to **plan** or **understand**, not to do. Key phrases: *research*, *design*, *how should we*, *flesh out*, *walk me through*, *figure out*, *plan the approach*, *write a proposal*.

Also trigger proactively when the user asks to implement something that touches more than one subsystem (e.g. models + workers + views), introduces a new pattern or DSL, or changes behavior for multiple user types (permission, feature flag).

## When NOT to use

Skip the design doc for single-file fixes (just fix it), changes that match an existing pattern exactly (new controller action, new report column — copy the pattern), bug hunts (investigate and fix, no doc needed), or when the user says "just do it" or shows time pressure.

Err on the side of NOT using it. A pointless design doc wastes a round-trip. If in doubt, state your assumptions briefly and ask "design doc first, or want grug just start?"

## The phases

Each phase has a clear exit signal. Do not advance until the signal is clear. Phase 1.5 is optional; skip when scope is already clear.

### Phase 1 — Research (silent, subagent-first)

Goal: understand existing code and constraints before writing a word of the doc.

**Default: dispatch subagent (`explore` or `general`).** Main context is finite. Research burns through many files, extracts patterns, discards detail — subagent is the disposable scratch pad for that work. Main context then reads only the 2-5 load-bearing files the subagent flagged. Direct-reading 20 files in main context poisons every later turn with detail that should have been summarised away.

**Dispatch rule:**

| Scope | Action |
|-------|--------|
| >3 files, scope unknown, or "look across codebase" | **must** dispatch subagent |
| ≤3 files, user named them, already open in this session | direct read ok |
| follow-up to subagent findings in same session | direct read the 2-5 load-bearing files subagent named |
| user says "don't branch out, just read X" | honor user, skip dispatch |

When in doubt, dispatch. Cheap to run, expensive to undo wrong-direction research already in main context.

**What grug ask subagent for** (one dispatch, structured task):

*Local code:*
- file:line of every candidate hook point the design might use
- at least two existing patterns for similar problems (paths + one-line summary each)
- framework / gem involved (`gem which <name>`, `bundle info`, `npm ls`), file:line of relevant hook
- existing policy / permission / feature-flag layers already enforcing what the design will touch (so design doesn't duplicate)
- directories with similar design docs or conventions the new doc should fit
- **contradictions**: places where the user's stated belief disagrees with the code

*Web (when relevant — tell subagent to `WebSearch` / `WebFetch`):*
- official doc / changelog for gem or library the design hooks into (pin version from `Gemfile.lock` / `package-lock.json` — doc must match installed version)
- GitHub issues / PRs on the upstream repo discussing the hook point or known gotcha
- RFC, ADR, or spec when design touches a standard (OAuth, OIDC, JSON Schema, etc.)
- prior-art writeups when introducing a novel pattern ("how did project X solve Y") — bounded, 2-3 sources max

Skip web research when the change is purely internal (refactor, new controller action in existing pattern, permission model on top of existing DSL). Web research is for *external unknowns*, not for things grug can answer from the codebase.

Require subagent return a **structured findings pack**: bulleted, file:line per local claim, URL + one-line takeaway per web claim, no prose essay. Reject a pack that is narrative — ask for bullets + citations.

**Cross-reference user claims:** subagent verifies any "X already works like Y" in code. Contradiction → surface as the **top bullet** of the Phase 2 reply. Doc cannot rest on a wrong premise.

**Exit signal** (all three):

1. Subagent findings pack received — OR — direct-read path explicitly justified against the dispatch rule above.
2. Grug can name file:line of every hook point the design will use.
3. Grug knows which existing patterns the design will mirror.

If findings pack is thin or contradictory, dispatch a second, narrower subagent task — do not paper over gaps by main-context grepping.

### Phase 1.5 — Targeted interview (optional)

Goal: resolve design-tree branches the initial request left open, before committing to a recommendation. Only ask when the answer would **change the design**. Not to gather color, not to feel thorough.

Good branch questions are ones where the answer forks the design: *"Is this gate per-tool or per-agent?"* changes the DSL surface; *"Should existing owners keep full access on plan downgrade?"* changes the runtime behaviour matrix; *"One permission per tool, or can a tool need several?"* changes API semantics.

Rules to keep it tight: skip when scope is already clear (most requests are); max one round — ask the 1-3 most load-bearing questions in a single numbered reply, do not loop; time-box — if answers don't resolve a branch, state an explicit assumption and move on, don't re-ask; ask about decisions, not facts — facts you dig up yourself in Phase 1, interview is only for decisions the user must make; batch — if you have 3 questions, one reply with all 3, don't ping-pong.

When in doubt, skip the interview and put the question in Phase 2's "open question for you" section instead. Same information, fewer round-trips.

Exit signal: user answers or says "your call" / "pick safer".

### Phase 2 — Findings reply (short, bulleted)

Goal: surface what you learned, propose an approach, invite pushback — **before** writing the doc.

Keep this reply tight. Bullet lists, file:line citations, explicit recommendation, one to three open questions. End with a concrete next-action question like *"want grug flesh out design doc, or adjust approach first?"*

Structure:

```
**existing <thing> today** (file:line)
- fact
- fact

**<hook point> today** (file:line)
- fact
- fact

**tool/surface → <gate> rough map**
- X → Y

**recommend approach (grug pick)**
1. ...
2. ...

**open question for you**
- ...
```

This phase exists to catch wrong assumptions cheaply. Never skip straight to the doc.

Exit signal: user replies with direction ("flesh out doc", "try approach B", "also consider Z").

### Phase 3 — Design doc draft

Goal: write a full doc to `docs/design/<kebab-name>.md` that someone unfamiliar with the conversation could read and understand.

Use the template below. Prose is appropriate here — this is generated content for an outside audience (team, future self). Drop the grug voice inside the doc, but keep it in the chat reply that delivers it.

After writing, reply with a short summary of the doc sections and ask *"want grug walk through step-by-step, or review doc first?"*

Exit signal: user asks for walkthrough or signals review complete.

### Phase 4 — Walkthrough (one step per turn)

Goal: verify understanding and catch design flaws that only surface when explained sequentially.

The walkthrough is **branch resolution in action**. Each step often depends on decisions from the previous step — DSL shape depends on hook-point choice, filter logic depends on DSL shape, mapping depends on abstraction. One step per turn lets the user challenge a branch before downstream steps commit to it.

Rules: one step per turn, never combine multiple steps in one reply because the user must be able to push back between steps; short per step, roughly 150-300 words, with file:line citations and code snippets for anything structural; end each step with a resume prompt like `"ready for step N+1 (<topic>)?"`; accept pushback mid-walkthrough — if the user questions or disagrees, stop the sequence, address it, refine the design, then ask whether to resume or replan.

When a refinement lands, decide where it goes. **Structural refinements** — a new design rule, a mapping expansion, a renamed helper, a layer change — update the doc in the **same turn** via targeted `Edit`, then continue the walkthrough. The doc stays honest mid-session. **Minor refinements** — wording tweaks, small caveats — batch and apply after the last step in one pass.

Step ordering, roughly: the problem (motivation); the existing system you build on; hook points and integration surface; the core new abstraction (DSL, class, module); mapping table (old → new, permission → tool, route → handler, etc.); each filter, layer, or component of the design, one per step. Skip detail the user says they don't care about (test, telemetry).

Exit signal: all steps covered, or user signals "enough" / "got it".

### Phase 5 — Update doc and lock in

Goal: capture every refinement from Phase 4 and present the locked doc for implementation.

Rewrite the doc incorporating walkthrough refinements. Full rewrite via `Write` is fine when refinements are structural; targeted `Edit` when they're local. Summarize changes from the original draft in chat as a bullet list. Say *"say word when grug start implement"* and stop. Do not start coding until explicit approval.

Exit signal: user says "implement", "start", "go", "approved", "Code review complete", or similar.

## Design principles to apply

Apply these while drafting. They shape the design, not the doc structure.

### Deep modules where it fits

Prefer deep modules: a simple, stable interface hiding complex behaviour. `required_permission :reports` on a tool is a deep-module win — one-line interface, four enforcement layers hidden behind it.

When the design introduces a new abstraction, call out in the "Design rules" section whether it's deep (complex behaviour, narrow interface) or shallow (glue, config). Shallow is fine when the problem is shallow; reviewers will push back when a shallow interface leaks implementation detail that ought to be hidden.

Skip this check for pure refactor or pure config designs.

## Design doc template

Write to `docs/design/<kebab-name>.md`. Sections in order:

```markdown
# <Feature> — Design Doc

**Status:** Draft
**Author:** <name from AGENTS.md>
**Date:** <today, YYYY-MM-DD>
**Scope:** <paths touched>

## Summary

One paragraph. What and why, no how.

## Motivation

Two to four paragraphs. Concrete problems today. Cite examples.

## Non-goals

Bullet list. What this design explicitly does NOT address. Prevents scope creep in review.

## Background

Subsections as needed: existing <domain> today (with code snippet from the codebase); how <integration surface> works (cite gem file:line); how <related concern> is enforced elsewhere (cite policies/concerns).

## Design rules

Short bullets stating the invariants. Example: "one permission per tool", "universally available unless declared". These are the knobs reviewers will push back on.

## Design

Numbered subsections for each component.

### 1. <Core abstraction>
Code block showing the API.

### 2. <Helper / support layer>
Code block.

### 3. <Mapping table>
Table with every entity and its assigned value.

### 4. <Layer/filter points>
Subsections (A, B, C, D) for each enforcement point.

## Runtime behaviour matrix

Table with rows = user states, columns = what they observe. Catches edge cases the prose missed.

## Alternatives considered

Bullet per alternative. Name it, explain why rejected.

## Testing Decisions (optional)

Include when the design introduces a new testable surface. Skip for pure refactor, pure config, or when the user explicitly opts out. When included: describe what the test boundary is (external behaviour, not implementation detail); list which modules get tests; cite prior-art tests in the codebase so the reviewer sees the style expected.

## Open questions

Bullets. Things the reviewer needs to decide or verify.

## Appendix — affected files

Flat list of every file that will be read/modified/created. Makes the scope concrete.
```

Adjust sections to fit. Drop `Runtime behaviour matrix` if it's not user-facing.

## Interaction examples

### Good: user asks for research

```
user: Let's research how we can make app/tools have permissions.
grug: [dispatch explore subagent: "map permission enforcement across
      app/policies, app/controllers, app/tools; cite file:line per claim;
      find 2+ existing DSL patterns; check Pundit changelog for version
      in Gemfile.lock re: new DSL hooks; flag contradictions with user
      claim that tools have no auth today"]
grug: [subagent returns findings pack, ~15 file:line refs + 2 pattern paths
      + 1 changelog URL flagging a relevant v2.4 hook]
grug: [main context reads 3 load-bearing files to confirm hook shape]
grug: [findings reply: bullets, file:line, rough map, recommendation, open question]
user: flesh out design doc
grug: [writes docs/design/tools-permissions.md]
grug: doc at <path>. <3-line summary>. walk through step-by-step?
user: yes
grug: ## Step 1 — the problem
      ... ready for step 2?
user: y
grug: ## Step 2 — <...>
```

### Bad: research in main context

```
user: Let's research how we can make app/tools have permissions.
grug: [greps 40 files, reads 18 of them directly in main context]
grug: [findings reply]
```

Wrong. Main context now carries 18 files of detail that subagent would have summarised to 15 bullets. Later phases degraded. Dispatch first, read only load-bearing files after.

### Good: mid-walkthrough pushback

```
grug: ## Step 4 — the DSL ...
user: seems correct. however I think search_* maybe also need. not sure if YAGNI
grug: [reconsiders, sharpens rule, updates mapping in chat]
grug: ... want grug update doc now or keep momentum?
user: keep momentum
grug: ## Step 5 — permission map (updated) ...
```

### Good: lock-in handoff

```
user: Code review complete. No changes requested.
grug: noted. doc locked in. say word when grug start implement.
```

### Bad: skipping phase 2

```
user: Let's research how to add X
grug: [immediately writes a 500-line design doc]
```

Wrong. Findings reply first, then doc. Doc might be completely wrong if an assumption is off.

### Bad: combining walkthrough steps

```
user: yes
grug: ## Step 1 — <...> ## Step 2 — <...> ## Step 3 — <...>
```

Wrong. One step per turn. User cannot push back when multiple steps arrive at once.

### Bad: starting implementation without lock-in

```
user: [reviews doc silently]
grug: [starts editing files]
```

Wrong. Wait for explicit approval.

## Anti-patterns

| Don't | Why |
|-------|-----|
| Write the doc before the findings reply | Assumptions may be wrong; wastes context |
| Research in main context when scope >3 files | Poisons main context with detail subagent would have discarded after summary |
| Skip dispatch because "grug can just grep" | Grep output clutters context; subagent grep + summarise keeps it clean |
| Accept prose findings from subagent | Need bullets + file:line; re-dispatch asking for structured pack |
| Skip web research when design hooks into third-party library | Installed version behavior may differ from grug's memory; cite doc + changelog |
| Web research for purely internal change | Noise; codebase is the source of truth for internal patterns |
| Combine multiple walkthrough steps | Prevents mid-walkthrough pushback |
| Drop to prose in the chat reply | Keep grug voice in chat; prose only inside the doc |
| Keep the rejected design in the doc | Move to "Alternatives considered" so the doc has one recommended path |
| Implement during walkthrough | Walkthrough is read-only. Implement after lock-in |
| Skip "Non-goals" | Without it, reviewers expand scope in PR review |
| Skip "Alternatives considered" | Without it, reviewers re-propose rejected options |
| Forget to update the doc after walkthrough refinements | Doc ends up contradicting the agreed design |

## Checklist

Before declaring the design doc done: Phase 1 dispatched to subagent (or direct-read path justified against the dispatch rule); subagent returned structured findings pack with file:line per local claim and URL + takeaway per web claim; web research ran when design hooks into third-party library (or skip justified for purely-internal change); main context read ≤5 load-bearing files flagged by pack; research phase cited file:line for every hook point used; findings reply posted and user responded before doc was written; doc saved at `docs/design/<kebab-name>.md`; doc has Summary, Motivation, Non-goals, Background, Design, Alternatives, Open questions, Appendix; walkthrough ran one step per turn; every accepted refinement from walkthrough applied to doc; summary of refinements posted in chat; waiting for explicit implementation approval before coding.
