# Research: a first-class global code review policy (REVIEW.md and what actually works)

| | |
|---|---|
| Date | 2026-08-04 |
| Mode | feasibility |
| Question | Can we author one first-class `REVIEW.md` set globally, and how should it compose with the review skills and seat agents already in this repo? |
| Repos examined | `dotfiles` (this repo) |
| Requested by / source | direct ask |

## TL;DR

**Verdict: not feasible as asked, feasible in a better form** (confidence: high).

`REVIEW.md` is a **repository-root-only** file read by **one** consumer: Anthropic's hosted GitHub Code Review.
There is no `~/.claude/REVIEW.md`, no `.claude/REVIEW.md`, no hierarchy, and no `@` imports.
A global one would be read by nothing: the 2.1.220 binary on this machine contains **zero occurrences of the string `REVIEW.md`**, so the local `/code-review` has no code path for that filename at any effort level.
The hosted service is also out of reach today: it needs Owner or Primary Owner, and this account's `organizationRole` is `user`.

What *is* reachable, and is the better artifact anyway: the local review runs as a **fork** that inherits the full `CLAUDE.md` hierarchy plus `~/.claude/rules/`, and its own built-in prompt already treats "which CLAUDE.md rule is broken" as a first-class finding category.
So the policy belongs at **`~/.claude/rules/code-review.md`**, symlinked by the `ai` role from the loop that already ships `~/.claude/CLAUDE.md`.
Ship a condensed `REVIEW.md` **template** alongside it for the day the hosted service is enabled, and keep the two derived from one source rather than written twice.

## Context

The ask assumed `REVIEW.md` is the customization surface for Claude Code's review, settable globally, and that it should route to the review capability already here: `code-review-and-quality`, `code-simplification`, `performance-optimization`, and the 15 staff-engineer seats with their failure-mode checklists.
The routing instinct is right. The file is the wrong vehicle.

## Current state

**Review capability already in the repo** (`roles/ai/files/claude/`):

| Artifact | Global? | Reviewer-safe? | Axes it owns |
|---|---|---|---|
| `skills/code-review-and-quality` (`SKILL.md:26-86`) | no, per-project add (`skill-registry.json:85-93`) | yes, except its Dead Code Hygiene delete prompt (`:231-247`) | correctness, readability, architecture, security, performance; change sizing (`:105-113`) |
| `skills/code-simplification` (`:123-156`) | no (`skill-registry.json:75-83`) | **no, mutates** (`:157-170`) | nesting, long functions, naming, duplication, dead code, over-engineering |
| `skills/performance-optimization` (`:99-291`) | no (`skill-registry.json:95-103`) | steps 1-2 only; **3-5 mutate** | LCP/CLS/INP, TTFB, bundle, N+1, indexes, re-renders, caching, leaks |
| `skills/knip` | no | **no, `--fix` deletes** (`:100-110`) | unused files, deps, exports |
| `skills/coderabbit` | no | **no, edits and posts replies** (`:83`) | whatever CodeRabbit flagged |
| `agents/cc-staff-reviewer.md` | via `/cc-review` | read-only (`tools: Read, Glob, Grep, Bash, WebFetch`) | **Claude Code setup only** - "You do NOT review the project's application source code" (`:45`) |
| 15 seat plugins, `plugins/*/skills/*-failure-modes/references/*.md` | no, plugin install + workspace trust + restart | read-only checklists | 130+ checklists; `failure-visibility.md` in 11 seats, `errors-and-resilience.md` in 3 |

**Hooks already cover part of a review's job** (`settings.json:46-124`): `em-dash-gate.sh` blocks introduced em dashes on Write/Edit, `pre-commit-verify.sh` runs typecheck and lint before any commit, `git-skill-gate.sh` blocks `--no-verify` and attribution lines.
Spending review budget on those axes is wasted.

**No review config exists yet**: no `REVIEW.md`, no `codeReview` key in `settings.json`, no `ReportFindings` reference anywhere in the repo, and `git log -20 -- roles/ai/files/claude/` shows no prior attempt.

## Findings

### 1. What is the exact `REVIEW.md` contract?

