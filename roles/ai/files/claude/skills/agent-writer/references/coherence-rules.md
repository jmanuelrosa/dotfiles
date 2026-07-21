# Coherence rules

When to read: while authoring the pair, and again when briefing the audit subagent.
Every rule here was a real audit finding once; apply them during writing, not as a cleanup pass.

## Trigger tables are one artifact in two renderings

The agent's Step 3 table and the skill's SKILL.md router cover the same domains, in the same order.
The agent names each domain in bare form (`api-design`); the skill router links it (`[references/api-design.md](references/api-design.md)`), and every linked file exists on disk with exactly that name.
The "a typical <discipline> brief fires at least..." example names the same domains in both.
The safest workflow is to fix the domain list once, then render it the two ways and never add a domain to one without the other.

## Annotation breadth

A reference escalation line may claim "(also an ask-first boundary in the agent)" only when the agent's ask-first tier really contains that boundary, at the same breadth.
"Adding a new base image" annotated as ask-first is wrong when the agent's boundary says "adding a third-party action, orb, plugin, or base image": widen the reference wording or drop the annotation.
If the sibling agents all carry a boundary the new agent lacks, add the boundary to the agent rather than dropping the annotation.

## Never vs ask-first: approval must not unlock the forbidden

An ask-first item the caller could approve must never authorize what the never tier forbids.
The reliable framing is execution vs authorship: authoring a plan, a migration file, or an exact command for a human is ask-first; executing against production, shared environments, or protected data is never, and no approval reaches it.
Test each ask-first row by asking: if the caller says yes, what may the agent now do, and is any of that in the never tier?

## References must not contradict themselves

A reference must never escalate what its own Check treats as routine implementation.
If the check says pinned-version upgrades are explicit-diff routine, the escalation trigger cannot be "adding or changing a base image"; narrow it to what is genuinely a decision ("adding a new base image or switching to a different one").

## Advisor seats: hard rules outrank checks

For read-only seats, no reference check may require an action the hard rules forbid: no installs, no network calls against targets, no exploitation to "verify".
A check that cannot be satisfied read-only routes to the Not assessed section with a named next step for a human.

## Fact-check domain claims

Checklists state falsifiable domain behavior, and a confident wrong claim ships to every future run.
The known trap classes: statistics (power, SRM, peeking), database engine behavior (lock levels, transactional DDL, CONCURRENTLY), Kubernetes rollout semantics (what actually allows zero pods), and security semantics (JWT, CORS, header effects).
The audit subagent's brief must name the seat's trap class explicitly and ask it to verify, not admire.
