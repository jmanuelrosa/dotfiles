# OWASP Cheat Sheets Specification

## Intent

Give every staff-engineer seat, the security advisor, and reviewers one place that holds every actionable recommendation of the OWASP Cheat Sheet Series as a read-only check, tagged with the seat that owns it.
The seats' own failure-mode checklists stay short gates; this skill is the exhaustive depth behind them, loaded one topic at a time.

## Scope

In scope:
- Every actionable recommendation of every sheet in the series, rewritten as a check with an owner seat and a source sheet.
- Framework-specific sheets kept apart in `stack-*` references.

Out of scope:
- Payload catalogs, attack walkthroughs, code samples, tool advertisements.
- Exploitation or live testing guidance; every check is performed by reading code, config, or a diff.
- Deciding whether a recommendation is adopted: dependency and breaking-change recommendations go to the caller as `needs-decision`.

## Users And Trigger Context

- Primary users: the staff-engineer seats whose bundles declare it in `requires.skills`, the security advisor seat, and reviewers.
- Common requests: "check this against OWASP", "harden this login flow", "what does OWASP say about JWT", a seat routing a brief that touches a security surface.
- Should not trigger for: general code quality, performance, or style work with no security surface.

## Runtime Contract

- Required first actions: match the surface against the trigger table and read only the files that fire.
- Required outputs: none of its own; the calling seat's report contract applies.
- Non-negotiable constraints: items owned by another seat are reported, not implemented; library or dependency recommendations escalate as `needs-decision`.
- Expected bundled files loaded at runtime: `SKILL.md` and one to four `references/*.md`.

## Source And Evidence Model

Authoritative source: the OWASP Cheat Sheet Series repository, `OWASP/CheatSheetSeries`, `cheatsheets/*.md`, at the commit recorded in `SOURCES.md`.

Data that must not be stored: secrets, customer data, findings about a specific project.

## Reference Architecture

- `SKILL.md`: the seat ownership table and the trigger table.
- `references/`: one file per topic (several sheets merged and deduplicated) and one `stack-*` file per framework family.
- `SOURCES.md`: snapshot commit, the sheet-to-reference map, and the refresh procedure.

## Validation

- Lightweight: `quick_validate.py` from skill-writer; every sheet in the snapshot appears in the `SOURCES.md` map; every reference is routed from `SKILL.md`; no em or en dashes.
- Acceptance: each reference keeps the item shape (bold rule, `Check:`, `Owner:`, `Source:`), and every owner is a seat named in the ownership table.

## Known Limitations

- A snapshot: sheets added or revised upstream after the recorded commit are not reflected until a refresh.
- Owner tags reflect the default seat split; a project with a different split routes by its own boundaries.

## Maintenance Notes

- Refresh: follow the procedure in `SOURCES.md`, re-extract only the sheets whose files changed since the recorded commit, and update the map.
- A new sheet goes into the existing topic file whose surface it shares; a new file only when no topic fits, with a new trigger row in `SKILL.md`.
- When a seat is added or renamed, update the ownership table and the owner vocabulary together.
