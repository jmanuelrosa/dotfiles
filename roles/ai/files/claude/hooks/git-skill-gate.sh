#!/usr/bin/env bash
# git-skill-gate.sh — PreToolUse hook for Claude Code.
#
# Blocks direct `git commit` / `git push` invocations unless the current
# session has recently invoked the /commit or /pr skill. Failure modes
# fail open (allow) to avoid locking the user out on harness edge cases.

set -euo pipefail

WINDOW=150
ALLOWED_SKILLS_REGEX='^(commit|pr)$'
GATED_CMD_REGEX='^[[:space:]]*git[[:space:]]+(commit|push)([[:space:]]|$)'

input=$(cat)
command=$(jq -r '.tool_input.command // ""' <<<"$input")
transcript=$(jq -r '.transcript_path // ""' <<<"$input")

# Fast path: only gate git commit / git push.
if ! [[ "$command" =~ $GATED_CMD_REGEX ]]; then
  exit 0
fi

# Hard block --no-verify regardless of skill context. Both skills forbid
# it in prose; the gate enforces it so a slip can't reach git.
if [[ "$command" =~ --no-verify ]]; then
  cat >&2 <<'EOF'
--no-verify is blocked. Pre-commit hooks exist for a reason.
If a hook is failing, fix the underlying issue or disable the hook in
its own config — don't skip it.
EOF
  exit 2
fi

# No transcript → fail open so harness replay / compaction can't lock the
# user out. The user can still re-enable a hard block by editing settings.
if [[ -z "$transcript" || ! -r "$transcript" ]]; then
  exit 0
fi

# Scan the recent tail for a Skill(commit|pr) tool_use. The query is
# defensive against schema drift: anything missing → no match.
found=$(tail -n "$WINDOW" "$transcript" \
  | jq -rs '
      [ .[]
        | (.message.content // [])
        | (if type == "array" then .[] else empty end)
        | select(.type == "tool_use" and .name == "Skill")
        | (.input.skill // empty)
      ]
      | map(select(test("'"$ALLOWED_SKILLS_REGEX"'")))
      | length
    ' 2>/dev/null || echo 0)

if [[ "${found:-0}" -gt 0 ]]; then
  exit 0
fi

cat >&2 <<'EOF'
Direct `git commit` / `git push` is blocked outside the commit/pr skills.

Use:
  /commit   — stage and commit through the structured flow
  /pr       — push and open the PR/MR

To bypass for a one-off, the user can run the command in a terminal
or temporarily disable this hook in ~/.claude/settings.json
(hooks.PreToolUse).
EOF
exit 2
