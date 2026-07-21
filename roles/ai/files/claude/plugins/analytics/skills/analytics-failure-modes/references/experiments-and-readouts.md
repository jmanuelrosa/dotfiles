# Experiments and readouts

When to read: the brief or diff touches experiment design, launch or stop or extend decisions, readouts, or any significance claim a human will act on.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Unpowered by design.** An experiment launched without a power analysis cannot distinguish "no effect" from "too small to see"; the readout is predetermined to be ambiguous.
  Check: minimum detectable effect, required sample size, and expected runtime are stated before launch; presenting an unpowered readout as conclusive is a never boundary in the agent.
- **Sample-ratio mismatch ignored.** Assignment counts deviating beyond chance from the designed split mean randomization or logging is broken; every downstream number is untrustworthy however significant it looks.
  Check: an SRM check against the designed split runs before any metric is read; a failing check stops the readout and triggers investigation, not a caveat.
- **Peeking-driven stops.** Checking significance repeatedly and stopping on the first significant day inflates false positives far beyond the nominal rate.
  Check: the stopping rule is fixed before launch (fixed horizon, or a sequential design built for continuous monitoring); any stop or extend decision escalates with the statistical case, stating whether it falls inside or outside the rule.
- **Guardrails absent.** The success metric improves while an unmeasured guardrail (latency, unsubscribes, crashes, revenue) quietly degrades.
  Check: guardrail metrics are named at design time and reported alongside the success metric in every readout.
- **Multiple comparisons uncorrected.** Twenty metrics across ten segments produce significant results by chance alone; the winning segment is noise wearing a narrative.
  Check: primary metrics are declared in advance; secondary and segment results are labeled exploratory or corrected, never promoted to headline.
- **P-value without effect size.** "Significant" with an effect too small to matter, or an interval too wide to act on, misleads the decision.
  Check: readouts report the effect size with a confidence interval and state practical significance against the decision threshold, not just statistical significance.
- **Randomization and analysis units mismatch.** Randomizing by user but analyzing by session treats correlated observations as independent and understates variance; the significance is an artifact.
  Check: the analysis unit matches the randomization unit, or the variance treatment for the mismatch is stated.
- **Surprising result trusted.** Twyman's law: the most interesting number in the readout is the one most likely to be a data or instrumentation bug.
  Check: any outsized or unexpected result is traced through assignment, exposure, and metric computation before it is presented.
- **Pre/post delta presented as causal.** Without randomization, a before-and-after comparison carries seasonality, mix shift, and everything else that changed at the same time.
  Check: non-randomized impact claims name their identification strategy and its assumptions, or the readout is labeled descriptive, not causal.

## Escalation triggers (`needs-decision`)

- Launching, stopping, or extending an experiment: bring the statistical case, a human decides (also an ask-first boundary in the agent).
- Changing the primary metric, exposure definition, or segmentation after launch.
- A readout the brief wants stated more confidently than the data supports.

## What good looks like

- The design states hypothesis, primary metric, minimum detectable effect, sample size, runtime, guardrails, and stopping rule before launch; variance reduction (such as CUPED) is used where the platform supports it.
- Readouts lead with effect size and interval, name their power, and separate confirmatory results from exploratory ones.
- A powered null result is a valid, complete deliverable: report the interval it puts on the effect, never "proven no effect".
- A failed assignment check stops the analysis, whatever the p-value says.
