---
name: setup-review
description: Review my agent configuration for the harness this session is running in (user + project scope)
argument-hint: "[claude|pi]"
effort: medium
disable-model-invocation: true
---
Maintenance review of my agent configuration.

1. Determine which harness to review. An explicit `claude` or `pi` argument wins. Otherwise, `PI_SESSION_ID` set means pi; unset means Claude Code. State the detected harness and reviewer before delegating.
2. Delegate the review at BOTH user and current-project scopes:
   - Claude Code: `cc-staff-reviewer`
   - pi: `pi-staff-reviewer`
   The reviewer reports which scopes it found and what usage evidence was available.
3. Return the reviewer's report verbatim: prioritized P0-P2 findings, adoption opportunities, proposed new artifacts, action table, and highest-leverage next three moves.
4. If the report contains adoption opportunities or proposed artifacts, use the harness's structured multi-select question tool to ask which items to take. Give each item one option whose description states why and how in one line. Skip this step when there are no ASK items.
5. Apply only accepted items in this main conversation. Edit configuration directly; create skills or agents through the skill-writing skill. Most reviewed paths are symlinks into the dotfiles repo, so edit the owning file under `roles/ai/files/`, update its registry entry when needed, say where the change landed, and offer to commit there. Drop declined items without ceremony.

The reviewer never modifies files.
In this conversation, modify files only for items explicitly accepted in step 4.
