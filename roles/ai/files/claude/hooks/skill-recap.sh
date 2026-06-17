#!/usr/bin/env python3
# vim: ft=python
# Filename keeps .sh extension to match the path referenced in settings.json
# (hooks.Stop) and the symlink in ~/.claude/hooks. The shebang is what
# determines execution. Python matches the git-skill-gate.sh convention and
# avoids a jq runtime dependency.
"""skill-recap.sh — Stop hook for Claude Code.

When Claude finishes a turn, surface a one-line recap of which skills ran, e.g.

    🧩 Skills this turn: commit, humanizer

The recap is emitted as `systemMessage`, which Claude Code shows to the user but
does NOT add to the model's context — so this costs zero context. Crucially, the
output carries no `decision`/`reason`/`additionalContext`, so the turn ends
normally and nothing is fed back to the model. Turns that used no skill print
nothing (no noise).

Turn boundary: a user-submitted prompt and the tool results it spawns share a
`promptId`; assistant events carry none. So the just-finished turn is every
event from the first occurrence of the last user event's `promptId` through the
end. When no event carries a `promptId`, fall back to a recency window.

Skill signals (both top-level/known-good from git-skill-gate.sh and the Skill
tool):
  - `attributionSkill` — stamped on assistant events inside a slash-command flow
  - `Skill` tool-use blocks — `message.content[].input.skill` for skills the
    model invokes directly

Fail-open: any parse/IO error returns with no output (exit 0), so a malformed
transcript can never disrupt the turn or surface a stray message.
"""

import json
import sys
from pathlib import Path

FALLBACK_WINDOW = 40


def load_events(transcript_path):
    path = Path(transcript_path)
    if not path.is_file():
        return []
    events = []
    with path.open() as f:
        for raw in f:
            try:
                events.append(json.loads(raw))
            except Exception:
                continue
    return events


def current_turn(events):
    last_prompt_id = None
    for event in reversed(events):
        if event.get("promptId"):
            last_prompt_id = event["promptId"]
            break
    if last_prompt_id is None:
        return events[-FALLBACK_WINDOW:]
    for i, event in enumerate(events):
        if event.get("promptId") == last_prompt_id:
            return events[i:]
    return events[-FALLBACK_WINDOW:]


def skills_used(events):
    seen = []

    def add(name):
        if name and name not in seen:
            seen.append(name)

    for event in events:
        add(event.get("attributionSkill"))
        if event.get("type") != "assistant":
            continue
        content = (event.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if (
                isinstance(block, dict)
                and block.get("type") == "tool_use"
                and block.get("name") == "Skill"
            ):
                add((block.get("input") or {}).get("skill"))
    return seen


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    if not isinstance(data, dict):
        return

    transcript_path = data.get("transcript_path") or ""
    if not transcript_path:
        return

    try:
        skills = skills_used(current_turn(load_events(transcript_path)))
    except Exception:
        return

    if not skills:
        return

    print(json.dumps({
        "systemMessage": f"🧩 Skills this turn: {', '.join(skills)}",
        "suppressOutput": True,
    }))


if __name__ == "__main__":
    main()
