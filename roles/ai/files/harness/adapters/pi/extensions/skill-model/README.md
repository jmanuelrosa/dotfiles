# Skill model

## In one sentence

A skill that declares `model:` runs on that model in pi too, after `redirects` translate it to a model pi can serve.

## Why it exists

Claude Code honours the `model:` field in shared skill frontmatter, but pi's skill loader drops it.
The catalog is shared with Claude Code, so its pins name Claude models (`opus`, `anthropic/claude-sonnet-5`) that pi has no auth for.
This extension makes the same frontmatter mean something in pi, without a second, pi-only declaration.

## What it does

### 1. Detect the skill

A pin starts on `/skill:<name>`, looked up through `pi.getCommands()`, or when the model `read`s any `SKILL.md` itself.
No `model:` key, or `model: inherit`, leaves the session alone.

### 2. Redirect, then resolve

If the lowercased spec is a key in `redirects` in `roles/ai/files/harness/adapters/pi/model-routing.json`, it is replaced by its target before any lookup.
Any spec can be a key, whether a bare alias or a `provider/id` from any provider.
The result resolves against `enabledModels` in declared order: an exact `provider/id` or id first, then the first id containing the spec.

### 3. Pin for one agent run

The resolved model is selected for the run, and the footer shows `<skill> on <model>` while the pin is live.
If nothing matches, or the model has no configured auth, a warning is shown and the session stays where it was.

### 4. Restore

When the run settles, the previous model and thinking level are restored, so the next prompt starts from the session model again.
This matches Claude Code, where the override applies for the rest of the current turn.
The pin is recorded as a session entry, so a reload or resume mid-pin still restores correctly.

### Unpinned runs

If the session's selected model is itself a redirect key, each agent run switches to its target and switches back when the run settles.

## Example

With this `model-routing.json`:

```json
"redirects": {
  "sonnet": "openai-codex/gpt-6-sol",
  "cursor/composer-2-5": "openai-codex/gpt-6-luna"
}
```

| Skill frontmatter | What happens |
|---|---|
| `model: sonnet` | Redirected, then pinned to `openai-codex/gpt-6-sol` for the run |
| `model: cursor/composer-2-5` | Redirected, then pinned to `openai-codex/gpt-6-luna` |
| `model: cursor/grok-4.6` | No redirect: pinned to Grok as declared |
| `model: gemini-9` | Matches nothing enabled: warning, session unchanged |
| `model: inherit` or no key | Runs on the session model |

## No automatic failover

A provider error, including a rate or spend limit, is left to pi's normal retry handling; the extension never switches models mid-run.
When a provider runs out, add a redirect for its model and the next run lands elsewhere.

## What it does not cover

Agent frontmatter pins are not routed here.
pi-subagents resolves them in the parent's preflight and throws on an unknown model before any child session exists, and local foreground children never load ambient extensions.
Agents take the same `redirects` through `subagents.agentOverrides` in pi's `settings.json`, which `make test` keeps in sync.
Refusing disallowed Cursor models belongs to [cursor-model-policy](../cursor-model-policy/README.md), not to this extension.

## Verification

Resolution, redirects, persistence and restoration are covered by `lib/python/tests/test_pi_skill_model.py` and `lib/python/tests/test_pi_model_routing.py`.
The routing policy is documented in `docs/internals/harnesses.md`.
