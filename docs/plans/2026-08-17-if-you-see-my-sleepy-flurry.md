# Cut per-session context cost without losing quality

## Context

The weekly usage allowance was 35% consumed within a few days.
Measuring the transcripts in `~/.claude/projects/` for Aug 11-17 shows the cause is not a single expensive operation but a structural one: **every request carries 162k tokens of context on average**, across 2,580 requests.

| Metric | Measured |
|---|---|
| Requests | 2,580 |
| Cache reads | 395M tokens |
| Cache writes | 22M tokens |
| Output | 2.7M tokens |
| Avg context per request | 162k |
| Median session | 184 turns, starts 62k, peaks 186k |
| Sessions peaking above 150k | 9 of 17 |
| Weighted model mix | Opus 73%, Fable 15%, Sonnet 11% |

Cost here is the area under the context-growth curve, so it is driven by two terms: the baseline a session starts at, and how long a session is allowed to run before it resets.
Both are addressable without giving up any capability.

One caveat on the measurement: the 38 subagent runs record no usage in `~/.claude/tasks/`, so their cost is absent from these totals.
The real figure is somewhat higher than what is shown above.

## Intended outcome

Median session-start baseline from 62k to roughly 38k, and average carried context from 162k toward ~100k, with the same skills, agents and seats available.
Nothing is deleted that the transcripts show being used.

## Change 1: split `dotfiles/CLAUDE.md` into on-demand docs

`CLAUDE.md` is 91,538 bytes (~24.7k tokens) and loads on every turn in three checkouts (`dotfiles`, `dotfiles-product-team-pipeline`, `dotfiles-pi-settings`), which together were 26% of the week's requests.
Measured section sizes:

| Section | ~tokens | Destination |
|---|---|---|
| `### claude-kit` | 6,265 | `roles/ai/files/scripts/claude-kit/ARCHITECTURE.md` (beside its existing README) |
| `### The product-team plugin` | 3,956 | `docs/internals/product-team.md` |
| `### Seat plugins & the staff-engineer fleet` | 2,743 | `docs/internals/seat-plugins.md` |
| `### Skill registry & dependencies` | 2,369 | `docs/internals/skill-registry.md` |
| `### The code review policy` | 2,093 | `docs/internals/code-review-policy.md` |
| `### Script output style` | 1,576 | `docs/internals/script-output-style.md` |
| `### Acceptance criteria live on the branch` | 1,328 | `docs/internals/acceptance-criteria.md` |
| `### Workspace trust` | 757 | fold into `claude-kit/ARCHITECTURE.md` |
| `### Plan files are dated, and committed` | 645 | `docs/internals/plan-files.md` |
| `### Skill precedence` | 636 | `docs/internals/skill-precedence.md` |
| `### Where a test lives` | 456 | `docs/internals/testing-layout.md` |

What **stays** in `CLAUDE.md`: repository purpose, common commands, the Architecture subsections through `Roles of note`, Secrets, Conventions, plus a new routing table naming each `docs/internals/` file and when to open it.
Target: under 12,000 bytes (~3.2k tokens), a saving of roughly 22k tokens per turn in those three checkouts.

The content moves verbatim.
This is a relocation, not a rewrite: the prose is the design record and shortening it is a separate decision.

Two couplings to fix in the same commit:

- **`lib/python/tests/test_tv_cables.py:83`** scans `(REPO / "roles", REPO / "lib", REPO / "CLAUDE.md")` for retired `_claude_scope_*` names. Add `REPO / "docs" / "internals"` to that tuple, or the guard silently stops covering the moved prose.
- **Five internal anchors** (`#claude-kit`, `#script-output-style`, `#skill-registry--dependencies`, `#the-product-team-plugin` twice, `#workspace-trust`) become cross-file links to the new paths.

## Change 2: default to Sonnet in `roles/ai/files/claude/settings.json`

Opus is 73% of weighted spend and weekly limits weight it far more heavily than Sonnet.

- `"model": "opus"` becomes `"model": "sonnet"`.
- `"effortLevel": "high"` stays unchanged, as chosen.
- `fallbackModel` and `availableModels` stay as they are, so `/model opus` remains one keystroke away for design work.

