# Teammate Specification

## Intent and shape

`/teammate` is a read-only senior engineer for whichever product the session is in.
It answers how code works, why it exists, what happens end to end, where a change would start, and what a PR touches, and it labels every claim by the evidence behind it.
It teaches in conversation: a short mental model first, then the thread the user picks.
It writes nothing except, on an explicit yes, to that product's private `.teammate/` store.

It is one skill composed from five dependencies it reads as installed: PStack `how`, `why`, `teach` and `unslop`, and Matt Pocock `domain-modeling`.
None of their text is copied, so `make skill-drift` and `kura update --type skill` bring their changes in.

## Scope and invocation

- Global, user-invoked only: `/teammate <question>` in Claude Code, `/skill:teammate <question>` in Pi. It never loads itself into a coding session.
- Forms: a free question; `init` to set up or refresh the product's profile (root, repos, sources, approvals); `survey [repo]` for the first map of a product; `pr <number|url>`; `save`.
- First time in a product: `/teammate init`, then `/teammate survey`. Without a profile the teammate still answers, from code, in-repo docs and local git only.
- Works in any repo. Nothing about a product or company lives in the skill; each product's facts live in its own `PROFILE.md`.

Example questions:

- `/teammate how does request authentication work here?`
- `/teammate why do we retry this call three times?`
- `/teammate what happens when a user changes their plan?`
- `/teammate I need to change how invoices are numbered. Where do I start?`
- `/teammate pr 1234`
- `/teammate survey api`
- "that didn't land, simpler" as a follow-up

## Runtime contract

| Piece | File |
|---|---|
| Boundaries, routing, answer shape | `SKILL.md` |
| Five evidence labels | `references/evidence.md` |
| First run in a product, source detection, isolation | `references/profile.md` |
| Source staging and the commands PStack does not cover | `references/sources.md` |
| Cross-repo tracing | `references/trace.md` |
| Deep survey | `references/survey.md` |
| Store layout, anchors, staleness, approval gate | `references/knowledge.md` |
| Cursor mechanics per harness, named overrides | `references/harness-bridge.md` |
| Claude-only write fence | `scripts/write-fence.py` |

**Sources.** Detected per product on first run and approved by the user: forge (`gh`, `glab` on any authenticated host or SSH alias), tracker (`acli` once a key resolves, or forge issues), chat and file-store connectors, `ntn`, `sentry`, and in-repo knowledge.
Code, in-repo docs and local git need no approval; everything else stays unsearched until the profile turns it on.
A connector signed in to an account that spans several companies is still off by default per product.

**Knowledge.** `<workspace root>/.teammate/` holds `PROFILE.md`, `INDEX.md`, `areas/`, `topics/`, `GLOSSARY.md`, `learner.md` and private `evals/`.
Pages carry commit anchors and are re-checked with `git log <sha>..HEAD -- <paths>` on load, so stale knowledge is flagged instead of trusted.
Writes happen only on an explicit yes, as one proposed batch.
Promoting a page into a repo's own docs is a normal change the user makes.

**Read-only enforcement.**
In Claude Code the skill's `hooks` entry asks before any Write, Edit or NotebookEdit outside a `.teammate/` directory, and its subagents are only `Explore` or `Plan`, which have no write tools.
The hook asks rather than denies because a skill hook stays active for the rest of the session, including when the user moves on to their own edits.
In Pi and Codex the frontmatter is ignored, so read-only rests on the instructions and each harness's own prompts.

## Enabling integrations

- Forge and tracker: sign in with the CLI in your own terminal (`gh auth login`, `glab auth login`, `acli jira auth login --web`, `ntn login`). The next onboarding detects them.
- Chat and file-store connectors: connect them in the client (for Claude, the claude.ai connectors; for Pi, `pi mcp login <server>`). A connector that needs sign-in is reported as unavailable, never signed in for you.
- Change a product's approved sources by editing its `PROFILE.md`, or ask the teammate to propose the change.

## Changing behavior

- Answer shape, boundaries and routing: `SKILL.md`.
- How a source is searched: `references/sources.md`, or upstream PStack's playbooks for method.
- A dependency's behavior: never edit the vendored copy. Override it in `references/harness-bridge.md` by naming the check traded against, per the skill-precedence rules.
- After a dependency update, re-run the acceptance cases; the bridge table is the part most likely to drift.

## Validation

Recorded below by date.
Automated means a headless `claude -p` run graded by a separate read-only agent against private ground truth; manual means a person read the transcript.
Cases ran on a real 9-repo product workspace; their targets and ground truth live in that product's private `.teammate/evals/`, never here.

