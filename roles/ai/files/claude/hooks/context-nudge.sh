#!/usr/bin/env python3
# vim: ft=python
# Filename keeps .sh extension to match the path referenced in settings.json
# (hooks.UserPromptSubmit) and the symlink in ~/.claude/hooks. The shebang is
# what determines execution. Python matches the skill-recap.sh convention and
# avoids a jq runtime dependency.
"""context-nudge.sh: UserPromptSubmit hook for Claude Code.

Past the wrap-up threshold in docs/internals/context-hygiene.md, say so:

    🧭 Context 41%: /handoff then /clear costs less than carrying this further

Cost is context size x number of requests, so every turn taken at 70% is paid
at 70% again on the next one. The status line already shows the percentage, but
an ambient gauge is not a prompt; this fires once per band so it reads as a
decision point rather than decoration.

Two audiences, deliberately priced differently:

  - `systemMessage` goes to the user. Claude Code shows it but does NOT add it
    to the model's context, so it costs zero tokens and is emitted on every
    turn above the threshold.
  - `hookSpecificOutput.additionalContext` goes to the model, and is charged on
    every subsequent turn of the session. So it is emitted only when crossing
    into a new 10% band, which is what makes the reminder affordable. It must
    be nested inside `hookSpecificOutput`; at the top level it is ignored.

Where the percentage comes from: hooks are not given `context_window`, only the
status line is. Rather than infer a window size from the model name (wrong by
5x between a 200k and a 1M model), statusline.sh publishes the percentage Claude
Code hands it, and this reads that file. No status line run yet, or a null
percentage after a compact, means no nudge.

Fail-open: any parse/IO error returns with no output (exit 0). This hook is
advisory and never blocks a prompt, so a stale cache or a missing file costs a
reminder, never a turn.
"""

import json
import os
import sys
import tempfile

HANDOFF_PCT = 35
BAND = 10


def state_dir():
    return tempfile.gettempdir()


def session_is_safe(session_id):
    return bool(session_id) and str(session_id).replace("-", "").replace("_", "").isalnum()


def read_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def context_pct(session_id):
    pct = read_json(os.path.join(state_dir(), f"claude-context-{session_id}.json")).get("pct")
    return pct if isinstance(pct, int) else None


def band_file(session_id):
    return os.path.join(state_dir(), f"claude-nudge-{session_id}.json")


def last_band(session_id):
    band = read_json(band_file(session_id)).get("band")
    return band if isinstance(band, int) else None


def record_band(session_id, band):
    try:
        with open(band_file(session_id), "w", encoding="utf-8") as fh:
            json.dump({"band": band}, fh)
    except OSError:
        pass


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    if not isinstance(data, dict):
        return

    session_id = data.get("session_id")
    if not session_is_safe(session_id):
        return

    pct = context_pct(session_id)
    if pct is None:
        return

    band = pct // BAND
    if pct < HANDOFF_PCT:
        # A compact drops the percentage back down; forget the bands already
        # announced so the next climb through them nudges again.
        if last_band(session_id) is not None:
            record_band(session_id, band)
        return

    out = {
        "systemMessage": (
            f"🧭 Context {pct}%: /handoff then /clear costs less than carrying this further"
        )
    }

    if band != last_band(session_id):
        record_band(session_id, band)
        out["hookSpecificOutput"] = {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": (
                f"Context is at {pct}% of the window. Per the context-hygiene rule, "
                "finish the current thread, then offer to write a handoff and clear. "
                "Do not clear on your own initiative."
            ),
        }

    print(json.dumps(out))


if __name__ == "__main__":
    main()
