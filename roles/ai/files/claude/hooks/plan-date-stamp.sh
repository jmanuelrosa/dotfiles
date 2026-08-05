#!/usr/bin/env python3
# vim: ft=python
# Filename keeps .sh extension to match the path referenced in settings.json
# (hooks.PostToolUse) and the symlink in ~/.claude/hooks. The shebang is what
# determines execution. Python matches the other hooks and avoids a jq
# runtime dependency.
"""plan-date-stamp.sh - PostToolUse hook for Claude Code, on ExitPlanMode.

Renames the approved plan file to carry the date it was finalized:

    docs/plans/right-now-we-save-glimmering-sun.md
    docs/plans/2026-08-05-right-now-we-save-glimmering-sun.md

Claude Code owns the plan filename (a slugified prompt prefix plus a random
word pair) and offers no setting to date it, so the repo can only rename after
the fact. ExitPlanMode is the moment to do it: the plan file is written and
edited repeatedly while planning, so renaming any earlier would break every
later Edit against the original path.

The path comes from the transcript rather than the event, because ExitPlanMode
takes no parameters at all: it reads the plan from the file and passes nothing.
Claude Code injects one authoritative record per plan session:

    {"type": "attachment", "attachment": {"type": "plan_mode",
     "isSubAgent": false, "planFilePath": "/abs/path/<slug>.md", ...}}

`planFilePath` is absolute, so no `plansDirectory` lookup is needed, and
`isSubAgent` states outright what a filename heuristic would only guess (a
subagent's plan carries an `-agent-<hash>` suffix, but the field is the fact).
The last such attachment wins, so re-entering plan mode retargets correctly.

Fail-open: any parse/IO error returns with no output (exit 0). The rename is
cosmetic, and losing it costs a date on a filename, while blocking here would
cost the user an approved plan.
"""

import json
import os
import re
import sys
from datetime import date
from pathlib import Path

DATED_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-")


def last_plan_attachment(transcript_path):
    path = Path(transcript_path)
    if not path.is_file():
        return None
    found = None
    with path.open() as f:
        for raw in f:
            try:
                event = json.loads(raw)
            except Exception:
                continue
            if not isinstance(event, dict):
                continue
            attachment = event.get("attachment")
            if isinstance(attachment, dict) and attachment.get("type") == "plan_mode":
                found = attachment
    return found


def target_name(name):
    return f"{date.today().isoformat()}-{name}"


def rename(attachment):
    """Return the new filename, or None when this plan is not ours to rename."""
    if attachment.get("isSubAgent"):
        return None

    plan_path = attachment.get("planFilePath") or ""
    if not plan_path:
        return None

    source = Path(plan_path)
    if DATED_RE.match(source.name) or not source.is_file():
        return None

    destination = source.with_name(target_name(source.name))
    if destination.exists():
        return None

    os.replace(source, destination)
    return destination.name


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
        attachment = last_plan_attachment(transcript_path)
        if attachment is None:
            return
        renamed = rename(attachment)
    except Exception:
        return

    if not renamed:
        return

    print(json.dumps({
        "systemMessage": f"📅 Plan dated: {renamed}",
        "suppressOutput": True,
    }))


if __name__ == "__main__":
    main()