**2026-10-16, round 1 (automated, 8 cases, one run per arm with and without the skill).**
With the skill: pass on simple explanation, historical reasoning, navigation, contradiction and unavailable integration; partial on the cross-repo flow, missing evidence and read-only safety.
Without the skill: failed navigation (missed the dependent in another repo), contradiction (picked a winner without reading the doc) and read-only safety (offered to apply a fix).
Defects found: dependencies loaded through a chained `ls` that failed silently, invented source gaps, tickets labeled as verified behavior, an unread cross-repo claim stated as fact, answers over the length cap, a turn ended while subagents still ran, and a side-effecting command run without asking.
With-skill cost was about 1.8 times the baseline.

**2026-10-16, round 2 (automated, same cases after fixes).**
Fixed: dependency loading by exact path, invented gaps, side effects, subagents finishing before the reply, and the cross-repo flow when the session starts at the workspace root.
New or remaining: a no-profile rule that also blocked the repo's own PRs and tickets (lost the real answer in the unavailable-integration case), a ground-truth file read through a workspace grep, answers at 279 to 345 words, a doc found but not read in the contradiction case, and two mislabels.
Each was addressed in the skill text the same day.

**2026-10-16, round 3 (automated, 5 cases plus `init`, with the skill).**
Fixed: forge and tracker reads without a profile, the ground-truth leak (no tool call touched it, subagents included), the doc found but not read, chained commands, and the profile lookup cost.
Pass on simple explanation, historical reasoning, navigation and the contradiction case; partial on missing evidence and `init`.
New or remaining: four of six replies over 300 words, a reason taken from a code comment labeled Verified, staged sources phrased as "couldn't" and an unprobed connector called "not authorized", a doc called outdated without checking history, the user's identity guessed from a path, `init` missing sibling repos because listing outside the session directory is blocked, and a PR comment read so large it spilled to disk.
Each was addressed in the skill text the same day.

**2026-10-16, round 4 (automated, same six cases).**
All six pass against ground truth, at about $0.42 to $0.66 a run.
Fixed: source phrasing, the outdated-doc guess, the identity guess, the Navigate case reading its tracker item and anchoring every repo, all three profile candidates read, and `init` (numbered root options, every sibling repo found with listing blocked, worktrees as views, Stage A on and Stage B off, one approval, no writes).
Remaining: five of six replies at 309 to 396 words against the 300 target; a code comment labeled Historical evidence instead of Documented intent; one run still fetched full PR comment bodies and spilled 436KB to disk; one gap line merged "not fetched" with "fetched and empty", fixed in text afterwards and not re-run.

**Onboarding (automated, three more product layouts: nested GitLab repos, a flat repo set with a knowledge repo, one product inside a mixed folder).**
No content from another product appeared, worktrees were recognized as views of their main repo, a docs contradiction was flagged, nothing was written, and each run offered to set up a profile.

**Interactive teaching (automated, three resumed turns).**
The repair turn re-explained the same facts more simply without re-investigating; the first two turns ran long, which led to the explicit length rule.

**Write fence (automated probes).**
Fires and asks in the main thread; does not expand `${CLAUDE_SKILL_DIR}`; does not reach subagents; not restored by a headless `--resume`.

**Pi (automated, one case).** Answer shape and labels held, but the sandbox blocked reading the skill's files because the test links pointed into a worktree outside Pi's read paths; to re-run once installed from the main checkout.

**Codex.** Not run: not installed.

## Known limitations

- `claude plugin eval` cannot exercise this skill: every run gets a temporary home and an empty workspace, so the dependencies, the real repos and the CLI sign-ins are all absent.
- In headless `claude -p` runs, `git` is sandboxed and cannot read `~/.gitconfig`, so acceptance runs disable the sandbox for the child and pass a read-only command allowlist.
- `${CLAUDE_SKILL_DIR}` does not expand in a hook command, so the hook path is built from `$HOME` and assumes the global Claude skills root.
- The write fence does not reach subagents and is not restored by a headless `--resume`.
- A session started inside one repo may not read its sibling repos; cross-repo traces need the session started at the workspace root or the siblings added to it.
- Codex is not installed on the authoring machine, so the Codex path is untested.
- The 300-word target for a first reply is not reliably held: four rounds of tightening brought replies to 295 to 396 words, not under 300.

## Future improvements

- Re-run the Pi cases once the skill is installed from the main checkout, and run the Codex cases once Codex is installed.
- Run each acceptance case several times per arm; one run each shows direction, not variance.
- Give Pi a write fence: a Pi extension hook that asks before writes outside `.teammate/`, so read-only stops resting on instructions alone there.
- A small read-only script that checks every store page's anchors at once, so a session reports staleness without one `git log` per page.
- Bring the with-skill cost (about 1.8 times the baseline in round 1) down by reading only the dependency sections a mode uses.
- Turn the private acceptance runner into a reusable one for skills that need the real workspace, since `claude plugin eval` cannot reach it.
