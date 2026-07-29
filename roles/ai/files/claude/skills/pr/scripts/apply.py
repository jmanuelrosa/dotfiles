#!/usr/bin/env python3
"""apply.py - push and open the PR/MR for the /pr skill.

Reads an approved plan file and performs the push plus the create call in one
Bash round-trip:

    {"host": "gh", "base": "main", "branch": "fix/gh-4-x",
     "title": "fix(x): y", "body_file": "/tmp/claude/pr-body-x.md",
     "repo": "gitlab.com-work/group/project"}

`repo` is GitLab only and optional: it is the `-R` value that pins the account
when one server backs several. `--skip-push` opens the PR against a branch that
is already on the remote.

Because this script pushes outside the git-skill-gate hook's view of the command
string, the hook gates it by path instead, and it re-implements the outward-text
blocks itself: attribution lines and typographic dashes in the title or body,
plus a refusal to push a branch carrying .claude/tasks/ state or a cleartext
secret. It never passes --no-verify. On a push failure it prints the standalone
`git` command to retry with, because the sandbox only runs a command
unsandboxed when its leading token is `git`, and a push spawned from here is
sandboxed: SSH auth and any pre-push hook needing the network or a write outside
the worktree fail there.
"""

import fnmatch
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 1
EXIT_BLOCKED = 2
EXIT_PUSH_FAILED = 3
EXIT_CREATE_FAILED = 4

HOSTS = ("gh", "glab")

ATTRIBUTION_RE = re.compile(r"(?i)co-authored-by:.*claude|generated with.*\bclaude\b|\U0001F916")
# Built from codepoints so the em-dash-gate hook never trips on this file itself.
DASH_RE = re.compile(f"[{chr(0x2014)}{chr(0x2013)}]")
TASKS_PATH_RE = re.compile(r"(^|/)\.claude/tasks/")

SECRET_BASENAME_GLOBS = (".env", ".env.*", "*.pem", "*-key.json", "credentials*")
# `.env.*` also matches the sample files a repo deliberately tracks, and unlike
# staging, a push cannot un-publish a secret that is already in history: the
# check is here to stop a fresh mistake leaving the machine, not to relitigate.
SECRET_EXEMPT_SUFFIXES = (".example", ".sample", ".template", ".dist")


def fail(message, code):
    print(f"apply.py: {message}", file=sys.stderr)
    sys.exit(code)


def run(argv):
    return subprocess.run(argv, capture_output=True, text=True)


def looks_secret(path):
    base = path.rsplit("/", 1)[-1]
    if base.endswith(SECRET_EXEMPT_SUFFIXES):
        return False
    return any(fnmatch.fnmatch(base, glob) for glob in SECRET_BASENAME_GLOBS)


def resolve_ref(base):
    for candidate in (base, f"origin/{base}"):
        probe = run(["git", "rev-parse", "--verify", "--quiet", f"{candidate}^{{commit}}"])
        if probe.returncode == 0:
            return candidate
    return ""


def changed_files(base):
    """Paths the branch touches, empty when the range cannot be resolved.

    An unresolvable range is not itself a reason to refuse the push: there is
    nothing to inspect, and the create call reports the real problem.
    """
    base_ref = resolve_ref(base)
    if not base_ref:
        return []
    proc = run(["git", "diff", "--name-only", "-z", f"{base_ref}...HEAD"])
    if proc.returncode != 0:
        return []
    return [path for path in proc.stdout.split("\0") if path]


def validate_text(label, text):
    if ATTRIBUTION_RE.search(text):
        fail(
            f"{label} contains a Claude attribution line; attribution is handled by settings.json",
            EXIT_BLOCKED,
        )
    if DASH_RE.search(text):
        fail(
            f"{label} contains an em/en dash; use a hyphen, comma, colon, or parentheses",
            EXIT_BLOCKED,
        )


def validate_branch(base):
    for path in changed_files(base):
        if TASKS_PATH_RE.search(path):
            fail(
                f"{path} is local-only agent state (.claude/tasks/) and must never reach the remote",
                EXIT_BLOCKED,
            )
        if looks_secret(path):
            fail(
                f"{path} looks like a cleartext secret; drop it from the branch before pushing",
                EXIT_BLOCKED,
            )


