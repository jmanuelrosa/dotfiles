#!/usr/bin/env python3
# vim: ft=python
# Filename keeps .sh extension to stay compatible with the path referenced in
# settings.json (hooks.PreToolUse) and the existing symlink in ~/.claude/hooks.
# The shebang is what determines execution.
"""git-skill-gate.sh — PreToolUse hook for Claude Code.

Blocks any `git commit`, `git push`, `gh pr create`, or `glab mr create`
invocation (including forms like `git -c key=val push`,
`git --git-dir=… push`, `VAR=… git push`, or `… && git push`) unless the
current session is inside the skill that owns that command: `git commit`
requires /commit; `git push`, `gh pr create`, and `glab mr create`
require /pr (SKILLS_FOR_SUBCOMMAND).

The signal is `attributionSkill` on the assistant event: Claude Code
stamps it on each assistant turn that runs inside a slash-command flow,
and AskUserQuestion preserves it across the approval gate. A gated
subcommand is allowed if any of the last 30 events is attributed to
one of its skills.

Hard-blocks `--no-verify` regardless of skill context. Also hard-blocks,
regardless of skill context: any `git commit` that stages files under
`.claude/tasks/` (local-only agent task state that must never be
tracked), and any commit message (read from `-m`/`--message` values and
`-F`/`--file` contents) containing a Claude attribution line
(`Co-Authored-By: ... Claude`, `🤖 Generated with ...`, handled instead
by the `attribution` setting in settings.json) or a typographic dash
(em/en dash; house style is a regular hyphen or plain punctuation).

Fail-open on transcript errors so harness replay or compaction can't
lock the user out. To swap to fail-closed, change the `sys.exit(0)`
lines in the transcript-handling path to `sys.exit(2)`.

Acknowledged limitations: the matcher does not parse subshells, command
substitution, `eval`, or shell aliases, and for gh/glab it does not
recognize flags placed before the subcommand (`gh -R o/r pr create`).
The gate is intent-friction, not a security boundary.
"""

import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

WINDOW_EVENTS = 30
SKILLS_FOR_SUBCOMMAND = {
    "git commit": {"commit"},
    "git push": {"pr"},
    "gh pr create": {"pr"},
    "glab mr create": {"pr"},
}

OPTIONS_WITH_SEPARATE_ARG = {
    "-c", "-C",
    "--git-dir", "--work-tree", "--namespace",
    "--super-prefix", "--exec-path",
}

SHELL_SEPARATORS = {";", "&&", "||", "|", "&"}

TASKS_PATH_RE = re.compile(r"(^|/)\.claude/tasks/")

ATTRIBUTION_RE = re.compile(r"(?i)co-authored-by:.*claude|generated with.*\bclaude\b|🤖")

DASH_RE = re.compile("[\u2014\u2013]")


def split_subcommands(line):
    padded = re.sub(r"(\|\||&&|;|\||&)", r" \1 ", line)
    try:
        tokens = shlex.split(padded, comments=False, posix=True)
    except ValueError:
        tokens = padded.split()
    chunks, cur = [], []
    for t in tokens:
        if t in SHELL_SEPARATORS:
            if cur:
                chunks.append(cur)
                cur = []
        else:
            cur.append(t)
    if cur:
        chunks.append(cur)
    return chunks


def gated_subcommand(tokens):
    i = 0
    while i < len(tokens) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[i]):
        i += 1
    if i >= len(tokens):
        return None
    binary = tokens[i]
    if binary == "git":
        i += 1
        while i < len(tokens):
            tok = tokens[i]
            if not tok.startswith("-"):
                break
            if tok in OPTIONS_WITH_SEPARATE_ARG:
                i += 2
            else:
                i += 1
        if i < len(tokens):
            key = f"git {tokens[i]}"
            if key in SKILLS_FOR_SUBCOMMAND:
                return key
        return None
    if binary in ("gh", "glab") and i + 2 < len(tokens):
        key = f"{binary} {tokens[i + 1]} {tokens[i + 2]}"
        if key in SKILLS_FOR_SUBCOMMAND:
            return key
    return None


def skills_in_window(transcript_path):
    if not transcript_path:
        return None
    path = Path(transcript_path)
    if not path.is_file():
        return None
    try:
        events = []
        with path.open() as f:
            for raw in f:
                try:
                    events.append(json.loads(raw))
                except Exception:
                    continue
        return {
            event.get("attributionSkill")
            for event in events[-WINDOW_EVENTS:]
            if event.get("attributionSkill")
        }
    except Exception:
        return None


