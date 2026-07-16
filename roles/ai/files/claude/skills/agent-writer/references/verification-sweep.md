# Verification sweep

When to read: after the audit fixes land, before the final message.
All checks must pass; a red check is fixed or reported honestly, never skipped.

## Checks

1. **Line budget.** The agent is <= ~205 lines and in family with the siblings:
   `wc -l roles/ai/files/claude/plugins/*/agents/*.md`
2. **No em or en dashes** in any touched file:
   `grep -rnP '[\x{2013}\x{2014}]' roles/ai/files/claude/plugins/<discipline>/`
   Must return nothing.
3. **Frontmatter parses under strict YAML** and uses `description: >-`; for advisor seats also confirm the `model:` and `tools:` lines survived:
   `awk '/^---$/{c++; next} c==1{print}' <file> | ruby -ryaml -e 'YAML.safe_load(STDIN.read)'`
   Run for the agent and the skill's SKILL.md.
4. **ansible-lint exits 0** (redirect output to a file; the spinner garbles inline capture):
   `ANSIBLE_LOCAL_TEMP="$TMPDIR/ansible-tmp" ansible-lint > "$TMPDIR/lint.out" 2>&1; echo $?`
5. **Packaging is valid.** For a seat plugin: `plugin.json` parses and validate passes (the `groups` warning is benign):
   `claude plugin validate roles/ai/files/claude/plugins/<discipline>`
   For a utility agent instead: both registries parse as JSON (`python3 -c "import json; json.load(open('roles/ai/files/claude/skill-registry.json')); json.load(open('roles/ai/files/claude/agent-registry.json'))"`).
6. **The seat is discoverable:**
   `fish -c 'claude-agent list'` shows `<discipline> (plugin) [groups]`, and `claude plugin details <discipline>@skills-dir` lists the bundled agent and skill. (A utility agent shows as `<name>`, with `(needs: <skill>)` if it declares one.)
7. **Trigger-table integrity** (belt and braces after the audit): every domain in the agent's Step 3 table has a reference file in the bundled skill and a matching row in the skill's router; the agent lists bare domain names, the router links them, and both cover the same domains in the same order.

## Final message contract

Report, in this order: what shipped with paths and line counts; research evidence adopted vs rejected; audit findings and how each was fixed; the verification results; `git status` output.
Remind the user nothing was committed: `/commit` is theirs to drive.

## Known environment quirks

Background researchers deliver via teammate messages, not TaskOutput; end the turn and wait.
`acli` and some tools run outside the sandbox; a sandbox-looking failure deserves one real attempt before being declared blocked.
Use `$TMPDIR` for scratch files, never `/tmp` directly.
