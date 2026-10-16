#!/usr/bin/env python3
"""apply.py - branch, commit, push and open the PR/MR for the /ship skill.

Reads the approved plan and runs the whole outward sequence in one Bash
round-trip, so nothing after the confirmation gate waits on a human:

    {"branch": {"action": "keep", "name": "fix/gh-4-banner"},
     "commits": [{"files": ["src/a.ts"], "message": "fix(x): subject\\n\\n- why"}],
     "pr": {"base": "main", "body_file": "/tmp/claude/ship-body-x.md",
            "repo": "gitlab.com-work/group/project"}}

`branch.action` is `keep` (ship from the current branch), `create` (new branch
at HEAD, carrying any commits already on it), `create-from-base` (new branch off
the remote base, carrying only the working tree and leaving the existing
commits behind) or `rename` (a nonstandard current branch). `commits` may be
empty when the branch already holds the work. `pr.repo` is GitLab only and pins
the account when one server backs several. File paths are relative to the
repository root.

`--from push` resumes after the commits landed; `--from pr` resumes after a
push the caller ran by hand. Every check runs up front, before the first
mutation, and the run stops on the first failure.

The git-skill-gate hook sees this command, not what it spawns, so it gates the
script by path and this script re-implements the hook's hard blocks itself:
attribution lines and typographic dashes in any message, title or body,
`.claude/tasks/` state and cleartext secrets in a commit or on the branch,
nonstandard branch names, pushing the default branch, and a title that differs
from the derivation. It never passes --no-verify or --amend.
"""

import argparse
import fnmatch
import importlib.util
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 1
EXIT_BLOCKED = 2
EXIT_COMMIT_FAILED = 3
EXIT_PUSH_FAILED = 4
EXIT_CREATE_FAILED = 5

HEADER_MAX = 100
BRANCH_ACTIONS = ("keep", "create", "create-from-base", "rename")
STAGES = ("commit", "push", "pr")

ATTRIBUTION_RE = re.compile(r"(?i)co-authored-by:.*claude|generated with.*\bclaude\b|\U0001F916")
# Built from codepoints so the em-dash-gate hook never trips on this file itself.
DASH_RE = re.compile(f"[{chr(0x2014)}{chr(0x2013)}]")
TASKS_PATH_RE = re.compile(r"(^|/)\.claude/tasks/")
SECRET_BASENAME_GLOBS = (".env", ".env.*", "*.pem", "*-key.json", "credentials*")
# `.env.*` also matches the sample files a repo deliberately tracks, and the committed,
# non-secret env files test and local scripts load through `--env-file`.
SECRET_EXEMPT_SUFFIXES = (".example", ".sample", ".template", ".dist", ".env.test", ".env.e2e", ".env.docker", ".env.dev")


