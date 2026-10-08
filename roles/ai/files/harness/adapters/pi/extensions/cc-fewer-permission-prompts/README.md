# cc-fewer-permission-prompts

## Why it exists

Claude Code ships `/fewer-permission-prompts`, which mines past tool calls for read-only commands worth pre-approving.
The shared port is the `cc-fewer-permission-prompts` skill, which edits `policy/permissions.toml` so every harness gets the rules from one place.
Pi only reaches skills through `/skill:<name>`, so without this command the short form would be sent to the model as ordinary text.

## What it does

`index.ts` registers `/cc-fewer-permission-prompts`.
It resubmits `/skill:cc-fewer-permission-prompts` with prompt expansion enabled and forwards any arguments.
When the agent is busy, the invocation is queued as a follow-up message.
The `cc-` prefix keeps the port from colliding with the Claude Code built-in of the same name.

## Verification

Registration, argument forwarding and busy-session delivery are covered by `lib/python/tests/test_pi_cc_fewer_permission_prompts.py`.
The miner itself is tested beside the skill, in `kura/catalog/skills/cc-fewer-permission-prompts/tests/`.
