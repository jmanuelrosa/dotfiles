# Notebooks and reproducibility

When to read: the brief or diff touches analysis notebooks, ad hoc analyses, or any deliverable whose conclusion a human will act on.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Hidden kernel state.** A notebook that only produces its numbers because of out-of-order execution or a deleted cell's leftover variables.
  Check: restart the kernel and run top to bottom before calling any result final; the committed version is the clean run.
- **Unseeded randomness.** Sampling, splits, or simulation without a fixed seed makes the readout unreproducible; the next run quietly disagrees.
  Check: every stochastic step sets an explicit seed, visible in the notebook.
- **Unpinned environment.** Imports resolved against whatever the machine has today; months later the notebook errors or, worse, computes differently.
  Check: dependencies are pinned in the project's idiom (lockfile, environment file, inline requirements); name the gap in the report when no idiom exists.
- **Conclusion without provenance.** A number in the summary whose producing query, model version, or date range is nowhere stated; nobody can re-verify it.
  Check: every reported number cites the exact query, model, and data version or date range it came from, in the notebook itself.
- **Manual steps between cells.** "Download the CSV first" or a hand-edited intermediate file makes the notebook a narrative, not an analysis.
  Check: the notebook runs end to end from declared inputs; manual steps are eliminated or made explicit, loud failures.
- **Stale outputs committed.** Cell outputs from an older run than the committed code, so readers trust numbers the current code does not produce.
  Check: committed outputs come from the final clean-kernel run, or outputs are stripped per the project's convention.
- **Pasted, not produced.** Numbers hand-copied into cells or markdown from a console session; the notebook shows results its code never computed.
  Check: results flow from executed cells; a pasted number no cell can reproduce is treated as fabricated.

## Escalation triggers (`needs-decision`)

- A conclusion the brief needs that the available data cannot support at the stated confidence.
- Productionizing a notebook into a scheduled job or model: that is a modeling brief, propose it.
- Sharing an analysis that exposes row-level sensitive data beyond its current audience.

## What good looks like

- Restart-and-run-all is the definition of working; the committed artifact is the clean run.
- Every number traces to a query, a version, and a date range without asking the author.
- Anyone with warehouse access can rerun it next quarter and get the same answer, or a loud failure.