def load_context():
    path = Path(__file__).with_name("context.py")
    spec = importlib.util.spec_from_file_location("ship_context_for_apply", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CONTEXT = load_context()


def fail(message, code):
    print(f"apply.py: {message}", file=sys.stderr)
    sys.exit(code)


def run(argv):
    return subprocess.run(argv, capture_output=True, text=True)


def git(*args):
    return run(["git", *args])


def looks_secret(path):
    name = path.rsplit("/", 1)[-1]
    if name.endswith(SECRET_EXEMPT_SUFFIXES):
        return False
    return any(fnmatch.fnmatch(name, glob) for glob in SECRET_BASENAME_GLOBS)


def check_text(label, text):
    if ATTRIBUTION_RE.search(text):
        fail(f"{label} contains a Claude attribution line; attribution is handled by settings.json", EXIT_BLOCKED)
    if DASH_RE.search(text):
        fail(f"{label} contains an em/en dash; use a hyphen, comma, colon, or parentheses", EXIT_BLOCKED)


def check_path(label, path):
    if TASKS_PATH_RE.search(path):
        fail(f"{label}: {path} is local-only agent state (.claude/tasks/) and must never be committed", EXIT_BLOCKED)
    if looks_secret(path):
        fail(f"{label}: {path} looks like a cleartext secret; drop it from the plan", EXIT_BLOCKED)


def validate_commits(commits):
    for i, commit in enumerate(commits, 1):
        files = commit.get("files") or []
        message = commit.get("message") or ""
        if not files:
            fail(f"commit {i}: empty file list", EXIT_USAGE)
        if not message.strip():
            fail(f"commit {i}: empty message", EXIT_USAGE)
        header = message.splitlines()[0]
        if len(header) > HEADER_MAX:
            fail(f"commit {i}: header exceeds {HEADER_MAX} chars: {header!r}", EXIT_BLOCKED)
        check_text(f"commit {i} message", message)
        for path in files:
            check_path(f"commit {i}", path)


def branch_exists(name):
    return git("rev-parse", "--verify", "--quiet", f"refs/heads/{name}").returncode == 0


def validate_branch_plan(branch, base):
    action, name = branch.get("action"), branch.get("name") or ""
    if action not in BRANCH_ACTIONS:
        fail(f"branch.action must be one of {', '.join(BRANCH_ACTIONS)}", EXIT_USAGE)
    current = git("branch", "--show-current").stdout.strip()
    if not current:
        fail("detached HEAD, no branch to ship from", EXIT_BLOCKED)
    if action == "keep":
        if name and name != current:
            fail(f"plan keeps branch {name!r} but the current branch is {current!r}", EXIT_BLOCKED)
        name = current
    elif branch_exists(name):
        fail(f"branch {name!r} already exists; pick another name", EXIT_BLOCKED)
    if name == base:
        fail(f"{name!r} is the base branch; ship from a <type>/<slug> branch instead", EXIT_BLOCKED)
    if not CONTEXT.BRANCH_RE.fullmatch(name):
        fail(
            f"branch {name!r} is nonstandard; use <type>/<slug> or <type>/<TICKET>-<slug> "
            "with the Conventional Branch types",
            EXIT_BLOCKED,
        )
    return action, name


def switch_branch(action, name, base_ref):
    if action == "keep":
        return
    if action == "create":
        argv = ["switch", "-c", name]
    elif action == "create-from-base":
        argv = ["switch", "--no-track", "-c", name, base_ref]
    else:
        argv = ["branch", "-m", name]
    result = git(*argv)
    if result.returncode != 0:
        fail(f"git {' '.join(argv)} failed, nothing was committed:\n{result.stderr}", EXIT_BLOCKED)
    print(f"Branch: {name}")


def unplanned(staged, files):
    """`git commit` takes the whole index, so anything staged beyond the plan rides along."""
    planned = [os.path.normpath(f) for f in files]
    if "." in planned:
        return []
    return [
        path for path in staged
        if path and not any(path == p or path.startswith(p + "/") for p in planned)
    ]


def commit_all(commits):
    for i, commit in enumerate(commits, 1):
        added = git("add", "--", *commit["files"])
        if added.returncode != 0:
            fail(f"commit {i}: git add failed:\n{added.stderr}", EXIT_COMMIT_FAILED)
        staged = git("diff", "--cached", "--name-only").stdout.split("\n")
        if not any(staged):
            fail(f"commit {i}: nothing staged after git add {' '.join(commit['files'])}", EXIT_COMMIT_FAILED)
        stray = unplanned(staged, commit["files"])
        if stray:
            fail(
                f"commit {i}: the index also holds paths outside this commit's plan: {', '.join(stray)}. "
                "Add them to the plan or unstage them, then rerun",
                EXIT_COMMIT_FAILED,
            )
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as handle:
            handle.write(commit["message"].rstrip("\n") + "\n")
            message_path = handle.name
        done = git("commit", "-F", message_path)
        os.unlink(message_path)
        if done.returncode != 0:
            print(done.stdout, end="")
            print(done.stderr, end="", file=sys.stderr)
            fail(
                f"commit {i}: git commit failed (pre-commit hook?); its files are still staged. "
                "Fix the cause, drop the commits that landed from the plan, and rerun",
                EXIT_COMMIT_FAILED,
            )
        print(f"[{i}/{len(commits)}] {commit['message'].splitlines()[0]}")


def changed_files(base_ref):
    proc = git("diff", "--name-only", "-z", f"{base_ref}...HEAD")
    return [path for path in proc.stdout.split("\0") if path] if proc.returncode == 0 else []


def remote_host():
    url = git("remote", "get-url", "origin").stdout.strip()
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
        "-c", f"url.https://{name}/.pushInsteadOf=git@{name}:",
        "-c", "credential.helper=",
        "-c", "credential.helper=!gh auth git-credential",
        "push", "-u", "origin", branch,
    ]


def existing_pr(host, branch, repo):
    """The URL of an open PR/MR already proposing `branch`, or an empty string."""
    if host == "gh":
        proc = run(["gh", "pr", "list", "--head", branch, "--state", "open", "--json", "url"])
        key = "url"
    else:
        proc = run(["glab", "mr", "list", "--source-branch", branch, "-F", "json", *(["-R", repo] if repo else [])])
        key = "web_url"
    if proc.returncode != 0:
        return ""
    try:
        found = json.loads(proc.stdout or "[]")
    except ValueError:
        return ""
    return found[0].get(key, "") if found else ""


