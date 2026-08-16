<!-- Appended to the target repo's CLAUDE.md by /product-team:setup-strategy. Three lines on purpose: this file is loaded on every turn of every session in the repo, and the config it used to hold is read by eight skills that can open it when they run. Anything added here is paid for by every unrelated conversation. -->

## Product Team

This repo runs the Product Team pipeline: `/product-team:product-lead` for the guide and current status, `docs/strategy/product-team.yml` for the profile, gate medium, gate owners and roster.
Stage order is derived from the artifacts on disk (`pt.py status {slug}`), not from a maintained table; `docs/initiatives/{slug}/STATUS.md` records only gate decisions and kills.
Never merge a gate PR, edit an accepted ADR, invent a metric baseline, or delete an initiative folder.
