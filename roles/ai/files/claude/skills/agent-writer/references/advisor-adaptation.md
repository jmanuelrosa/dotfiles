# Advisor adaptation

When to read: the agent is read-only and produces an assessment instead of a diff.
The shipped example is `security-staff-engineer.md` + `security-failure-modes/`; read that pair alongside this file.
Blindly applying the implementer template to an advisor seat produces nonsense; these are the locked swaps.

## What the failure modes mean

Implementer references list defects the agent might introduce.
Advisor references list what the agent might MISS across the assessed surface: every check reads as "rule out having missed X", verified by tracing code paths and configs, never by mutating anything.
Assessment-quality traps (stale-training-data claims, forwarding scanner output unverified, manufactured low-priority findings to look thorough, a critical finding buried mid-list) belong in the AGENT's red flags and rationalizations, not in the references: the references check the assessed system, the agent checks itself.

## Structural swaps

- **The intro sentence pair.** "Each item is a check." stays; the second sentence becomes "An item you could not verify goes in the Not assessed section; silence is never read as safety." (there is no `done` to block and no `needs-decision` status).
- **The escalation heading.** "Escalation triggers (report immediately)": conditions that interrupt or lead the assessment rather than queueing in the ranked list (a live secret, evidence of active compromise, an actively exploitable critical finding, the brief drifting out of the seat's scope).
- **Boundary tiers.** The seat keeps Hard rules instead of ✅/⚠️/🚫: a read-only seat has nothing to ask permission for, so do NOT manufacture an ask-first tier. Reference annotations say "(also a hard rule)" where relevant.
- **The report.** The seat keeps its own output contract (for security: posture header, threat-model table, ranked findings with owner routing, paved-path recommendations, Not assessed). It gains a "### Self-check" section, and does not gain "Decisions and trade-offs" or "Pending ask-first items": an assessor makes no implementation decisions.
- **The trigger table.** Grows out of whatever lens or scope section the seat already has; loop step 3 becomes "Open the failure-mode checklists". Byte-identical between agent and SKILL.md as usual.
- **Loop step 1.** Scope honesty replaces blast radius: state what the assessment can and cannot reach, and what the Not assessed section will therefore carry.

## The overriding coherence rule

No reference check may require an action the hard rules forbid: no installs, no network calls against targets, no exploitation to verify a finding.
A check that cannot be satisfied read-only routes to Not assessed with a named next step for a human.

## What must survive edits

Advisor frontmatter deliberately differs from the family: a `tools:` allowlist and a non-opus `model:` are identity, not drift.
The verification sweep explicitly confirms both lines survived, because style sweeps will try to normalize them.
Fixes always route to the owning implementer seat by name; nothing in the pair may position the advisor as a per-change gate if it was designed as a deliberate, on-demand seat.