- **Answer:** Root-only, single location, verbatim injection, no imports, one consumer.
  "`REVIEW.md` is a file at your repository root that overrides how Code Review behaves on your repo."
  "Claude auto-discovers REVIEW.md at the repository root. No configuration is needed."
  "Because it's pasted verbatim, `REVIEW.md` is plain instructions: `@` import syntax is not expanded, and referenced files are not read into the prompt."
  It is injected "into the system prompt of every agent in the review pipeline as the highest-priority instruction block".
  There is **no prescribed schema**: freeform markdown, with seven documented tuning axes (severity, nit volume, skip rules, repo-specific checks, verification bar, re-review convergence, summary shape). The one doc example uses `# Review instructions` / `## What Important means here` / `## Cap the nits` / `## Do not report` / `## Always check`, illustratively.
  Docs warn: "Length has a cost: a long `REVIEW.md` dilutes the rules that matter most."
- **Evidence:** https://code.claude.com/docs/en/code-review (#review-md, #customize-reviews, #example), https://support.claude.com/en/articles/14233555-set-up-code-review-for-claude-code
- **Confidence:** high
- **Assumptions:** none

### 2. Which surfaces read it, and can it be global?

- **Answer:** Only the hosted GitHub Code Review auto-discovers it. The local `/code-review` explicitly does not: "The review follows your `CLAUDE.md` like any Claude Code session, but it doesn't read `REVIEW.md`." Stated unconditionally, with no version, effort, `ultra`, or host qualifier.
  Confirmed independently against the binary: scanning all 256,908,272 bytes of `/opt/homebrew/Caskroom/claude-code@latest/2.1.220/claude` gives **0 matches** for `(?i)review\.md`, and no path-building or string-concatenation pattern. `reviewInstructions` exists in the binary but is never a file, it is the ultrareview plain-words note passed in memory.
  `ultrareview` docs never mention `REVIEW.md` (undocumented, not established either way). `/review <pr>`, `/security-review`, and the GitHub Action do not auto-discover it, though an Action `prompt` can be written to read it after `actions/checkout`.
  **Global is impossible**: no user-level or `.claude/` location exists in any source, and `memory.md` documents four `CLAUDE.md` scopes while never mentioning `REVIEW.md`.
- **Evidence:** https://code.claude.com/docs/en/code-review#what-the-review-reads-and-edits, https://code.claude.com/docs/en/ultrareview, https://code.claude.com/docs/en/memory, https://code.claude.com/docs/en/github-actions, `strings` over the installed 2.1.220 binary
- **Confidence:** high for the CLI (binary-verified), medium for `ultra` and `/security-review` (undocumented)
- **Assumptions:** that Anthropic's server-side pipeline does not probe non-root paths before falling back. Not verifiable from this machine; docs and support article both assert root-only.

### 3. Is the hosted service usable by this account?

- **Answer:** No, today. "Code Review is in research preview, available for Team and Enterprise subscriptions" and "You need the Owner or Primary Owner role in your Claude organization and permission to install GitHub Apps in your GitHub organization." This account reports `organizationName = Didomi`, `organizationRole = user`, `workspaceRole = None`.
  Also excluded for Zero Data Retention orgs. Cost is documented, not inferred: "Each review averages $15-25 in cost, scaling with PR size, codebase complexity, and how many issues require verification", billed as usage credits outside plan usage.
- **Evidence:** https://code.claude.com/docs/en/code-review, https://support.claude.com/en/articles/14233555-set-up-code-review-for-claude-code, non-secret `oauthAccount` fields in `~/.claude.json`
- **Confidence:** high on the role gate, medium on the plan tier (not exposed in readable non-secret fields)
- **Assumptions:** that Didomi has not enabled it on a repo you can reach. Worth one question to whoever owns the Claude org.

### 4. What does reach every local review, and does the built-in prompt leave room for a policy?

- **Answer:** Yes, and the built-in prompt actively invites one.
  A non-fork subagent's startup context includes "**CLAUDE.md files**: every level of the hierarchy the main conversation loads, including `~/.claude/CLAUDE.md`, project rules, `CLAUDE.local.md`, and managed policy files", and only Explore and Plan omit it. `/code-review` is stronger still: it "runs the review as a fork", and a fork "inherits the parent conversation instead of starting fresh".
  `~/.claude/rules/` is a documented, real mechanism: "Personal rules in `~/.claude/rules/` apply to every project on your machine", "Rules without `paths` frontmatter are loaded at launch with the same priority as `.claude/CLAUDE.md`", and "The `.claude/rules/` directory supports symlinks". This machine has none and the repo manages none.
  The built-in review prompt (extracted from the binary) hunts correctness first: "read every hunk, open the surrounding files for context as needed... and hunt for correctness issues - wrong or inverted conditions, off-by-one, null/undefined dereference, missing `await`, dropped error handling, removed guards or validations, broken callers of changed functions, races." And it already names our lever: findings should "state the concrete cost (what is duplicated, wasted, harder to maintain, or **which CLAUDE.md rule is broken**)... Correctness bugs always outrank cleanup, altitude, and conventions findings when the output cap forces a cut."
  `ReportFindings` is not gated on the bundled skill: "Claude calls it when active code-review instructions tell it to", with fields file, summary, failure scenario, and optional `category` slug. Effort is a `/code-review` argument, not a file concept: "At `low` and `medium`, the review reports only the findings it's most confident in... `high` through `max` cast a wider net."