def staged_tasks_files(cwd):
    """Staged paths under .claude/tasks/, or None on any error (fail-open)."""
    if not cwd:
        return None
    try:
        out = subprocess.run(
            ["git", "-C", cwd, "diff", "--cached", "--name-only", "-z"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return None
    if out.returncode != 0:
        return None
    return [p for p in out.stdout.split("\0") if p and TASKS_PATH_RE.search(p)]


def commit_message_texts(tokens, cwd):
    """Message texts from -m/--message values and -F/--file contents;
    unreadable files are skipped (fail-open)."""
    texts = []

    def add_file(value):
        path = Path(value)
        if not path.is_absolute() and cwd:
            path = Path(cwd) / value
        try:
            texts.append(path.read_text())
        except Exception:
            pass

    i = 0
    while i < len(tokens):
        tok = tokens[i]
        nxt = tokens[i + 1] if i + 1 < len(tokens) else None
        if tok in ("-m", "--message") and nxt is not None:
            texts.append(nxt)
            i += 2
        elif tok in ("-F", "--file") and nxt is not None:
            add_file(nxt)
            i += 2
        elif tok.startswith("--message="):
            texts.append(tok.split("=", 1)[1])
            i += 1
        elif tok.startswith("--file="):
            add_file(tok.split("=", 1)[1])
            i += 1
        elif len(tok) > 2 and tok.startswith("-m"):
            texts.append(tok[2:])
            i += 1
        elif len(tok) > 2 and tok.startswith("-F"):
            add_file(tok[2:])
            i += 1
        else:
            i += 1
    return texts


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    command = (data.get("tool_input") or {}).get("command", "") or ""
    transcript_path = data.get("transcript_path", "") or ""
    cwd = data.get("cwd", "") or ""

    if not command:
        sys.exit(0)

    if "--no-verify" in command:
        print(
            "--no-verify is blocked. Pre-commit hooks exist for a reason.\n"
            "If a hook is failing, fix the underlying issue or disable the hook\n"
            "in its own config — don't skip it.",
            file=sys.stderr,
        )
        sys.exit(2)

    chunks = split_subcommands(command)
    gated = [s for s in (gated_subcommand(c) for c in chunks) if s]
    if not gated:
        sys.exit(0)

    if "git commit" in gated:
        for chunk in chunks:
            if gated_subcommand(chunk) != "git commit":
                continue
            for text in commit_message_texts(chunk, cwd):
                if ATTRIBUTION_RE.search(text):
                    print(
                        "Commit message contains a Claude attribution line\n"
                        "(Co-Authored-By / 🤖 Generated with). Attribution is handled\n"
                        "by the `attribution` setting in settings.json; rewrite the\n"
                        "message without it and commit again.",
                        file=sys.stderr,
                    )
                    sys.exit(2)
                if DASH_RE.search(text):
                    print(
                        "Commit message contains an em/en dash (U+2014/U+2013).\n"
                        "House style: never use them. Rewrite the message with a\n"
                        "regular hyphen, comma, colon, or parentheses instead.",
                        file=sys.stderr,
                    )
                    sys.exit(2)

        tasks_hits = staged_tasks_files(cwd)
        if tasks_hits:
            preview = "\n".join(f"  {p}" for p in tasks_hits[:10])
            print(
                ".claude/tasks/ files are staged — that's local-only agent state and\n"
                "must never be tracked. Unstage it before committing:\n"
                f"{preview}\n"
                "\n"
                "  git restore --staged .claude/tasks\n"
                "\n"
                "and make sure `.claude/tasks/` (or `.claude/`) is in this repo's .gitignore.",
                file=sys.stderr,
            )
            sys.exit(2)

    active = skills_in_window(transcript_path)
    if active is None:
        print("git-skill-gate: transcript parse failed, allowing command", file=sys.stderr)
        sys.exit(0)

    blocked = sorted(s for s in set(gated) if not (SKILLS_FOR_SUBCOMMAND[s] & active))
    if not blocked:
        sys.exit(0)

    for sub in blocked:
        skills = " or ".join(f"/{s}" for s in sorted(SKILLS_FOR_SUBCOMMAND[sub]))
        print(f"Direct `{sub}` is blocked outside the {skills} skill.", file=sys.stderr)
    print(
        "\n"
        "Use:\n"
        "  /commit   (stage and commit through the structured flow)\n"
        "  /pr       (push and open the PR/MR)\n"
        "\n"
        "To bypass for a one-off, the user can run the command in a terminal\n"
        "or temporarily disable this hook in ~/.claude/settings.json\n"
        "(hooks.PreToolUse).",
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
