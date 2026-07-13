# Verification sweep

When to read: after the audit fixes land, before the final message.
All checks must pass; a red check is fixed or reported honestly, never skipped.

## Checks

1. **Line budget.** The agent is <= ~205 lines and in family with the siblings:
   `wc -l roles/ai/files/claude/agents/*.md`
2. **No em or en dashes** in any touched file:
   `grep -rnP '[\x{2013}\x{2014}]' roles/ai/files/claude/agents/<seat>.md roles/ai/files/claude/skills/<seat>-failure-modes/`
   Must return nothing.
3. **Frontmatter parses under strict YAML** and uses `description: >-`; for advisor seats also confirm the `model:` and `tools:` lines survived:
   `awk '/^---$/{c++; next} c==1{print}' <file> | ruby -ryaml -e 'YAML.safe_load(STDIN.read)'`
   Run for the agent and the skill's SKILL.md.
4. **ansible-lint exits 0** (redirect output to a file; the spinner garbles inline capture):
   `ANSIBLE_LOCAL_TEMP="$TMPDIR/ansible-tmp" ansible-lint > "$TMPDIR/lint.out" 2>&1; echo $?`
5. **Both registries parse as JSON:**
   `python3 -c "import json; json.load(open('roles/ai/files/claude/skill-registry.json')); json.load(open('roles/ai/files/claude/agent-registry.json'))"`
6. **Dependency wiring is live:**
   `fish -c 'claude-agent list'` shows `<seat> (needs: <seat>-failure-modes)`.
7. **Trigger-table integrity** (belt and braces after the audit): every path in the agent's Step 3 table and the skill's router table exists on disk, and the two tables diff clean against each other.

## Final message contract

Report, in this order: what shipped with paths and line counts; research evidence adopted vs rejected; audit findings and how each was fixed; the verification results; `git status` output.
Remind the user nothing was committed: `/commit` is theirs to drive.

## Known environment quirks

Background researchers deliver via teammate messages, not TaskOutput; end the turn and wait.
`acli` and some tools run outside the sandbox; a sandbox-looking failure deserves one real attempt before being declared blocked.
Use `$TMPDIR` for scratch files, never `/tmp` directly.