- **Evidence:** https://code.claude.com/docs/en/memory, https://code.claude.com/docs/en/sub-agents, https://code.claude.com/docs/en/tools-reference, https://code.claude.com/docs/en/code-review#tune-effort-and-arguments, binary string extraction
- **Confidence:** high
- **Assumptions:** none

## Contradictions

- **Docs vs support article on layering.** The docs page says `REVIEW.md` takes "precedence over the default review guidance"; the support article says rules are "additive on top of the default correctness checks". Treat it as layered with override priority, and do not assume the built-in correctness pass disappears. This matters for authoring: do not restate correctness hunting, it is already there and outranks everything you add.
- **Severity vocabularies disagree across our own artifacts.** `code-review-and-quality:181-191` uses Required / Critical / Nit / Optional-Consider / FYI; `cc-review:13` uses P0-P2; `coderabbit:53` uses nitpick / warning; the hosted pipeline uses Important / Nit / Pre-existing, machine-readable as `{"normal": 2, "nit": 1, "pre_existing": 0}`. Four vocabularies for one concept.
- **A documentation bug worth knowing.** `commands` links `/review` to `code-review#review-a-pull-request` and `/security-review` to `code-review#review-for-security-issues`. Neither anchor exists, so there is currently no reference describing what `/security-review` reads.

## Proposed approach

Two artifacts from one source of truth. Reject the single global `REVIEW.md`, it cannot work.

**A. `roles/ai/files/claude/rules/code-review.md` → `~/.claude/rules/code-review.md`** (the one that works today)

Delivery already exists. `roles/ai/tasks/main.yml:55-66` is a hardcoded loop symlinking `settings.json`, `CLAUDE.md`, `statusline.sh` into `~/.claude/`; add `rules` to it as a linked directory.
`claude-kit sync` cannot prune it: `provision.py:115-120` iterates `scope.installed_names`, `scope.py:192-196` scans only `Path(root)/".claude"/leaf`, and `catalog.py:18` defines `LEAF` as `skills` / `agents` / `skills`. The scan never reads `~/.claude` top level, and a non-store link is not a candidate anyway (`scope.py:199`).
A rules file beats appending to `CLAUDE.md` on three counts: it keeps the 200-line `CLAUDE.md` intact, it is review-scoped rather than always-on prose, and `paths:` frontmatter is available later if you want per-language rules.

**B. `roles/ai/files/claude/templates/REVIEW.md`** (dormant, scaffolded per-repo)

A condensed derivative of A, ~40 lines, self-contained because it cannot import.
It earns its place two ways before the hosted service is enabled: a `claude-code-action` workflow whose `prompt` reads it, and being ready the day someone with Owner role turns Code Review on for a Didomi repo.

**Rejected:** a user-level skill named `code-review`. It would work, precedence is explicit ("A skill at any of these levels also overrides a bundled skill with the same name... personal overrides project"), but it *replaces* rather than wraps, forfeiting the tuned multi-agent finder pipeline, `ultra` routing, and `--fix` / `--comment` parsing. You would rebuild what Anthropic tunes.
**Rejected:** a scaffolded per-repo `REVIEW.md` alone, which is N copies still unread locally.
**Rejected:** hooks, which cannot inject instructions into a review.
**Rejected:** a git template dir, which misses every existing clone.

### The specification: eight ranked axes

Ranked, because the built-in prompt cuts from the bottom when the output cap bites. Each axis names its escalation and where deeper checklists live.

