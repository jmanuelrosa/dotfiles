# Skill aliases

## Why it exists

Pi reserves `/skill:<name>` for skills, while the shared workflow also uses the shorter Claude Code commands `/commit` and `/pr`.
Without real extension commands, those short forms would be sent to the model as ordinary text.

## What it does

`index.ts` registers `/commit` and `/pr`.
Each command resubmits the corresponding explicit Pi skill invocation with prompt expansion enabled and preserves any arguments.
When an agent is busy, the invocation is queued as a follow-up message.

## Verification

Command registration, argument forwarding, and busy-session delivery are covered by `lib/python/tests/test_pi_skill_aliases.py`.
The cross-harness behavior is documented in `docs/internals/pi-harness.md`.
