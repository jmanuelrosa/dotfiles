# Memo template

Fill every section that applies to the mode; drop sections marked for other modes entirely (no empty headers). Keep the memo decision-oriented: someone who reads only the TL;DR and Next steps should know what to do.

```markdown
# Research: <topic>

| | |
|---|---|
| Date | YYYY-MM-DD (add `revised YYYY-MM-DD` when extending) |
| Mode | feasibility / code deep-dive / general investigation |
| Question | <the one-sentence core question> |
| Repos examined | <repo names, or "none"> |
| Requested by / source | <Jira key, Slack thread, Notion doc, or "direct ask"> |

## TL;DR

<Feasibility mode: **Verdict: Feasible / Feasible with caveats / Not feasible** (confidence: high/medium/low), then 2-4 sentences of why.>
<Deep-dive mode: the 2-4 sentences you'd tell a teammate about how this area actually works.>
<General mode: the recommendation and the one fact that drives it.>

## Context

<Why this question came up, in the requester's terms. Quote the source material briefly where it sharpens the question.>

## Current state

<How the relevant system behaves today, as read. Every claim cites `path:line` (or a URL for external facts).>

## Findings

<One subsection per sub-question.>

### <Sub-question>

- **Answer:** <direct answer>
- **Evidence:** <`path:line` citations / URLs>
- **Confidence:** high / medium / low
- **Assumptions:** <anything load-bearing that is not evidenced, or "none">

## Contradictions

<Where sources disagree (ticket vs code, doc vs behavior), stated plainly. Drop the section if none.>

## Proposed approach (feasibility mode)

<The recommended option first, then rejected alternatives with the one-line reason each was rejected. Name the seams: which components change, which contracts are touched.>

## Risks and open questions

<Bullets. An open question names who or what could answer it.>

## Rough effort (feasibility mode)

<A range, not a number, with the main driver of the spread.>

## Verification notes

<What the adversarial pass challenged and the outcome: claim -> challenge -> held / downgraded / corrected.>

## Sources

<Every source consulted: Jira keys, Notion page ids, PR/issue URLs, doc URLs, "Slack thread pasted by user (YYYY-MM-DD)". One per line.>

## Next steps

<What decision is needed, from whom, and the concrete follow-up (spike, ticket, PR) if the answer is yes.>
```
