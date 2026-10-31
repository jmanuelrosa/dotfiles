# Diagram Sources

## Evidence

| Source | Authority and confidence | Contribution |
|---|---|---|
| User request in the authoring session (2026-10-30) | Required behavior, high | Diagrams per documentation kind (use case, explanation, reference, how-to, tutorial); Mermaid or draw.io; drawn from the code the way `teammate` investigates; refreshed when a PR or feature lands |
| Diátaxis (diataxis.fr) | Public framework, high | The four kinds and the reader question each answers; `use-case` added as the pre-documentation kind the user named |
| Mermaid docs and the GitHub and GitLab Markdown renderers | Platform contract, high | The renderable subset: quoting rules, reserved ids, no init directives, `stateDiagram-v2` |
| Sibling `teammate/references/knowledge.md` | Local precedent, high | Anchoring a stored claim to a sha plus paths and checking staleness with `git log <sha>..HEAD -- <paths>`; the marker reuses that model |
| Sibling `teach/SKILL.md` (PStack, MIT) | Upstream contract as installed, high | A tutorial is a series of diagrams that each add one part |
| Sibling `how/references/explainer-prompt.md` (PStack, MIT) | Upstream contract as installed, medium | Draw only when parts interact or data changes shape; a diagram clarifies, never decorates |
| Sibling `ship/SKILL.md` and `pr/SKILL.md` | Local precedent, high | One context script per call, `KEY=value` sections for the model, allowed-tools shape, the pre-gate question |
| draw.io file format (`mxfile`, `mxGraphModel`) | Public format, medium | The uncompressed XML skeleton and the `.drawio.svg` export path |
| `jgraph/drawio-mcp` README (official) | Vendor docs, high | Hosted MCP at `mcp.draw.io/mcp` with `get_drawio_reference`, `search_shapes`, `create_diagram`; `create_diagram` returns a link in a terminal |
| `drawio --help` from draw.io Desktop 32.6.1, and an export trial in the authoring session | Installed CLI plus measurement, high | `--export`, `--embed-diagram`, `--border`; format from the output extension; export works inside the Claude sandbox with a harmless `sandbox_extension_issue_file` warning; the PNG opens in the file-read tool for a visual check |
| `probelabs/maid` README | Vendor docs, medium | Browser-free Mermaid lint, stdin with `-`, exit 0 clean and 1 on errors; not trialled here, the sandbox classifier refused to run it |
| [dotfiles `docs/internals/script-output-style.md`](https://github.com/jmanuelrosa/dotfiles/blob/main/docs/internals/script-output-style.md) | Repository policy, high | A model-facing script prints plain `KEY=value` text like `context.py`, not the `dotkit.ui` vocabulary meant for humans |

## Decisions and coverage

| Dimension | Decision |
|---|---|
| Class | `workflow-process`: preconditions (a git repo, a docs root), ordered draw and refresh flows, failure handling (invalid markers, unknown sha), safety boundaries (code read-only) |
| Execution shape | `argument-driven` over `script-backed-workflow`. Inline guidance was rejected because staleness detection is mechanical and fragile in prose; a router was rejected because the three modes share one contract and one script |
| Format | Mermaid by default: renders on GitHub and GitLab, diffs in review, redrawable without a tool. draw.io opt-in, with an embedded SVG (or PNG) export so the image renders on the host and stays editable in draw.io |
| Mermaid lint | `@probelabs/maid` pinned and run through `bunx` per block, over `@mermaid-js/mermaid-cli`, which validates by rendering in a bundled Chrome. `@zabaca/mermaid-validate` is the fallback if maid disagrees with GitHub |
| draw.io MCP | Hosted server in the shared inventory, so no install. Only `get_drawio_reference` and `search_shapes`, which send no repo content; `create_diagram` is banned because it uploads the diagram and the local PNG export covers the preview. The official drawio plugin was not adopted: it duplicates the export this skill already scripts |
| Where diagrams live | In the doc page they illustrate, inside a marker, not in a separate diagrams store: a block in a page is what renders, and the marker is what the scan needs |
| Anchors | `sha` plus `paths` per diagram, same model as the `teammate` store; `stamp` writes the sha so it is never hand-typed |
| Investigation | Standalone read-only investigation with `Explore` in Claude Code, reusing any `how`, `why`, `teammate` answer or clean `.teammate/` page already in the session; no declared dependency on `how`, whose Cursor subagent mechanics need the teammate bridge |
| Refresh trigger | `ship` and `pr` run `scan --since <base> --lint` before their gate and ask once when a diagram is anchored to files the branch changed or fails lint; the redraw itself stays in `/diagram refresh` because both skills run on haiku and are unattended after the gate |
| Invocation | User-only (`disable-model-invocation: true`): it writes docs |
| Portability | Script path differs per harness and is spelled out; the `Explore` fan-out is Claude-only and named as such |
| Retrieval stop | Diátaxis, Mermaid's renderable subset and the local anchoring precedent cover the five kinds; further sources would add diagram taxonomy, not behavior |

## Gaps

- `maid` was not run in the authoring session: the sandbox classifier refused unreviewed npm code. Its wiring is tested against a stub; the first real `scan --lint` is the live check.
- No holdout examples yet; collect the first accepted and the first broken diagram under `references/evidence/`.

## Changelog

- 2026-10-30: created.
- 2026-10-30: added the maid lint, draw.io export to SVG or PNG, and the draw.io MCP for the XML reference and shape search.
