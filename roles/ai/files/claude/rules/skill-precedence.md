# Skill precedence

What wins when an installed skill contradicts the agent invoking it, or a checklist that agent is gated on.

This is not hypothetical and it is not rare.
The craft skills routed to by the design, frontend, mobile and desktop seats carry roughly ten live contradictions against those seats' own failure-mode references, and they fire on ordinary briefs rather than edge cases.
Without a stated precedence the agent resolves each one silently, which is how a seat whose first hard rule is "never trade accessibility for aesthetics" ends up taking its review format from a checklist with no accessibility rows in it.

A skill is expertise on loan. It was written for a different host, against a different project, with no knowledge of the boundaries the caller agreed to.

## Tier 1, absolute: no skill grants permission

An ask-first boundary exists to route a decision to a human. A skill sitting in the context window is not a human who approved it, and a skill that recommends the thing the gate guards has not lowered the gate.

So when a skill prescribes any of these, the result is a `needs-decision` naming the skill and the recommendation, **never an edit**:

- A dependency: a component, animation or icon library, an externally hosted or licensed web font.
- A new step in a system scale: spacing, type, color, motion, breakpoint, z-index.
- A brand-surface change: palette, typefaces, logo treatment.
- A raw value where the project has a token for it, or a whole parallel token system beside an existing one.
- A breaking change to a shared or published API.

This tier does not bend for confidence, for how well-regarded the skill is, or for how much better the suggestion is than what the project has. Being right is what the recommendation is for.

**One narrowing, and it is about scope rather than authority.** Where no prior decision exists to protect (a project with no design system, no recorded direction, no tokens), the scale, palette and typeface gates have nothing to guard and inventing them is the brief. Recording the choice is what arms the gate for the next brief. The dependency and breaking-change gates never relax, because they cost the project something whether or not a system exists.

## Tier 2, defeasible: the reference is the default

Technique conflicts are not permission conflicts, and a blanket refusal here makes the agent worse rather than safer.
When a reference says motion runs on transform and opacity and a skill demonstrates a `clip-path` reveal, the reference is right about the risk and the skill is right that the technique has a place.

So a reference's `Check:` is the default position, and a skill may override it **by naming the check it is trading against and satisfying it another way**, in the report. Not by ignoring it, and not by being more specific about the technique.

Worked examples, all real:

| The skill wants | The check it must name | What satisfying it looks like |
|---|---|---|
| `:hover { transform: scale(1.05) }` | Hover motion that moves the target's hit area | Hover the element's edge, confirm no flicker loop, and say so |
| `:nth-child` stagger delays | Selectors coupled to DOM structure | The markup is generated and its order is semantic, stated in the report |
| A `filter: blur()` transition | Animating outside transform and opacity | Verified with CPU throttling, and the result recorded |

An override that names no check is not an override, it is the skill winning by default, which is what this file exists to prevent.

## Output contracts are never a skill's to set

A skill may tell you how to think. It does not get to set the shape of your final message.

Some skills carry instructions that are harness control flow rather than advice: a canned greeting to emit on first invocation and then stop, or a mandated output table with a "never do this" counter-example. Inside an agent with its own completion-report contract, these are void, and the agent's contract wins with no exception. The same applies to a skill that instructs you to stop and await user input: a delegated agent has no user to await, and obeying that instruction returns a greeting where the caller expected work.

`emil-design-eng` carries both today. Read it for its motion technique, ignore its first-invocation and review-format mandates entirely.

## Reporting

A precedence call is a decision, so it goes in the report's decisions section in one line: what the skill wanted, which tier applied, and what you did.
Silent resolution is the failure mode. A reader who cannot see that a conflict occurred cannot tell a considered override from an agent that never opened the checklist.
