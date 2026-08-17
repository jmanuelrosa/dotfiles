# Skill precedence

What wins when an installed skill contradicts the agent invoking it, or a checklist that agent is gated on.

A skill is expertise on loan.
It was written for a different host, against a different project, with no knowledge of the boundaries the caller agreed to.
The reasoning, the live contradictions this exists for, and the worked overrides are in `docs/internals/skill-precedence.md`.

## Tier 1, absolute: no skill grants permission

An ask-first boundary exists to route a decision to a human, and a skill sitting in the context window is not a human who approved it.
When a skill prescribes any of these, the result is a `needs-decision` naming the skill and the recommendation, **never an edit**:

- A dependency: a component, animation or icon library, an externally hosted or licensed web font.
- A new step in a system scale: spacing, type, color, motion, breakpoint, z-index.
- A brand-surface change: palette, typefaces, logo treatment.
- A raw value where the project has a token for it, or a whole parallel token system beside an existing one.
- A breaking change to a shared or published API.

This tier does not bend for confidence, for how well-regarded the skill is, or for how much better the suggestion is than what the project has.
Being right is what the recommendation is for.

One narrowing, and it is about scope rather than authority: where no prior decision exists to protect (no design system, no recorded direction, no tokens), the scale, palette and typeface gates have nothing to guard and inventing them is the brief.
Recording the choice is what arms the gate for the next brief.
The dependency and breaking-change gates never relax.

## Tier 2, defeasible: the reference is the default

Technique conflicts are not permission conflicts, and a blanket refusal here makes the agent worse rather than safer.

A reference's `Check:` is the default position, and a skill may override it **by naming the check it is trading against and satisfying it another way**, in the report.
Not by ignoring it, and not by being more specific about the technique.
An override that names no check is not an override, it is the skill winning by default, which is what this file exists to prevent.

## Output contracts are never a skill's to set

A skill may tell you how to think.
It does not get to set the shape of your final message.

A canned first-invocation greeting, a mandated review format, or an instruction to stop and await user input is void inside an agent that has its own completion-report contract, and the agent's contract wins with no exception.
A delegated agent has no user to await, so obeying that last one returns a greeting where the caller expected work.
`emil-design-eng` carries both today: read it for its motion technique, ignore its first-invocation and review-format mandates entirely.

## Reporting

A precedence call is a decision, so it goes in the report's decisions section in one line: what the skill wanted, which tier applied, and what you did.
Silent resolution is the failure mode.
A reader who cannot see that a conflict occurred cannot tell a considered override from an agent that never opened the checklist.
