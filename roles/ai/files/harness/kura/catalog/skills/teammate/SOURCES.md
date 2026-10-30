# Teammate Sources

## Evidence

| Source | Authority and confidence | Contribution |
|---|---|---|
| User interview in the authoring session (2026-10-16) | Required behavior, high | Understanding over generation; read-only; five evidence labels; short-first answers; every moment of use; per-product sources and store; Claude Code, Pi and Codex; generic across products and companies; dependencies instead of copied text; deep upfront survey |
| Sibling `how/SKILL.md` and its explorer and explainer prompts (PStack, MIT, Lauren Tan) | Upstream contract as installed, high | Complexity split, 2 to 4 explorer angles, one explainer, mental-model output |
| Sibling `why/SKILL.md`, `references/epistemics.md` and source playbooks (PStack, MIT) | Upstream contract as installed, high | Code anchor before fan-out, one investigator per evidence category, gather versus conclude, confidence tiers, coverage map, Preserve / Change / Avoid / Risk |
| Sibling `teach/SKILL.md` (PStack, MIT) | Upstream contract as installed, high | Smallest complete answer first, no quizzes, build-up diagrams, narrowed `why` |
| Sibling `unslop/SKILL.md` (PStack, MIT) | Upstream contract as installed, high | Prose pass on every reply |
| Sibling `domain-modeling/SKILL.md` and `GLOSSARY-FORMAT.md` (Matt Pocock, MIT) | Upstream contract as installed, high | Glossary format and checking user claims against code |
| Matt Pocock `teach` (learning records), `wayfinder` (index, not store), `wait-what` (re-pitch) | Read upstream, not installed; patterns only | `learner.md`, `INDEX.md` gists with a "Not yet mapped" section, the repair rule |
| Addy Osmani `context-engineering` and `interview-me` (MIT) | Read upstream; patterns only | Retrieved content as untrusted evidence, explicit-yes approval semantics |
| Claude Code 2.1.300 docs and probes in the authoring session | Platform contract plus measurement, high | Skill `hooks` frontmatter; `${CLAUDE_SKILL_DIR}` does not expand in a hook command; skill hooks do not fire inside subagents or after a headless `--resume`; `Explore` and `Plan` carry no write tools |
| [dotfiles `docs/internals/harnesses.md`](https://github.com/jmanuelrosa/dotfiles/blob/main/docs/internals/harnesses.md) | Repository policy, high | Pi reads only `name`, `description`, `disable-model-invocation`; `PI_SESSION_ID`; Pi sandbox prompts on file-tool writes outside cwd; Codex has no subagent tool here |
| `skills/to-rfc/SKILL.md` | Local precedent, high | Wording for loading dependency skills by reading their files |

## Decisions and coverage

| Dimension | Decision |
|---|---|
| Artifact type | One skill with references, not several skills or custom agents: the core is a conversation with the user, and the dependencies already carry the investigation method |
| Reuse | Read `how`, `why`, `teach`, `unslop`, `domain-modeling` as installed; no copied text. Patterns from uninstalled skills are restated in our own words, not quoted |
| Invocation | User-only (`disable-model-invocation: true`) so it never takes over a coding session |
| Model pin | None: it inherits the session model, and its subagents follow the harness bridge |
| Generic | No product or company in the skill; everything product-specific lives in that product's `PROFILE.md` |
| Store | `<workspace root>/.teammate/`, unversioned and personal; never a public configuration repo |
| Write fence | Claude-only `ask` hook on Write, Edit and NotebookEdit outside `.teammate/`; ask, not deny, because a skill hook persists for the rest of the session |
| Subagents | `Explore` and `Plan` only in Claude Code, because the fence does not reach subagents |
