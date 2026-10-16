# Survey

`/teammate survey [repo]` builds the product's first map: one page per repo, then one page for how they connect.
It is the one deliberately broad mode, so it runs one repo at a time and stops between them.

## Before starting

The product must have a `PROFILE.md`; if not, run onboarding first.
Read `INDEX.md` and skip repos already surveyed whose anchors are not stale, unless the user names one.
Pick the next repo: the one named, else the one most other repos depend on (shared schema, shared library, the API the clients call).

## One repo

1. **Orient inline**, cheaply: README, CLAUDE.md or AGENTS.md, CONTEXT.md, the manifest (`package.json`, `pyproject.toml`, `go.mod`, Terraform roots), top-level layout, ADR titles, `git log --oneline -15`, commit count.
2. **Explore** with `how`'s complex path: 2 to 4 angles chosen for this repo (for example entry points and request lifecycle; domain model and storage; integrations and boundaries; build, deploy and configuration). Each explorer gets `how/references/explorer-prompt.md`, run per `harness-bridge.md`.
3. **Draft the area page** in `knowledge.md`'s page shape, with these sections, dropping any that do not apply:
   - What it is and who uses it, in two or three sentences.
   - Main components and where they live.
   - Main flows, one line each, with entry points.
   - Boundaries: what it calls and what calls it, each with its contract.
   - Domain terms found, proposed for GLOSSARY.md.
   - Surprises and contradictions between docs and code.
   - Not yet mapped.
4. **Show the draft** and ask for approval through the store gate. Apply corrections the user gives before writing.
5. **Stop.** Offer the next repo. If the session has grown large, suggest continuing in a fresh session; the store carries the state.

## Connections page

Once every in-scope repo has a page, draft `areas/connections.md`: each boundary from the area pages, matched end to end by contract, with mismatches and dangling contracts listed.
This is the page later traces start from.