def create_argv(host, base, branch, title, body, body_path, repo):
    if host == "gh":
        return [
            "gh", "pr", "create",
            "--base", base, "--head", branch,
            "--title", title, "--body-file", body_path,
            "--assignee", "@me",
        ]
    # glab has no --description-file, so the body travels as an argv value. No
    # shell is involved here, so fences and newlines survive intact.
    return [
        "glab", "mr", "create", *(["-R", repo] if repo else []),
        "--target-branch", base, "--source-branch", branch,
        "--title", title, "--description", body,
        "--assignee", "@me", "--yes",
    ]


def with_closes(body, closes):
    if not closes or closes in body:
        return body
    return f"{body.rstrip()}\n\n{closes}\n"


def load_plan(path):
    try:
        with open(path) as handle:
            plan = json.load(handle)
    except (OSError, ValueError) as error:
        fail(f"cannot read plan: {error}", EXIT_USAGE)
    if not isinstance(plan, dict):
        fail("plan must be a JSON object", EXIT_USAGE)
    if not isinstance(plan.get("branch"), dict):
        fail("plan is missing branch", EXIT_USAGE)
    if not isinstance(plan.get("commits", []), list):
        fail("commits must be a list", EXIT_USAGE)
    pr = plan.get("pr")
    if not isinstance(pr, dict):
        fail("plan is missing pr", EXIT_USAGE)
    for key in ("base", "body_file"):
        if not str(pr.get(key) or "").strip():
            fail(f"plan is missing pr.{key}", EXIT_USAGE)
    return plan


def main():
    parser = argparse.ArgumentParser(prog="apply.py", description=__doc__.splitlines()[0])
    parser.add_argument("plan")
    parser.add_argument("--from", dest="stage", choices=STAGES, default="commit")
    args = parser.parse_args()

    toplevel = git("rev-parse", "--show-toplevel").stdout.strip()
    if not toplevel:
        fail("not inside a git repository", EXIT_USAGE)
    plan = load_plan(args.plan)
    os.chdir(toplevel)

    host = CONTEXT.detect_host(git("remote", "get-url", "origin").stdout)
    if not host:
        fail("origin is neither GitHub nor GitLab", EXIT_USAGE)
    base = plan["pr"]["base"]
    base_ref = CONTEXT.resolve_ref(base)
    if not base_ref:
        fail(f"base branch {base} resolves to nothing locally, fetch it first", EXIT_USAGE)
    repo = plan["pr"].get("repo") or ""

    try:
        body = Path(plan["pr"]["body_file"]).read_text()
    except OSError as error:
        fail(f"cannot read body file: {error}", EXIT_USAGE)
    if not body.strip():
        fail("body file is empty", EXIT_USAGE)
    check_text("body", body)

    commits = plan.get("commits") or []
    if args.stage == "commit":
        validate_commits(commits)
        action, branch = validate_branch_plan(plan["branch"], base)
        switch_branch(action, branch, base_ref)
        commit_all(commits)
    else:
        _, branch = validate_branch_plan({"action": "keep"}, base)

    files = changed_files(base_ref)
    if not files:
        fail(f"{branch} has no changes against {base_ref}, nothing to ship", EXIT_BLOCKED)
    for path in files:
        check_path("branch", path)
    derived = CONTEXT.derive_title(branch, files)
    title = derived["title"]
    check_text("title", title)
    body = with_closes(body, derived["closes"])

    if args.stage != "pr":
        push = push_argv(host, branch)
        pushed = run(push)
        if pushed.returncode != 0:
            print(pushed.stdout, end="")
            print(pushed.stderr, end="", file=sys.stderr)
            fail(
                "push failed. Fix the cause, and never retry with --no-verify. When the cause\n"
                "  is auth or a pre-push hook that needs the network, run the push yourself as\n"
                "  a top-level command so it leaves the sandbox, then rerun with --from pr:\n"
                f"    {shlex.join(push)}",
                EXIT_PUSH_FAILED,
            )
        print(f"Pushed {branch} to origin")

    open_pr = existing_pr(host, branch, repo)
    if open_pr:
        print(f"Updated: {open_pr}")
        return EXIT_OK

    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
        handle.write(body)
        body_path = handle.name
    created = run(create_argv(host, base, branch, title, body, body_path, repo))
    os.unlink(body_path)
    if created.returncode != 0:
        print(created.stdout, end="")
        print(created.stderr, end="", file=sys.stderr)
        fail(f"{host} refused to create the PR/MR; once fixed, rerun with --from pr", EXIT_CREATE_FAILED)
    lines = [line.strip() for line in created.stdout.splitlines() if line.strip()]
    if not lines:
        fail(f"{host} printed no URL", EXIT_CREATE_FAILED)
    print(f"Title: {title}")
    print(f"Created: {lines[-1]}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
