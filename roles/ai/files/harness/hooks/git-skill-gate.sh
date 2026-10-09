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

Wrapper scripts that run git in a subprocess are invisible here: the hook
receives the Bash command, not what that command spawns. Four are known,
and they are not all handled in the same direction.

`skills/commit/scripts/apply.py` commits and `skills/pr/scripts/apply.py`
pushes, neither carrying the token that would name it, so both are gated
by path (WRAPPER_SCRIPTS) and need their owning skill like any other
commit or push.

`s-task` (~/.local/bin/s-task, from this repo's `work` role) pushes, and
that push is deliberately allowed rather than gated. It exists so a
GitHub issue gets a linked branch and a Jira ticket's Development panel
can see the branch, both of which require the branch to be on the remote,
and it happens at the start of the work rather than the end, so requiring
/pr would be backwards. What keeps it narrow: it pushes only a branch it
created moments earlier, off the default branch's tip, with no commits on
it, and it refuses to push a branch that already existed. So it cannot
push work, and /pr stays the only path that pushes commits. `s-task
--no-push` skips the push entirely.

`s-release` (~/.local/bin/s-release, from the same role) runs `gh pr
create`, and that is deliberately allowed too. It exists for a ritual
`master` will retire: opening the pull request that merges `develop` into
`master`, which is what deploys to production, across several repos at
once. What keeps it narrow: base and head are constants with no flag to
reach them, so it can only ever open `develop` into `master`; it commits
and pushes nothing, since both refs are already on the remote; it refuses
when there is nothing to release or a release PR is already open, so it
can open neither an empty one nor a duplicate; and it never merges, which
is the step that actually deploys. So /pr stays the only path that opens
a pull request for code someone wrote.

Git aliases are expanded before any check, by asking `git config --get
alias.<name>` in the command's cwd, so `git p` is gated the same as `git
push` when `p = push`, and `--no-verify` or a commit message inside an
alias is seen. A `!` alias is parsed as the shell line it names and never
executed. Destructive aliases that are not a commit or a push (`reset
--hard`) are left to the deny list in policy/permissions.toml.

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

# A skill's apply.py runs the gated command in a subprocess, with no `git
# commit` or `git push` in the command string, so executing it (directly or
# via an interpreter) gets the same gate by path. Only execution positions
# are checked: a `wc -c .../apply.py` must not trip the gate.
WRAPPER_SCRIPTS = (
    (re.compile(r"(^|/)skills/commit/scripts/apply\.py$"), "git commit"),
    (re.compile(r"(^|/)skills/pr/scripts/apply\.py$"), "git push"),
)
INTERPRETERS = {"bash", "sh", "zsh", "python", "python3"}

OPTIONS_WITH_SEPARATE_ARG = {
    "-c", "-C",
    "--git-dir", "--work-tree", "--namespace",
    "--super-prefix", "--exec-path",
}

CONFIG_LOCATING_OPTIONS = {"-C", "--git-dir", "--work-tree"}

SHELL_SEPARATORS = {";", "&&", "||", "|", "&"}

ENV_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

COMBINED_MESSAGE_FLAG_RE = re.compile(r"^-[A-Za-z]+m$")

SHELL_FUNCTION_SYNTAX_RE =re.compile(r"^(\{|\}|\(|\)|[A-Za-z_][A-Za-z0-9_-]*\(\))$")

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


def wrapper_subcommand(token):
    for pattern, subcommand in WRAPPER_SCRIPTS:
        if pattern.search(token):
            return subcommand
    return None


def git_subcommand_index(tokens):
    i = 1
    while i < len(tokens):
        tok = tokens[i]
        if not tok.startswith("-"):
            break
        i += 2 if tok in OPTIONS_WITH_SEPARATE_ARG else 1
    return i


def lookup_options(global_options):
    """The global options that choose which config an alias is read from.

    `-c` is forwarded only for `alias.*`, so nothing the command sets can change
    what the lookup itself does."""
    forwarded = []
    i = 0
    while i < len(global_options):
        tok = global_options[i]
        nxt = global_options[i + 1] if i + 1 < len(global_options) else None
        if "=" in tok and tok.split("=", 1)[0] in CONFIG_LOCATING_OPTIONS:
            forwarded.append(tok)
        elif tok in OPTIONS_WITH_SEPARATE_ARG and nxt is not None:
            if tok in CONFIG_LOCATING_OPTIONS or (tok == "-c" and nxt.startswith("alias.")):
                forwarded += [tok, nxt]
            i += 1
        i += 1
    return forwarded


def run_git(args, cwd):
    """stdout of a read-only git call, or None on any failure (fail-open)."""
    try:
        out = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=cwd if cwd and Path(cwd).is_dir() else None,
        )
    except Exception:
        return None
    return out.stdout if out.returncode == 0 else None