def remote_host():
    url = run(["git", "remote", "get-url", "origin"]).stdout.strip()
    if "://" in url:
        return url.split("://", 1)[1].partition("/")[0].rpartition("@")[2].partition(":")[0]
    return url.partition(":")[0].rpartition("@")[2]


def push_argv(host, branch):
    """The push, with GitHub forced onto HTTPS and the gh credential helper.

    This machine rewrites GitHub remotes to SSH globally and no session here can
    read ~/.ssh, so the rewrite is flipped back for the push only, and the helper
    chain is reset first so nothing is left in .git/config or ~/.gitconfig.
    """
    if host != "gh":
        return ["git", "push", "-u", "origin", branch]
    name = remote_host()
    return [
        "git",
        "-c",
        f"url.https://{name}/.pushInsteadOf=git@{name}:",
        "-c",
        "credential.helper=",
        "-c",
        "credential.helper=!gh auth git-credential",
        "push",
        "-u",
        "origin",
        branch,
    ]


def create_argv(plan, body):
    if plan["host"] == "gh":
        return [
            "gh", "pr", "create",
            "--base", plan["base"],
            "--head", plan["branch"],
            "--title", plan["title"],
            "--body-file", plan["body_file"],
            "--assignee", "@me",
        ]
    argv = ["glab", "mr", "create"]
    if plan.get("repo"):
        argv += ["-R", plan["repo"]]
    # glab has no --description-file, so the body travels as an argv value. No
    # shell is involved here, so fences and newlines survive intact.
    return argv + [
        "--target-branch", plan["base"],
        "--source-branch", plan["branch"],
        "--title", plan["title"],
        "--description", body,
        "--assignee", "@me",
        "--yes",
    ]


def load_plan(path):
    try:
        with open(path) as handle:
            plan = json.load(handle)
    except (OSError, ValueError) as error:
        fail(f"cannot read plan: {error}", EXIT_USAGE)
    if not isinstance(plan, dict):
        fail("plan must be a JSON object", EXIT_USAGE)
    if plan.get("host") not in HOSTS:
        fail(f"host must be one of {', '.join(HOSTS)}", EXIT_USAGE)
    for key in ("base", "branch", "title", "body_file"):
        if not str(plan.get(key) or "").strip():
            fail(f"plan is missing {key}", EXIT_USAGE)
    return plan


def main():
    argv = sys.argv[1:]
    skip_push = "--skip-push" in argv
    positional = [arg for arg in argv if arg != "--skip-push"]
    if len(positional) != 1:
        fail("usage: apply.py <plan.json> [--skip-push]", EXIT_USAGE)

    toplevel = run(["git", "rev-parse", "--show-toplevel"]).stdout.strip()
    if not toplevel:
        fail("not inside a git repository", EXIT_USAGE)

    plan = load_plan(positional[0])

    try:
        body = Path(plan["body_file"]).read_text()
    except OSError as read_error:
        fail(f"cannot read body file: {read_error}", EXIT_USAGE)
    if not body.strip():
        fail("body file is empty", EXIT_USAGE)

    validate_text("title", plan["title"])
    validate_text("body", body)
    validate_branch(plan["base"])

    if not skip_push:
        push = push_argv(plan["host"], plan["branch"])
        result = run(push)
        if result.returncode != 0:
            print(result.stdout, end="")
            print(result.stderr, end="", file=sys.stderr)
            fail(
                "push failed. Fix the cause, and never retry with --no-verify. When the cause\n"
                "  is auth or a pre-push hook that needs the network, run the push yourself as\n"
                "  a top-level command so it leaves the sandbox, then rerun with --skip-push:\n"
                f"    {shlex.join(push)}",
                EXIT_PUSH_FAILED,
            )
        print(f"Pushed {plan['branch']} to origin", file=sys.stderr)

    created = run(create_argv(plan, body))
    if created.returncode != 0:
        print(created.stdout, end="")
        print(created.stderr, end="", file=sys.stderr)
        fail(f"{plan['host']} refused to create the PR/MR", EXIT_CREATE_FAILED)

    lines = [line.strip() for line in created.stdout.splitlines() if line.strip()]
    if not lines:
        fail(f"{plan['host']} printed no URL", EXIT_CREATE_FAILED)
    print(f"Created: {lines[-1]}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
