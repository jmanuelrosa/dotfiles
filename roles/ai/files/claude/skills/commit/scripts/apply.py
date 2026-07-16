#!/usr/bin/env python3
"""apply.py - commit-loop executor for the /commit skill.

Reads an approved plan file and performs the stage + commit loop in one
Bash round-trip:

    {"commits": [{"files": ["a.ts", "b.ts"], "message": "feat(x): subject\n\n- body"}]}

Because this script commits outside the git-skill-gate hook's view of the
command string, it re-implements the hook's hard blocks itself: attribution
lines, em/en dashes, .claude/tasks/ paths, secret-looking files, header
length. It never passes --no-verify or --amend. On a pre-commit hook
failure it prints the output and stops the loop, leaving the failed
commit's files staged.
"""

import fnmatch
import json
import re
import subprocess
import sys
import tempfile

HEADER_MAX = 100

ATTRIBUTION_RE = re.compile(r"(?i)co-authored-by:.*claude|generated with.*\bclaude\b|\U0001F916")
DASH_RE = re.compile("[\u2014\u2013]")
TASKS_PATH_RE = re.compile(r"(^|/)\.claude/tasks/")
SECRET_BASENAME_GLOBS = (".env", ".env.*", "*.pem", "*-key.json", "credentials*")


def fail(msg):
    print(f"apply.py: {msg}", file=sys.stderr)
    sys.exit(1)


def run(args, **kw):
    return subprocess.run(args, capture_output=True, text=True, **kw)


def validate(commits):
    if not commits:
        fail("plan has no commits")
    for i, c in enumerate(commits, 1):
        files = c.get("files") or []
        message = c.get("message") or ""
        if not files:
            fail(f"commit {i}: empty file list")
        if not message.strip():
            fail(f"commit {i}: empty message")
        header = message.splitlines()[0]
        if len(header) > HEADER_MAX:
            fail(f"commit {i}: header exceeds {HEADER_MAX} chars: {header!r}")
        if ATTRIBUTION_RE.search(message):
            fail(f"commit {i}: message contains a Claude attribution line; attribution is handled by settings.json")
        if DASH_RE.search(message):
            fail(f"commit {i}: message contains an em/en dash; use a hyphen, comma, colon, or parentheses")
        for f in files:
            if TASKS_PATH_RE.search(f):
                fail(f"commit {i}: {f} is local-only agent state (.claude/tasks/) and must never be committed")
            base = f.rsplit("/", 1)[-1]
            if any(fnmatch.fnmatch(base, g) for g in SECRET_BASENAME_GLOBS):
                fail(f"commit {i}: {f} looks like a cleartext secret; drop it from the plan or get explicit user approval")


def main():
    if len(sys.argv) != 2:
        fail("usage: apply.py <plan.json>")
    try:
        with open(sys.argv[1]) as fh:
            plan = json.load(fh)
    except (OSError, ValueError) as e:
        fail(f"cannot read plan: {e}")

    commits = plan.get("commits") or []
    validate(commits)

    for i, c in enumerate(commits, 1):
        add = run(["git", "add", "--"] + c["files"])
        if add.returncode != 0:
            fail(f"commit {i}: git add failed:\n{add.stderr}")
        staged = run(["git", "diff", "--cached", "--name-only"])
        if not staged.stdout.strip():
            fail(f"commit {i}: nothing staged after git add {' '.join(c['files'])}")
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as tmp:
            tmp.write(c["message"].rstrip("\n") + "\n")
            msg_path = tmp.name
        commit = run(["git", "commit", "-F", msg_path])
        if commit.returncode != 0:
            print(commit.stdout, end="")
            print(commit.stderr, end="", file=sys.stderr)
            fail(f"commit {i}: git commit failed (pre-commit hook?); its files are still staged, fix before rerunning")
        header = c["message"].splitlines()[0]
        print(f"[{i}/{len(commits)}] {header}")

    log = run(["git", "log", "-n", str(len(commits)), "--pretty=%h %s"])
    print(log.stdout, end="")


if __name__ == "__main__":
    main()
