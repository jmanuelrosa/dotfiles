#!/usr/bin/env python3
"""context.py - one-shot branch context for the /pr skill.

Prints everything the drafting steps need in a single Bash round-trip: host,
base and current branch, the resolved GitLab account, the PR/MR template, the
commit list, the file stat, a filtered diff, and the deterministic title plus
the ticket the body needs.

Python rather than the bash shape /commit's context.sh uses, for two reasons.
The title derivation is a pure function of the branch name and the changed file
list (derive_title, unit-tested directly by tests/test_pr.py) and reads as
straight-line code only with real data structures. And parsing `glab repo view
-F json` and `glab auth status` here drops the `jq` dependency the shell form
needed, which the house convention forbids.
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

EXIT_OK = 0
EXIT_USAGE = 1
EXIT_NOT_A_REPO = 2
EXIT_NO_REMOTE = 3
EXIT_UNSUPPORTED_HOST = 4
EXIT_NO_BASE = 5
EXIT_NO_BRANCH = 6

RUN_TIMEOUT = 60
DIFF_FILE_CAP = int(os.environ.get("PR_DIFF_FILE_CAP") or 250)

# Noisy paths excluded from the drafting view only; they still appear in the
# stat section. The single-star form is deliberate: git's default pathspec
# matching treats `**/name` as requiring a leading directory, so the `**/` form
# lets a root-level package-lock.json straight through.
EXCLUDES = (
    ":(exclude)*package-lock.json",
    ":(exclude)*yarn.lock",
    ":(exclude)*pnpm-lock.yaml",
    ":(exclude)*bun.lock*",
    ":(exclude)*.min.js",
    ":(exclude)*.min.css",
    ":(exclude)*.map",
    ":(exclude)*node_modules/*",
    ":(exclude)*dist/*",
    ":(exclude)*build/*",
    ":(exclude)*.next/*",
    ":(exclude)*.generated.*",
    ":(exclude)*_generated.*",
    ":(exclude)*.pb.ts",
)

# Conventional Branch set, same as the regex in the commit skill and the
# ALLOWED_BRANCH_TYPES list in s-task.
BRANCH_TYPES = frozenset(
    {
        "feature",
        "fix",
        "chore",
        "docs",
        "refactor",
        "test",
        "perf",
        "ci",
        "build",
        "style",
        "revert",
    }
)

# Branch types and commitlint's commit types disagree on exactly one member.
COMMIT_TYPE_FOR_BRANCH_TYPE = {"feature": "feat"}

JIRA_TICKET = re.compile(r"^(?P<ref>[A-Z]+-[0-9]+)(?:-|$)")
GITHUB_TICKET = re.compile(r"^(?P<ref>gh-(?P<number>[0-9]+))(?:-|$)")

MONOREPO_ROOTS = ("packages", "apps")

# Container directories that name no feature and make a useless scope.
GENERIC_DIRS = frozenset(
    {"src", "lib", "libs", "app", "apps", "packages", "modules", "source", "test", "tests", "__tests__"}
)

GITHUB_TEMPLATES = (".github/pull_request_template.md", ".github/PULL_REQUEST_TEMPLATE.md")
GITLAB_TEMPLATES = (".gitlab/merge_request_templates/*.md",)

GLAB_ACCOUNT = re.compile(r"Logged in to (\S+) as (\S+)")
GLAB_ENDPOINT = re.compile(r"REST API Endpoint:\s*(\S+)")


def fail(message, code):
    print(f"context.py: {message}", file=sys.stderr)
    sys.exit(code)


def run(argv):
    """A finished process, or a failed stand-in when the binary is absent or hangs.

    Every caller here treats "could not run it" and "it said no" the same way, so
    the stand-in keeps them from each re-testing for a missing process.
    """
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=RUN_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired):
        return subprocess.CompletedProcess(argv, 1, "", "")


def git(*args, strip=True):
    proc = run(["git", "-c", "color.ui=never", *args])
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip() if strip else proc.stdout


def detect_host(remote):
    if "github" in remote:
        return "gh"
    if "gitlab" in remote:
        return "glab"
    return ""


def parse_remote(url):
    """(host, namespace) from either an scp-style or a URL-style remote."""
    if "://" in url:
        parts = urlsplit(url)
        host, path = parts.hostname or "", parts.path
    else:
        userhost, _, path = url.partition(":")
        host = userhost.rpartition("@")[2]
    return host, path.strip("/").removesuffix(".git")


def origin_head():
    return git("symbolic-ref", "--short", "refs/remotes/origin/HEAD").removeprefix("origin/")


def default_branch(host):
    base = origin_head()
    if not base:
        git("remote", "set-head", "origin", "-a")
        base = origin_head()
    if base:
        return base
    if host == "gh":
        argv = ["gh", "repo", "view", "--json", "defaultBranchRef", "--jq", ".defaultBranchRef.name"]
    else:
        argv = ["glab", "repo", "view", "-F", "json", "--jq", ".default_branch"]
    proc = run(argv)
    return proc.stdout.strip() if proc.returncode == 0 else ""


def resolve_ref(base):
    """The comparable ref for `base`, preferring the local branch.

    A repo cloned shallow or with a single branch has origin/<base> but no local
    <base>, and the diff has to work there too.
    """
    for candidate in (base, f"origin/{base}"):
        if run(["git", "rev-parse", "--verify", "--quiet", f"{candidate}^{{commit}}"]).returncode == 0:
            return candidate
    return ""


def glab_accounts():
    """(host, account, api_host) per authenticated host, from `glab auth status`.

    glab writes the block to stderr and, when sandboxed, appends an unrelated
    config-write error, so both streams are scanned and the exit code ignored.
    """
    proc = run(["glab", "auth", "status"])
    found = []
    for line in f"{proc.stderr}\n{proc.stdout}".splitlines():
        account = GLAB_ACCOUNT.search(line)
        if account:
            found.append([account.group(1), account.group(2), account.group(1)])
            continue
        endpoint = GLAB_ENDPOINT.search(line)
        if endpoint and found:
            found[-1][2] = urlsplit(endpoint.group(1)).hostname or found[-1][2]
    return [tuple(entry) for entry in found]


def glab_candidates(accounts, remote_host):
    """Authenticated hosts whose key or API endpoint matches the remote host.

    One server can back several accounts through a host alias, and glab picks by
    the remote's host token, so a fixed list resolves the wrong account.
    """
    return [(host, account) for host, account, api in accounts if remote_host in (host, api)]


def find_template(root, host):
    """The repo's PR/MR template, the host's own shape first."""
    own, other = (GITLAB_TEMPLATES, GITHUB_TEMPLATES) if host == "glab" else (GITHUB_TEMPLATES, GITLAB_TEMPLATES)
    for pattern in own + other:
        for match in sorted(root.glob(pattern)):
            if match.is_file():
                return match
    return None


def split_ticket(rest):
    """(ticket ref, kind, issue number, remaining slug) for a branch tail."""
    for kind, pattern in (("github", GITHUB_TICKET), ("jira", JIRA_TICKET)):
        match = pattern.match(rest)
        if match:
            number = match.groupdict().get("number") or ""
            return match.group("ref"), kind, number, rest[match.end("ref") :].lstrip("-")
    return "", "none", "", rest


def prose(slug):
    return " ".join(re.sub(r"[-_]+", " ", slug).split())


def monorepo_package(paths):
    names = set()
    for path in paths:
        parts = path.split("/")
        if len(parts) < 3 or parts[0] not in MONOREPO_ROOTS:
            return ""
        names.add(parts[1])
    return names.pop() if len(names) == 1 else ""


def shared_directory(paths):
    directories = [path.split("/")[:-1] for path in paths]
    common = []
    for level in zip(*directories):
        if len(set(level)) != 1:
            break
        common.append(level[0])
    for name in reversed(common):
        if name.lower() not in GENERIC_DIRS:
            return name
    return ""


def shared_areas(paths):
    """Path segments every file has in common, longest first.

    Needs two files at least: one file's own directory or name is what
    shared_directory already answered, not a shared area.
    """
    if len(paths) < 2:
        return []
    per_path = []
    for path in paths:
        parts = path.split("/")
        segments = {segment.lower() for segment in parts[:-1]}
        segments.add(parts[-1].split(".")[0].lower())
        per_path.append({s for s in segments if s and s not in GENERIC_DIRS})
    shared = set.intersection(*per_path)
    return sorted(shared, key=lambda segment: (-len(segment), segment))


def derive_scope(paths):
    """(scope, candidates) from the changed files, by the three-rule precedence."""
    paths = [path for path in paths if path]
    if not paths:
        return "", []
    package = monorepo_package(paths)
    if package:
        return package, []
    directory = shared_directory(paths)
    if directory:
        return directory, []
    areas = shared_areas(paths)
    if len(areas) == 1:
        return areas[0], []
    return "", areas


def derive_title(branch, files):
    """The title, ticket and scope implied by a branch name and its diff.

    Pure: no git, no filesystem, no environment. A GitHub issue never becomes a
    title suffix because GitHub appends its own `(#<pr-number>)` on squash merge,
    so `(#456)` in a title reads as a PR number; its link goes in the body.
    """
    derived = {
        "conventional": False,
        "type": "",
        "scope": "",
        "scope_candidates": [],
        "slug": "",
        "ticket": "",
        "ticket_kind": "none",
        "closes": "",
        "title": "",
    }
    branch_type, _, rest = branch.partition("/")
    if not rest or branch_type not in BRANCH_TYPES:
        return derived

    ticket, kind, number, tail = split_ticket(rest)
    commit_type = COMMIT_TYPE_FOR_BRANCH_TYPE.get(branch_type, branch_type)
    slug = prose(tail)
    scope, candidates = derive_scope(files)

    title = f"{commit_type}({scope})" if scope else commit_type
    if slug:
        title = f"{title}: {slug}"
    if kind == "jira":
        title = f"{title} ({ticket})"

    derived.update(
        conventional=True,
        type=commit_type,
        scope=scope,
        scope_candidates=candidates,
        slug=slug,
        ticket=ticket,
        ticket_kind=kind,
        closes=f"Closes #{number}" if kind == "github" else "",
        title=title,
    )
    return derived


def cap_per_file(diff, cap):
    lines, count = [], 0
    for line in diff.splitlines():
        if line.startswith("diff --git "):
            count = 0
            lines.append(line)
            continue
        count += 1
        if count <= cap:
            lines.append(line)
        elif count == cap + 1:
            lines.append(f"... [capped at {cap} lines; run git diff -- <path> for the rest]")
    return "\n".join(lines)


def emit(key, value):
    print(f"{key}={value}")


class Parser(argparse.ArgumentParser):
    """argparse exits 2 on a usage error, which is the not-a-repo code here."""

    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(EXIT_USAGE, f"context.py: {message}\n")


def main():
    parser = Parser(prog="context.py", description=__doc__.splitlines()[0])
    parser.add_argument("base", nargs="?", help="base branch, overrides origin/HEAD")
    parser.add_argument("--title", help="explicit title the caller owns, used verbatim")
    args = parser.parse_args()

    toplevel = git("rev-parse", "--show-toplevel")
    if not toplevel:
        fail("not inside a git repository", EXIT_NOT_A_REPO)
    os.chdir(toplevel)
    root = Path(toplevel)

    remote = git("remote", "get-url", "origin")
    if not remote:
        fail("no origin remote", EXIT_NO_REMOTE)
    host = detect_host(remote)
    if not host:
        fail(f"unsupported remote host: {remote}", EXIT_UNSUPPORTED_HOST)

    branch = git("branch", "--show-current")
    if not branch:
        fail("detached HEAD, no branch to open a PR from", EXIT_NO_BRANCH)

    base = args.base or default_branch(host)
    if not base:
        fail("could not determine the default branch", EXIT_NO_BASE)
    base_ref = resolve_ref(base)
    if not base_ref:
        fail(f"base branch {base} resolves to nothing locally, fetch it first", EXIT_NO_BASE)

    files = [line for line in git("diff", "--name-only", f"{base_ref}...HEAD").splitlines() if line]
    derived = derive_title(branch, files)

    print("== target ==")
    emit("HOST", host)
    emit("BASE", base)
    emit("BRANCH", branch)
    emit("BRANCH_CONVENTION", "ok" if derived["conventional"] else "nonstandard")
    emit("TYPE", derived["type"])
    emit("SCOPE", derived["scope"])
    emit("SCOPE_CANDIDATES", ", ".join(derived["scope_candidates"]))
    emit("TITLE", args.title or derived["title"])
    if args.title:
        emit("TITLE_SOURCE", "override")
    else:
        emit("TITLE_SOURCE", "derived" if derived["conventional"] else "unresolved")
    emit("TICKET", derived["ticket"])
    emit("TICKET_KIND", derived["ticket_kind"])
    emit("CLOSES", derived["closes"])

    if host == "glab":
        remote_host, namespace = parse_remote(remote)
        emit("NS", namespace)
        candidates = glab_candidates(glab_accounts(), remote_host)
        if len(candidates) == 1:
            host_key, _ = candidates[0]
            emit("GLHOST", host_key)
            emit("REPO", f"{host_key}/{namespace}")
        else:
            emit("GLHOST", "")
            emit(
                "GLHOST_CANDIDATES",
                ", ".join(f"{host_key} ({account})" for host_key, account in candidates),
            )
            if candidates:
                emit("GIT_EMAIL", git("config", "--get", "user.email"))
            else:
                emit("NOT_LOGGED_IN", remote_host)

    template = find_template(root, host)
    print("\n== template ==")
    if template is None:
        print("PATH=<none>")
    else:
        emit("PATH", template.relative_to(root))
        print()
        print(template.read_text(), end="")

    print("\n== commits ==")
    print(git("log", f"{base_ref}..HEAD", "--pretty=%h %s") or "<no commits on this branch>")

    print("\n== changed files (stat) ==")
    print(git("diff", f"{base_ref}...HEAD", "--stat"))

    print("\n== diff (noisy paths excluded, capped per file) ==")
    diff = git("diff", f"{base_ref}...HEAD", "--", ".", *EXCLUDES, strip=False)
    print(cap_per_file(diff, DIFF_FILE_CAP))

    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