1. **Correctness and data integrity** - blocker tier. *Do not restate the built-in list;* state only what it cannot infer: which invariants this codebase relies on, and that a claimed bug needs a reproducing path through real callers.
2. **Contract and compatibility** - blocker tier. Public API and schema back-compat, migration ordering and reversibility, feature-flag and kill-switch presence, whether the change is rollback-safe. Deeper: `database/references/migrations-and-deploy-ordering.md`, `backend/references/api-design.md`. **Currently covered by no skill in this repo.**
3. **Security and privacy** - blocker tier. Secrets in the diff, authz vs authn confusion (IDOR), injection, PII handling and retention. Deeper: the 9 `security/references/*.md`. Escalate to `/security-review`, never fix silently.
4. **Failure visibility and operability** - important tier. Does a failure surface, with correlating identity? Swallowed errors, bare catches, logs without a request or tenant id. Deeper: `failure-visibility.md`, present in 11 of 15 seats, which is how central it is. **Covered by no skill here.**
5. **Test adequacy** - important tier. Assertion strength, not coverage percentage; whether the new failure mode is actually reachable by a test. Deeper: `qa/references/assertion-strength.md`, `flakiness-and-async.md`. **Covered by no skill here.**
6. **Performance and resource cost** - important tier, with a measurement bar: a performance finding needs a mechanism (N+1, unbounded fetch, missing index, re-render cascade), not a hunch. Defer optimisation to `/performance-optimization` **after** merge, since it mutates.
7. **Convention and repo fit** - nit tier unless it breaks a stated rule, then important. The diff-checkable rules from `CLAUDE.md`: no TODOs / placeholders / stubs (`:26`), zero comments unless a non-obvious WHY, same bar for JSDoc (`:27`), no ticket or ADR numbers in comments (`:28`), no hardcoded magic numbers / URLs / tokens / paths (`:31`), code wrapped to `.editorconfig` `max_line_length` then formatter config, never a reflex 80 (`:36`), semantic line breaks in prose (`:35`), package manager matches the lockfile (`:22`), ADRs superseded not edited (`:29`), plans in `docs/plans/` (`:30`).
8. **Simplification and dead weight** - nit tier, capped. Duplication, over-abstraction, altitude. Report, never apply: `/simplify` and `/code-simplification` mutate and belong to a separate pass.

### The five control clauses that make it a policy rather than a checklist

- **One severity vocabulary**, replacing our four: `blocker` (do not merge) / `important` (fix before merge or file it) / `nit` (capped, see below) / `pre-existing` (flagged once, never blocks). Maps onto `ReportFindings` `category` slugs and onto the hosted `{normal, nit, pre_existing}` scale.
- **Verification bar.** Every finding carries a `file:line` in the *source*, not an inference from naming, plus a concrete failure scenario: inputs or state, then the wrong output. This is not invented, `ReportFindings` requires `failure_scenario`. A finding that cannot state one is an opinion and is dropped.
- **Nit cap.** At most 3 nits per review, and zero when a blocker exists. The point is that a reader who skips nothing skips the whole report.
- **Skip rules.** Generated and vendored trees, lockfiles (writes are denied anyway, `settings.json:157+`), snapshots, and `roles/ai/files/claude/skills/<upstream>` trees, since `claude-kit update --type skill` replaces those wholesale and a finding there is discarded on the next sync. Do not report em dashes (`em-dash-gate.sh` blocks them at Write time), or lint and typecheck failures (`pre-commit-verify.sh` runs them at commit time). Duplicating a hook wastes the output cap.
- **The reviewer does not mutate.** Read-only, always: `code-simplification`, `knip --fix`, `coderabbit`, `pr`, `performance-optimization` steps 3-5, and `cc-review` step 5 all edit code and are named as out of scope during a review. Findings only; fixes are a separate, explicitly requested pass.

### Two clauses that need your call

