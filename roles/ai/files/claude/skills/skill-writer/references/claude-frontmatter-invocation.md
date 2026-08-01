# Claude Frontmatter And Invocation

Load this when the skill needs Claude Code-specific frontmatter or invocation control.

## Use this file for

- extra trigger metadata
- invocation visibility rules
- skill-scoped model or effort overrides
- path or shell activation controls

## Relevant fields

| Field | Purpose | Notes |
|-------|---------|-------|
| `when_to_use` | extra trigger context for Claude | additive only; keep trigger-rich language in `description` |
| `disable-model-invocation` | only the user can invoke | good for side-effect-heavy workflows |
| `user-invocable` | hide from `/` menu and let Claude invoke | good for passive background knowledge |
| `allowed-tools` | pre-approve tools while skill is active | provider-specific |
| `disallowed-tools` | remove tools from the pool while skill is active | provider-specific; use for an autonomous skill that must never call `AskUserQuestion` |
| `arguments` | named positional args for `$name` substitution | pairs with `argument-hint`, which only feeds autocomplete |
| `model` | skill-scoped model override | provider-specific |
| `effort` | skill-scoped effort override | provider-specific; see below |
| `context: fork` | run the skill in a forked subagent | provider-specific; pair with `agent` to pick the subagent type |
| `agent` | subagent type used when `context: fork` is set | provider-specific |
| `background` | with `context: fork`, `false` waits for the result in the invoking turn | provider-specific; defaults to `true` |
| `hooks` | hooks scoped to this skill's lifecycle | provider-specific |
| `paths` | glob-based activation limits | provider-specific; limits automatic loading, not the listing cost |
| `shell` | shell for `!` preprocessing | provider-specific |

## When to set effort

Effort defaults to the session level, which the user picked for their own turn rather than for this skill.
Set it whenever the skill's work is reliably cheaper or reliably deeper than an average turn, and leave it unset otherwise.

- `medium`: template-driven and mechanical, where the procedure carries the work and the model only fills it in. A commit-message or ticket-formatting skill.
- `high`: read-and-summarize, research, and review, where breadth matters more than depth.
- `xhigh`: multi-file implementation, design, and adversarial review.

Two things to know before setting it.
It is orthogonal to `model`: a `sonnet` skill still benefits from `medium`, because effort governs tool calls and total token spend as well as thinking.
`high` is the session default, so setting it explicitly changes nothing today; it is a pin, and its job is to stop the skill being dragged up when the session runs at `xhigh`, `max`, or ultracode.
And a thin dispatcher skill that immediately hands off to a subagent gets almost nothing from its own effort value, since the work happens at the subagent's level; set it there instead.

## Invocation rules

1. If Claude should not decide when to run the skill, set `disable-model-invocation: true`.
2. If deliberate metadata should document that Claude may select the skill, set `disable-model-invocation: false`.
3. If the skill is not a meaningful command for humans, consider `user-invocable: false`.
4. Keep trigger-rich language in `description` even if `when_to_use` is present.

## Cross-provider parity

For Codex, add `agents/openai.yaml` under the skill root. Match Claude's behavior with `policy.allow_implicit_invocation`: use `false` when `disable-model-invocation` is `true`, and `true` when it is `false`. The same file may include `interface.display_name`, `interface.short_description`, and an explicit `interface.default_prompt` that references the skill as `$skill-name`.

## Portability rule

When using Claude or Codex-specific fields, say why they are necessary and note that they are not portable Agent Skills behavior.
