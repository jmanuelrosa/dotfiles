# Skill aliases

## Why it exists

Pi reserves `/skill:<name>` for skills, while the shared workflow also uses the shorter Claude Code commands `/commit`, `/pr` and `/ship`, plus `/cc-fewer-permission-prompts`, the port of Claude Code's `/fewer-permission-prompts`.
Without real extension commands, those short forms would be sent to the model as ordinary text.

## What it does

`index.ts` registers `/commit`, `/pr`, `/ship` and `/cc-fewer-permission-prompts`.
The `cc-` prefix keeps the last one from colliding with the Claude Code built-in of the same name.
Each command resubmits the corresponding explicit Pi skill invocation with prompt expansion enabled and preserves any arguments.
When an agent is busy, the invocation is queued as a follow-up message.

## Verification

Command registration, argument forwarding, and busy-session delivery are covered by `lib/python/tests/test_pi_skill_aliases.py`.