Seat agents are unaffected: each pins `model: opus` in its own frontmatter precisely so a delegated implementation does not follow the session model.
That pinning is why lowering the session default costs nothing on the delegated path.

## Change 3: prune per-project artifacts against actual use

Every linked skill contributes its frontmatter to the system prompt; a seat plugin contributes both agent and skill frontmatter, roughly 1k tokens per seat.

The evidence, from all transcript history:

- **Skills invoked at all**: `commit` (102), `pr` (88), `feature-team` (14), `grill-me` (6), `research` (5), `product-lead` (5), `coderabbit` (5), then single-digit one-offs. Only 4 `Skill` tool calls fired this entire week, so the long tail is not being auto-invoked either.
- **Seats genuinely used**: qa (23), frontend (22), platform (18), backend (14), database (13), design (8), security (6), cloud (4), dx (3). Analytics (1) and sre (1) are near-dead.

So the seats are earning their place and must not be removed wholesale.
The waste is per project, where linked sets do not match the stack:

| Project | Linked skills | Seats actually dispatched there |
|---|---|---|
| `3bitslost/pickleballontime` | 35 | database, backend, qa, platform, frontend, design, security, dx |
| `dotfiles` | 17 | dx only (plus Explore / general-purpose / Plan, which are built in) |
| `personal/brick` | 37 | none recorded |
| `personal/email.md` | 34 | frontend, platform, design, qa |

Per repo, run `claude-kit list` and remove seats for disciplines the repo has no surface for (`cloud`, `sre`, `analytics`, `data` in a small SaaS), plus craft skills never invoked there (`ai-seo`, `copywriting`, `cro`, `seo-audit`, `composition-patterns` in `pickleballontime`).
Removal is reversible with `claude-kit add`, so the bar for cutting is low.

Leave `~/.claude/rules/*.md` in force.
`code-review.md` is 2.7k tokens and always-on by design, and its own header states it is equally the bar for writing a diff, so it is not review-only content that could be deferred to a skill.

## Change 4: session hygiene, the largest single term

This needs no code and is where most of the saving is.
The median session runs 184 turns and climbs to 186k with only 2 compactions across the whole week, meaning sessions ride the ceiling instead of resetting.

- `/clear` between unrelated tasks. A 184-turn session costs roughly 3-4x the same work split across four fresh sessions, because every later turn re-reads everything the earlier ones accumulated.
- Use the existing `handoff` skill to carry state across a `/clear` rather than preserving it by never clearing.
- Route file-finding through the `Explore` subagent instead of reading files into the main context. The `dotfiles` sessions already do this (14 Explore calls); `pickleballontime`, the single most expensive project at 27% of the week, made 3.
- The statusline already renders a context meter (`context [▓▓░░░░░░] 100k (19%)`). Treat 60% as the prompt to wrap up or hand off, rather than 95%.

## Verification

1. `make test` passes, with `test_tv_cables.py` still guarding the moved prose (confirm by temporarily inserting a retired `_claude_scope_` name into a `docs/internals/` file and seeing it fail).
2. `wc -c CLAUDE.md` under 12,000.
3. Open a fresh session in `dotfiles` and run `/context`: session-start baseline should read roughly 38-42k against the 85k measured today.
4. Open a fresh session in a pruned project and confirm the skills you actually use (`/commit`, `/pr`, `/feature-team`) still resolve, and that `architect` can still dispatch the seats listed in the table above.
5. `make check-role ROLE=ai` dry-runs clean, since the moved files change no Ansible task.
6. After a week, re-run the transcript analysis and compare avg context per request against the 162k baseline recorded here.

## Expected effect

- Baseline: 62k to ~38k median, ~40k saved per turn in the dotfiles checkouts.
- Carried context: 162k toward ~100k, driven mostly by Change 4.
- Combined, roughly a 40% reduction in tokens read, before counting the Opus-to-Sonnet shift, which reduces weighted allowance consumption by more than it reduces raw tokens.