def git_alias(name, global_options, cwd):
    """The body git would expand `name` to, or None when it is not an alias.

    Git runs a real command over an alias of the same name, so a name it lists
    as a command is never expanded."""
    options = lookup_options(global_options)
    body = (run_git([*options, "config", "--get", f"alias.{name}"], cwd) or "").strip()
    if not body:
        return None
    commands = run_git([*options, "--list-cmds=builtins,main,others"], cwd)
    if commands and name in commands.split():
        return None
    return body


def shell_alias_chunks(line):
    """A `!` alias line as command chunks, with a function-style wrapper peeled off."""
    chunks = []
    for chunk in split_subcommands(line):
        while chunk and SHELL_FUNCTION_SYNTAX_RE.match(chunk[0]):
            chunk = chunk[1:]
        if chunk:
            chunks.append(chunk)
    return chunks


def expand_git_aliases(tokens, cwd, seen_aliases=frozenset()):
    """The command chunks a chunk really runs, with git aliases expanded as git would.

    A `!` alias is a shell line: it is parsed, never run. Git appends the
    caller's arguments to that line, so they land on its last chunk."""
    start = 0
    while start < len(tokens) and ENV_ASSIGNMENT_RE.match(tokens[start]):
        start += 1
    if start >= len(tokens) or tokens[start] != "git":
        return [tokens]
    i = start + git_subcommand_index(tokens[start:])
    if i >= len(tokens):
        return [tokens]
    name = tokens[i]
    if f"git {name}" in SKILLS_FOR_SUBCOMMAND or name in seen_aliases:
        return [tokens]
    body = git_alias(name, tokens[start + 1:i], cwd)
    if body is None:
        return [tokens]
    seen = seen_aliases | {name}
    rest = tokens[i + 1:]
    if body.startswith("!"):
        chunks = shell_alias_chunks(body[1:])
        if chunks:
            chunks[-1] = chunks[-1] + rest
        return [expanded for chunk in chunks for expanded in expand_git_aliases(chunk, cwd, seen)]
    try:
        expansion = shlex.split(body)
    except ValueError:
        expansion = body.split()
    return expand_git_aliases([*tokens[:i], *expansion, *rest], cwd, seen)


def gated_subcommand(tokens):
    i = 0
    while i < len(tokens) and ENV_ASSIGNMENT_RE.match(tokens[i]):
        i += 1
    if i >= len(tokens):
        return None
    binary = tokens[i]
    wrapper = wrapper_subcommand(binary)
    if wrapper:
        return wrapper
    if binary in INTERPRETERS:
        for tok in tokens[i + 1:]:
            if tok.startswith("-"):
                continue
            wrapper = wrapper_subcommand(tok)
            if wrapper:
                return wrapper
            break
    if binary == "git":
        i += git_subcommand_index(tokens[i:])
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
        if (tok in ("-m", "--message") or COMBINED_MESSAGE_FLAG_RE.match(tok)) and nxt is not None:
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

    chunks = [
        expanded
        for chunk in split_subcommands(command)
        for expanded in expand_git_aliases(chunk, cwd)
    ]

    if "--no-verify" in command or any("--no-verify" in tok for chunk in chunks for tok in chunk):
        print(
            "--no-verify is blocked. Pre-commit hooks exist for a reason.\n"
            "If a hook is failing, fix the underlying issue or disable the hook\n"
            "in its own config — don't skip it.",
            file=sys.stderr,
        )
        sys.exit(2)

    keyed = [(chunk, gated_subcommand(chunk)) for chunk in chunks]
    gated = [key for _, key in keyed if key]
    if not gated:
        sys.exit(0)

    if "git commit" in gated:
        for chunk, key in keyed:
            if key != "git commit":
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
