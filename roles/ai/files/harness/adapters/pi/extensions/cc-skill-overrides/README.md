# Skill overrides

## Why it exists

Claude Code's `skillOverrides` setting decides how much of each skill the model sees, and pi has no counterpart.
Without it, the catalog's dependency-only skills (`grilling`, `domain-modeling` and the rest) were advertised to pi's model with their full descriptions while Claude listed them by name only, so the two harnesses picked different skills for the same prompt.
The `cc-` prefix marks it as a port of a Claude Code built-in.

## What it does

`harness-build` renders `generated/skill-overrides.json` from the same skill registry and override rules as Claude's `skillOverrides`, plus any `[skill_overrides]` in pi's `adapter.toml`.
Claude's own adapter entries name Claude's bundled skills and are not carried over.

On `before_agent_start` it edits the skill list pi builds the system prompt from:

| State | Effect in pi |
|---|---|
| `name-only` | Listed with an empty description |
| `user-invocable-only` | Not listed; `/skill:<name>` still works |
| `off` | Not listed, and a typed `/skill:<name>` is refused with a notice |
| `on` | Unchanged |

The model can still read a hidden skill's `SKILL.md` by path, as it can read any file.

## Verification

`lib/python/tests/test_pi_skill_overrides.py` runs the extension against stubbed pi events.
