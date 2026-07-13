# Alert routing and on-call

When to read: the brief or diff touches routing trees, receivers, severity labels, inhibition rules, silences, escalation policies, or on-call load.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Route tree that swallows alerts.** An alert matching no route, captured by an earlier broader route, or excluded by matchers on the root route (which must match everything) dies silently or lands on the wrong team with a green config check.
  Check: walk the new or changed alert through the routing tree top to bottom and name the receiver it reaches, mechanically with the stack's route-test tooling where it exists; a catch-all route exists and someone actually reads it.
- **Receiver that goes nowhere.** A route pointing at a decommissioned channel, an empty receiver, or a misspelled destination delivers to nothing.
  Check: every referenced receiver is defined, and its destination is verified against where the team actually looks, not where it looked last year.
- **Severity without a contract.** Severity values that do not map to a known response (page now, ticket, FYI) force every alert to be re-triaged from scratch at 3am.
  Check: new alerts use the project's existing severity ladder, and each value maps to the documented response expectation.
- **Inhibition that never matches or over-matches.** An inhibition rule with mismatched labels suppresses nothing; one with too-broad matchers suppresses the outage's own page.
  Check: for each inhibition rule, name a concrete alert pair it should and should not suppress, and verify the label equalities hold in both cases.
- **Silence without expiry or reason.** An open-ended silence outlives its incident and eats the next one.
  Check: any silence or mute rule in the diff carries an expiry and a written root cause; silencing without one is never yours to do (a never boundary in the agent).
- **Grouping that spams or hides.** Grouping too broadly folds fifty distinct failures into one notification; too narrowly, one incident sends fifty pages.
  Check: group keys match how responders think about the failure domain, and repeat and refresh intervals are deliberate choices.
- **Flapping alert routed to a pager.** A page that fires and resolves repeatedly trains its receiver to ignore it; alert fatigue is how real pages get missed.
  Check: anything routed to paging has a duration and grouping that make repeated delivery for the same episode impossible.
- **Paging load nobody counted.** Every new pager alert spends the rotation's attention budget; the SRE book's sustainable bound is at most two actionable incidents per 12-hour shift, and past it every page is triaged as probably-noise.
  Check: state the expected page frequency and that the receiving rotation is the right owner; unknown frequency escalates rather than defaulting to page.

## Escalation triggers (`needs-decision`)

- Changing paging destinations, escalation policies, or on-call schedules (also an ask-first boundary in the agent).
- Rerouting an existing alert to a different team or channel (also an ask-first boundary in the agent).
- Any change expected to materially increase page volume for a rotation.

## What good looks like

- Every alert provably reaches a named receiver a human watches; the catch-all stays empty in steady state.
- Severity forms a small documented ladder from page to FYI, applied consistently across the rule set.
- The rotation's page log shows only actionable, user-impacting pages; everything else arrives as tickets.
