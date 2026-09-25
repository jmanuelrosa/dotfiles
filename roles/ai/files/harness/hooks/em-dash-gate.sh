#!/usr/bin/env python3
# vim: ft=python
# Filename keeps .sh extension to match the other hooks referenced from
# settings.json (hooks.PreToolUse) and symlinked into ~/.claude/hooks.
# The shebang is what determines execution.
"""em-dash-gate.sh - PreToolUse hook for Claude Code.

Blocks Write and Edit calls that INTRODUCE typographic dashes (em dash
U+2014, en dash U+2013). House style: regular hyphen or restructured
punctuation, never typographic dashes.

The check is delta-based so files that already contain these characters
stay editable: an Edit is blocked only when new_string carries more
dashes than old_string, a Write only when the content carries more than
the current file on disk.

The dash characters appear only as \\u escapes in this source so edits
to this file never trip the gate itself.

Fail-open on malformed input. Like git-skill-gate, this is
intent-friction, not a security boundary: the user can bypass by
editing in a terminal or disabling the hook in settings.json.
"""

import json
import re
import sys
from pathlib import Path

DASH_RE = re.compile("[\u2014\u2013]")

BLOCK_MESSAGE = (
    "This change introduces an em/en dash (U+2014/U+2013). House style:\n"
    "never use them. Rewrite with a regular hyphen, comma, colon, or\n"
    "parentheses, then retry. Dashes already present in the file may\n"
    "stay; only newly added ones are blocked."
)


def dash_count(text):
    return len(DASH_RE.findall(text or ""))


def resolve(file_path, cwd):
    path = Path(file_path)
    if not path.is_absolute() and cwd:
        path = Path(cwd) / file_path
    return path


def introduced_by_write(tool_input, cwd):
    new_count = dash_count(tool_input.get("content", ""))
    if new_count == 0:
        return False
    path = resolve(tool_input.get("file_path", ""), cwd)
    try:
        old_count = dash_count(path.read_text())
    except Exception:
        old_count = 0
    return new_count > old_count


def introduced_by_edit(tool_input):
    new_count = dash_count(tool_input.get("new_string", ""))
    return new_count > dash_count(tool_input.get("old_string", ""))


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_name = data.get("tool_name", "") or ""
    tool_input = data.get("tool_input") or {}
    cwd = data.get("cwd", "") or ""

    if tool_name == "Write":
        blocked = introduced_by_write(tool_input, cwd)
    elif tool_name == "Edit":
        blocked = introduced_by_edit(tool_input)
    else:
        blocked = False

    if blocked:
        print(BLOCK_MESSAGE, file=sys.stderr)
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
