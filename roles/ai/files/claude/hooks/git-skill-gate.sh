#!/usr/bin/env python3
# vim: ft=python
# Filename keeps .sh extension to stay compatible with the path referenced in
# settings.json (hooks.PreToolUse) and the existing symlink in ~/.claude/hooks.
# The shebang is what determines execution.
"""git-skill-gate.sh — PreToolUse hook for Claude Code.

Blocks any `git commit` or `git push` invocation (including forms like
`git -c key=val push`, `git --git-dir=… push`, `VAR=… git push`, or
`… && git push`) unless the current session is inside the /commit or
/pr skill.

The signal is `attributionSkill` on the assistant event: Claude Code
stamps it on each assistant turn that runs inside a slash-command flow,
and AskUserQuestion preserves it across the approval gate. Allow if any
of the last 30 events is attributed to a skill in ALLOWED_SKILLS.

Hard-blocks `--no-verify` regardless of skill context. Also hard-blocks
any `git commit` that stages files under `.claude/tasks/` (local-only
agent task state that must never be tracked), regardless of skill context.

Fail-open on transcript errors so harness replay or compaction can't
lock the user out. To swap to fail-closed, change the `sys.exit(0)`
lines in the transcript-handling path to `sys.exit(2)`.

Acknowledged limitations: the matcher does not parse subshells, command
substitution, `eval`, or shell aliases. The gate is intent-friction, not
a security boundary.
"""

import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

WINDOW_EVENTS = 30
ALLOWED_SKILLS = {"commit", "pr"}
GATED_SUBCOMMANDS = {"commit", "push"}

OPTIONS_WITH_SEPARATE_ARG = {
    "-c", "-C",
    "--git-dir", "--work-tree", "--namespace",
    "--super-prefix", "--exec-path",
}

SHELL_SEPARATORS = {";", "&&", "||", "|", "&"}

TASKS_PATH_RE = re.compile(r"(^|/)\.claude/tasks/")


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
    if i >= len(tokens) or tokens[i] != "git":
        return None
    i += 1
    while i < len(tokens):
        tok = tokens[i]
        if not tok.startswith("-"):
            break
        if tok in OPTIONS_WITH_SEPARATE_ARG:
            i += 2
        else:
            i += 1
    if i < len(tokens) and tokens[i] in GATED_SUBCOMMANDS:
        return tokens[i]
    return None


def is_gated(tokens):
    return gated_subcommand(tokens) is not None


def recently_invoked_allowed_skill(transcript_path):
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
        for event in events[-WINDOW_EVENTS:]:
            if event.get("attributionSkill") in ALLOWED_SKILLS:
                return True
        return False
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

    gated = [s for s in (gated_subcommand(c) for c in split_subcommands(command)) if s]
    if not gated:
        sys.exit(0)

    if "commit" in gated:
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

    result = recently_invoked_allowed_skill(transcript_path)
    if result is None:
        print("git-skill-gate: transcript parse failed, allowing command", file=sys.stderr)
        sys.exit(0)
    if result:
        sys.exit(0)

    print(
        "Direct `git commit` / `git push` is blocked outside the commit/pr skills.\n"
        "\n"
        "Use:\n"
        "  /commit   — stage and commit through the structured flow\n"
        "  /pr       — push and open the PR/MR\n"
        "\n"
        "To bypass for a one-off, the user can run the command in a terminal\n"
        "or temporarily disable this hook in ~/.claude/settings.json\n"
        "(hooks.PreToolUse).",
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
