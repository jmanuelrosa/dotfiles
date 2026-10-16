# Harness bridge

`how`, `why` and `teach` were written for Cursor.
They are read as installed, never edited, and this file translates the parts that name Cursor mechanics.
Where a dependency and this file disagree on a mechanic, this file wins; on method, evidence and tone, the dependency wins.

## Which harness

An explicit `claude`, `pi` or `codex` in the arguments wins.
Otherwise `PI_SESSION_ID` set means Pi, and a session that offers the `Explore` and `Plan` agent types is Claude Code.
What decides the mechanics is whether a subagent tool exists in this session; if it does not, as in Codex, every spawn below runs inline.

## Loading the dependencies

SKILL.md's "Loading files" section gives the paths.
The dependencies are marked user-only upstream, so never try to invoke them through a skill tool and never type their slash command; reading the files is the invocation.
When `teach` says to "run `how` and `why`", that means read and follow those files.

## Mechanics

| A dependency says | Claude Code | Pi | Codex or no subagent tool |
|---|---|---|---|
| A `Task` subagent, `generalPurpose`, `readonly: true` (`how` explorers) | `Explore` agents with low effort, all spawned in one message | `Explore` through pi-subagents | Do each explorer's angle yourself, one after another |
| `readonly: false` so investigators keep MCP (`why`) | `Explore`: it keeps Bash and MCP tools and has no write tools | `Explore` | Inline |
| One explainer (`how`) or synthesizer (`why`) | `Plan` agent, which is read-only by its tool set, given the dependency's prompt template | Default subagent, told it is read-only | Inline |
| Model lines in `pstack-models.mdc` and Cursor model slugs | Ignore; leave the model unset | Ignore | Ignore |
| "List the available MCPs from the Cursor environment" | Use the product profile, then probe per `sources.md` | Same; Slack tools carry this harness's own prefix | Same; network commands may ask to leave the sandbox |
| A Linear, Datadog or Databricks example | The tool the profile names for that category | Same | Same |
| An image-generation tool | A series of mermaid diagrams, each adding one part | Same | Same |
| Cursor location, open files | The conversation, cwd, `git status` | Same | Same |

Subagents in Claude Code are always `Explore` or `Plan`, never `general-purpose`, because the write fence does not reach inside a subagent and those two have no write tools.
Spawn them in the foreground, never in the background, so the reply waits for their findings instead of ending on "they are still running".
Give each subagent the exact paths of the dependency prompt it needs, since it does not inherit this session's loaded files.
Every subagent prompt also carries three rules from SKILL.md, because a subagent does not see them: run each shell command alone, never chained or piped; never read or search `.teammate/evals/`; label anything not read in that run as Inference or Unknown.

## Overrides

Each override names the check it trades against and how that check is still met.

1. **`why` defaults to the full parallel investigation.** The check is a complete coverage map. Met by staging sources per `sources.md`, exactly as `teach` already narrows `why`, and listing every unsearched category in Sources Consulted with an offer to search it.
2. **`why`'s eight-section report and `how`'s "do not substantially rewrite" the explainer.** The check is that labels, citations and gaps survive presentation. Met by presenting the short-first shape from SKILL.md while keeping every evidence label, every gap and the confidence language unchanged, and giving the full report when asked.
3. **`domain-modeling` updates the glossary inline as terms resolve.** The check is that the shared vocabulary stays current. Met by proposing the entry inline the moment a term resolves and writing it through the store gate in `knowledge.md` on an explicit yes.

State an override in the answer only when it changed what the user sees, for example "Chat and docs not searched yet (staged)".