- **Seat routing.** The 130+ failure-mode references are the best review knowledge here, but they live inside plugins requiring install plus workspace trust plus a restart, and they are namespaced `<seat>:<seat>-failure-modes`. A global rule can only say "if the seat is installed, open these"; it cannot rely on presence. The alternative is inlining the 20 highest-value `Check:` bullets into the rules file, which duplicates them and drifts.
- **Effort default.** `high` (this machine's `effortLevel`, `settings.json:24`) casts a wider net than `low`/`medium`, which report only high-confidence findings. Worth stating explicitly in the policy so a reviewer knows which bar applies.

## Risks and open questions

- **Rule files are always-on context.** Without `paths:` frontmatter a rules file loads at launch in every session, not only during a review. Keep it tight, and consider gating with `paths:` if it grows past ~100 lines.
- **The undocumented surfaces could change.** Whether `ultra` or `/security-review` read `REVIEW.md` is unstated; if a future release makes the local review read it, the recommendation shifts and the template becomes the primary artifact. The binary check is the canary: re-run the `REVIEW.md` string scan after a major upgrade.
- **Does Didomi already run hosted Code Review?** Only someone with Owner or Primary Owner in the Claude org can answer. If yes, `REVIEW.md` moves from dormant template to live artifact per repo.
- **Seven axis gaps have no owner even after this.** i18n, accessibility, licensing, and non-JS ecosystems (all our tooling is npm and knip) are named in no skill and would be prose-only in the policy.
- `.claude/state/` is not gitignored here. Your call whether to ignore or commit these memos; I have not touched `.gitignore`.

## Rough effort

**Half a day to a day and a half.** The spread is almost entirely the seat-routing decision: a rules file plus a template plus one line in `main.yml` is a couple of hours, and a `test_review_policy.py` asserting the rules file stays in the symlink loop and the axis list stays in sync with the seat references is the rest. Inlining checklists instead of routing to them roughly doubles it and buys drift.

## Verification notes

- *"`REVIEW.md` is root-only, no global variant"* → challenged by re-reading all doc pages, searching GitHub and the web, and scanning the binary → **held**, and strengthened: 0 matches for `(?i)review\.md` across the whole 2.1.220 binary, so there is no dynamic path construction either. One sub-clause **corrected**: precedence *is* documented, just not between `REVIEW.md` copies (it outranks default review guidance and merges with `CLAUDE.md`).
- *"The local `/code-review` does not read it, so it is useless locally"* → challenged for version and mode qualifiers → **first half held, second half refuted**. The built-in prompt makes "which CLAUDE.md rule is broken" an explicit finding category, so a local policy hook exists and is first-class. This flipped the recommendation from "author per-repo `REVIEW.md`" to "author a rules file".
- *"Hosted-only, Team/Enterprise, Owner role, $15-25"* → challenged → **partially holds**. Every gate is real and verbatim; the claim omitted *research preview*, overstated the GitHub App scopes (read on contents plus write on PRs is what the review uses), and "hosted-only" is wrong since a self-hosted Action `prompt` can read the file. The account's `organizationRole = user` was found here, which is the actual blocker.
- *"Delivery must be `CLAUDE.md`, `.claude/rules/`, or a skill"* → challenged, including a suspicion that `.claude/rules/` was stale in `cc-staff-reviewer.md` → **held and improved**. `~/.claude/rules/` is documented, symlink-supported, and reaches subagents. The refuter found the mechanism already ships (`main.yml:55-66` links `~/.claude/CLAUDE.md` today), and confirmed the pruning claim for a stronger reason than originally given: the scan is per-leaf-directory, so `~/.claude` top level is never read.

## Sources

- https://code.claude.com/docs/en/code-review (and the `.md` raw variant)
- https://code.claude.com/docs/en/ultrareview
- https://code.claude.com/docs/en/memory
- https://code.claude.com/docs/en/sub-agents
- https://code.claude.com/docs/en/skills
- https://code.claude.com/docs/en/commands
- https://code.claude.com/docs/en/settings
- https://code.claude.com/docs/en/tools-reference
- https://code.claude.com/docs/en/github-actions
- https://support.claude.com/en/articles/14233555-set-up-code-review-for-claude-code
- https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md
- `anthropics/claude-code-action` `action.yml` inputs
- Installed binary `/opt/homebrew/Caskroom/claude-code@latest/2.1.220/claude` (string extraction)
- This repo: `roles/ai/files/claude/CLAUDE.md`, `settings.json`, `skill-registry.json`, `roles/ai/tasks/main.yml`, `skills/{code-review-and-quality,code-simplification,performance-optimization,cc-review,coderabbit,knip,pr}/SKILL.md`, `agents/cc-staff-reviewer.md`, `plugins/*/skills/*-failure-modes/`, `roles/ai/files/scripts/claude-kit/claude_kit/{commands/provision.py,scope.py,catalog.py}`

## Next steps

Decisions needed from you, in order:

1. **Confirm the pivot**: `~/.claude/rules/code-review.md` as the live artifact, with `REVIEW.md` shipped as a dormant per-repo template. This is the only fork in the road.
2. **Pick the seat-routing option**: conditional routing by name (cheap, may point at an uninstalled seat) or inlined top-20 checks (self-contained, drifts).
3. **Ask whoever owns the Didomi Claude org** whether hosted Code Review is enabled, and on which repos. That decides whether the template is dormant or immediately live.

Then the build is: write the rules file against the eight axes and five control clauses above, add `rules` to the `main.yml:55-66` loop, write the condensed template, and add a test pinning the symlink entry and the axis list so neither silently rots.
