# Diagram Specification

## Intent

Give a project's documentation diagrams that are drawn from the code, filed by the question they answer, and kept true as the code changes.
The skill owns two moments: drawing one diagram for one documentation kind, and refreshing every diagram whose anchored files moved since it was verified.

## Scope

In scope:

- Mermaid diagrams written into Markdown pages under the repo's docs root, inside an anchor marker.
- draw.io sources on request, exported to SVG or PNG with draw.io Desktop's CLI, authored with the hosted draw.io MCP's XML reference and shape search.
- A scan that names stale, invalid and current diagrams, lints Mermaid blocks with the pinned `maid` and checks draw.io sources and exports, and a stamp that re-anchors them to HEAD.
- Reusing an investigation already in the session (`how`, `why`, `teammate`, a clean `.teammate/` page).

Out of scope:

- Editing application code, tests or configuration.
- Installing tools: draw.io Desktop comes from the ai role's casks, the draw.io MCP from the shared MCP inventory, and `maid` is fetched by `bunx`.
- Sending diagram content to any hosted service, including draw.io's `create_diagram`.
- Prose documentation beyond a two-line lead and a legend; that is `documentation-and-adrs` territory.
- Deciding a repo's docs layout: existing Diátaxis directories are used, never created.

## Users And Trigger Context

- Primary users: engineers documenting a product they work on, in Claude Code, Pi or Codex.
- Common user requests: "diagram the consent flow", "add a use case diagram for billing", "draw a reference diagram of the schema", "update the diagrams", "are the diagrams still right after this PR".
- Should not trigger for: charts of data (that is `dataviz`), UI mockups (Figma skills), a Miro board (`miro-code-explain-on-board`), an inline sketch in a chat answer (`how` and `teach` already draw those).

## Runtime Contract

- Required first actions: read `references/kinds.md` and `references/mermaid.md` (or `references/drawio.md`) for a draw; run `scripts/diagrams.py scan --lint` for a refresh or list.
- Required outputs: the page and line of each diagram touched, its anchor paths, and what is not verified; one status line per diagram on refresh.
- Non-negotiable constraints: code read-only; `sha` set only by `stamp`; dashed edges and a "not verified" list for every inference; a lint that could not run is reported as unavailable, never as a pass; no diagram content leaves the machine; one shell command per call.
- Expected bundled files loaded at runtime: `references/kinds.md`, `references/mermaid.md`, `references/drawio.md`, `scripts/diagrams.py`.

## Source And Evidence Model

Authoritative sources:

- The repo's code at HEAD, and `git log` over the anchored paths.
- Diátaxis for the four documentation kinds.
- Mermaid syntax as rendered by GitHub and GitLab.

Useful improvement sources:

- positive examples: diagrams a reviewer accepted without edits.
- negative examples: blocks that failed to render on the host, markers the scan reported invalid, diagrams that went stale without the scan noticing (too narrow `paths`).
- commit logs/changelogs: the stamps a refresh produced per PR.
- validation results: `scripts/tests/test_diagrams.py`.

Data that must not be stored:

- secrets
- customer data
- private URLs or identifiers not needed for reproduction

## Reference Architecture

- `SKILL.md` contains: the modes, the draw and refresh steps, the boundaries and the marker format.
- `references/` contains: per-kind guidance and page placement (`kinds.md`), Mermaid rules with examples (`mermaid.md`), the draw.io opt-in (`drawio.md`).
- `scripts/` contains: `diagrams.py` (`scan` with `--since`, `--lint`, `--only`; `stamp`) and its tests, which stand in a stub for `maid`.
- `assets/`: none.

## Validation

- Lightweight validation: `uv run scripts/quick_validate.py` from the skill-writer root; `make test` runs `scripts/tests`.
- Deeper validation: run `scan --lint` against a page with a known-bad block and confirm `maid` reports it; open a draw.io PNG export and check the layout.
- Holdout examples: none yet.
- Acceptance gates: the scan reports stale exactly when a commit or working-tree change touches an anchored path; `stamp` rewrites only the named marker.

## Known Limitations

- `maid` is a third-party parser, not Mermaid itself: a block it accepts can still fail on GitHub in a corner case, and it cannot judge legibility.
- The lint distinguishes a diagnostic from a failure to run only by exit code; a `bunx` fetch failure that exits 1 reads as a lint error whose `lint:` lines name the fetch.
- Globs in `paths` follow git's `:(glob)` pathspec, so `**` matches across directories but a brace pattern does not.
- A diagram spanning several repos anchors only the repo its page lives in; the other repos' parts are inferences unless read in the session.
- draw.io sources are maintained as XML; the lint checks that the export exists, not that it matches the current source, so a refresh always re-exports.

## Maintenance Notes

- When to update `SKILL.md`: a new mode, a change to the marker format, or a change in what is written where.
- When to update `SOURCES.md`: a new kind mapping, a Mermaid rule learned from a render failure, a decision reversed.
- When to update `references/evidence/`: when a reviewed diagram or a failed render is worth keeping as an example.
