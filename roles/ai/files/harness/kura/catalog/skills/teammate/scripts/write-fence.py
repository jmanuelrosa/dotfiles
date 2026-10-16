#!/usr/bin/env python3
"""PreToolUse fence for the teammate skill: writes outside a .teammate/ store need the user's say-so."""

import json
import sys
from pathlib import Path

STORE_DIR = ".teammate"
PATH_KEYS = ("file_path", "notebook_path")


def target_path(event):
    tool_input = event.get("tool_input") or {}
    for key in PATH_KEYS:
        value = tool_input.get(key)
        if value:
            return Path(value)
    return None


def inside_store(path):
    resolved = path.resolve(strict=False)
    return STORE_DIR in resolved.parts


def main():
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        event = {}
    path = target_path(event)
    if path is not None and inside_store(path):
        return 0
    shown = str(path) if path is not None else "an unknown path"
    decision = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": (
                f"teammate is read-only: {shown} is outside a {STORE_DIR}/ store. "
                "Approve only if you asked for this change."
            ),
        }
    }
    json.dump(decision, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
