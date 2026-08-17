# Right-size the always-loaded context layer

## Context

A fresh session in this repo starts at 51.2k tokens before a single word is exchanged.
Of that, 11.9k is memory files and 4.5k is skill frontmatter, and both are re-read on every request for the life of the session.

An earlier pass (`docs/plans/2026-08-17-if-you-see-my-sleepy-flurry.md`) already moved 22k tokens of prose out of the project `CLAUDE.md` into `docs/internals/`, and it deliberately left `~/.claude/rules/*.md` alone on the grounds that `code-review.md` is "equally the bar for writing a diff".
That reasoning holds for part of the file and not for the rest: measured by bytes, 59% of `code-review.md` is review-*output* machinery (how to grade, how much to report, which tools not to touch, what `/code-review`'s first argument means) that cannot change a line of code being written.

There is a second problem the earlier pass did not look for, and it is arguably worth more than the tokens.
The always-loaded layer contradicts the current harness in one place and duplicates live hooks in three others, and Anthropic's Claude 5 context-engineering guidance names both patterns as the ones that make a model deliberate instead of act:

- Global `CLAUDE.md` says "Default to zero comments". The harness system prompt says, verbatim, "Write code that reads like the surrounding code: match its comment density, naming, and idiom."
- Attribution lines are blocked three times over: `git-skill-gate.sh`, the `attribution` setting in `settings.json` (both keys already empty), and the harness default.
- Em-dashes, lint and typecheck each have a live hook, and `code-review.md` itself says not to spend the context budget on what a hook already blocks.

Nothing routes `code-review.md` to `/code-review`.
A grep across every skill, agent and plugin returns zero references to the policy, its severities, or `~/.claude/rules/`.
`/code-review` is a Claude Code built-in that never reads the file; the policy applies only because it happens to be resident in memory.
That is why deferring any part of it needs an explicit routing stub rather than a silent move.

### Intended outcome

Memory files 11.9k to ~5.9k, skills 4.5k to ~4.0k, session baseline 51.2k to ~44.7k.
Roughly 6.5k tokens off every request for the life of every session, in every project, with no capability removed and every deferred artifact one invocation away.

## Change 1: split `code-review.md` by audience

`roles/ai/files/claude/rules/code-review.md` goes from 3.5k to ~1.4k.
The split line is whether a sentence can change code being written, not whether it is important.

**Stays always-loaded** (the local vocabulary and the safety boundaries, neither of which a model infers):

- The four severities as a table. Repo-specific, and the reason it exists is to collapse four rival dialects.
- The eight axes as a numbered list: name, severity, and only the clause carrying local knowledge. The generic explanation of what "correctness" or "security" means is cut, because that is exactly the judgment a Claude 5 model already applies.
- The nit cap, in one line.
- "The reviewer does not mutate", in one line. This is a safety boundary, so it must not depend on a skill being invoked first.
- The skip list (generated trees, vendored trees, `roles/ai/files/claude/skills/<upstream>`), in one line.
- A routing stub: producing an actual review report means invoking `review-mechanics` first.

**Moves to a new skill** `roles/ai/files/claude/skills/review-mechanics/SKILL.md`, loaded only when a review is actually being produced:

The verification bar in full, the effort table, seat routing, the skip rules with their rationale, the reporting format, the nit-discipline reasoning, and the full out-of-scope mutator list.

`docs/internals/code-review-policy.md` is unchanged and stays the "why" layer.

### Test coupling, and it is the real work here

`lib/python/tests/test_review_policy.py` reads `POLICY` (line 42) directly for six things that this change relocates: the seat-routing regex (line 143), the banned mutators (line 156), the literal `/code-review --fix` (line 162), every effort level (line 192), and the superseded reviewer name (line 197).
All six fail on a naive move.

Add `MECHANICS = SKILLS / "review-mechanics" / "SKILL.md"` beside `POLICY`, then repoint each assertion at the file that now owns the claim.
The severity test (line 139) keeps pointing at `POLICY`, because those staying resident is the thing worth guarding.
Add one new test asserting the stub in `POLICY` names `review-mechanics`, so the routing cannot rot silently.

Register the skill in `roles/ai/files/claude/skill-registry.json` under `local_skills` with the `global` group, matching the shape of the existing `cc-review` entry, so `claude-kit sync` links it into `~/.claude/skills/`.

## Change 2: global `CLAUDE.md`, 2.4k to ~1.4k

`roles/ai/files/claude/CLAUDE.md`.

- **Delete the attribution rule outright.** Triple-covered, and both `attribution` keys in `settings.json` are already empty strings.
- **Cut the em-dash rule down to one line scoped to chat.** Correction worth noting before this lands: `em-dash-gate.sh` is registered against `matcher: "Write|Edit"` (`settings.json:257-262`), so it covers files and not conversational output. Deleting the rule entirely, as chosen, would leave chat unguarded. Keeping one short line for the surface the hook cannot see preserves the intent of the cut and closes the gap; say so if you would rather drop it completely.
- **Keep "default to zero comments" as a single line**, and delete the paragraph around it about earning its place and the matching JSDoc bar. The conflict with the harness default stays, but becomes cheap and deliberate rather than a paragraph the model has to weigh.
- **Cut "complete code only: no TODOs, placeholders, or stubs"** and the `.editorconfig` / `printWidth` paragraph. Both are Claude 5 default behaviour.
- **Keep the semantic-line-breaks rule**, which is not default behaviour, in one line.
- **Compress `Tools & CLIs`.** The CLI table stays as-is: it is dense and it fires constantly. The ctx7 paragraph keeps its trigger sentence and loses the id-selection mechanics; the `glab` multi-host recipe pointer and the package-manager rule each collapse to one line.
- **Delete the `acli` sandbox paragraph.** Its own last sentence says the detail lives in the `jira` skill's Auth check section, so it is pure duplication.
- **Keep branch naming and the denied-operations line** verbatim. Neither is inferable.

## Change 3: project `CLAUDE.md`, 3.7k to ~2.2k

`## Architecture` is 6,404 bytes, the single heaviest section in the always-loaded layer.
The guidance is to spend tokens on gotchas and not on what the tree already says.

Keep, because each is a trap that costs a wrong change: profiles gate roles, Homebrew is per-role with no central list, playbook order is load-bearing and `meta/main.yml` deps are banned, configs are symlinks so edits apply without a re-run, idempotency is mandatory, and the lint exclusions are conscious.

Cut or compress: the `roles/<name>/` directory tree (an `ls` answers it), the brew `trusted` key paragraph (narrow, belongs with the role), and `Roles of note`, which is orientation prose rather than a gotcha and compresses to a short table.
Trim the vault and become-password prose above the Makefile table to one line; the table itself stays.

The `docs/internals/` routing table stays exactly as it is. It is already the pattern this whole plan is applying.

## Change 4: `skill-precedence.md` 1.5k to ~0.5k, `context-hygiene.md` 0.9k to ~0.4k

`skill-precedence.md` keeps the Tier 1 permission gates in full, because they exist to route a decision to a human and must not depend on a skill being loaded.
The Tier 2 principle collapses to its one-sentence rule.
The worked-example table, the scope narrowing, the `emil-design-eng` specifics and the reporting paragraph move into the existing `docs/internals/skill-precedence.md`.

`context-hygiene.md` keeps the actionable bullets and the 35% handoff threshold.
The measurement statistics and the entire `When the task is itself about cost` section move to `docs/internals/context-hygiene.md`, which already exists and already holds the derivation.

`lib/python/tests/test_design_direction.py:237-250` asserts on `skill-precedence.md` body text and needs updating in the same commit.

## Change 5: prune three project skills, ~0.5k for no authoring

`.claude/skills/node`, `.claude/skills/performance-optimization` and `.claude/skills/idea-refine` are project-scoped links in an Ansible repo with no Node.js, no application to profile, and no ideation surface.
`node` alone carries an 834-character description, ~280 tokens of always-loaded frontmatter.

Remove all three from this project with `claude-kit remove`, which is reversible with `claude-kit add`.
Do not edit `node`'s description in place: it is a vendored upstream skill and `claude-kit update` would overwrite the edit on the next sync.

This is Change 3 of the earlier plan applied to this repo, which that plan scoped but did not execute here.

## Expected effect

| Artifact | Now | After |
|---|---|---|
| `rules/code-review.md` | 3.5k | ~1.4k |
| project `CLAUDE.md` | 3.7k | ~2.2k |
| global `CLAUDE.md` | 2.4k | ~1.4k |
| `rules/skill-precedence.md` | 1.5k | ~0.5k |
| `rules/context-hygiene.md` | 0.9k | ~0.4k |
| three project skills | ~0.5k | 0 |
| `review-mechanics` frontmatter | 0 | ~0.05k |
| **Session baseline** | **51.2k** | **~44.7k** |

Roughly 6.5k off every request. The larger remaining term is still session length, which is Change 4 of the earlier plan and needs no code.

## Verification

1. `make test` passes, specifically `lib/python/tests/test_review_policy.py` and `test_design_direction.py`.
2. Confirm the relocated claims are genuinely still guarded, rather than the tests having been loosened: temporarily delete the effort table from the new `review-mechanics` skill and confirm `test_the_policy_documents_every_effort_a_call_site_could_name` fails.
3. `make check-role ROLE=ai` dry-runs clean. No Ansible task changes, since `rules/*.md` is globbed and the new skill is registry-driven.
4. `claude-kit sync` then `ls -l ~/.claude/skills/review-mechanics` resolves, and `~/.claude/rules/` still holds exactly three `.md` symlinks.
5. Fresh session in this repo, run `/context`: memory files should read ~5.9k against 11.9k today, baseline ~44.7k against 51.2k.
6. Behavioural check, the one that matters most: run `/code-review medium` on a real diff and confirm the report still uses the four severities, respects the nit cap, and names an effort level. If the model produces a review without invoking `review-mechanics`, the routing stub is too weak and needs strengthening before this is considered done.
