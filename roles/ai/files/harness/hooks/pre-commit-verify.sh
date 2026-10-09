#!/usr/bin/env python3
# vim: ft=python
# Filename keeps .sh extension for consistency with the sibling hooks
# referenced from settings.json (hooks.PreToolUse). The shebang is what
# determines execution.
"""pre-commit-verify.sh — PreToolUse hook for Claude Code.

Runs the project's check-only verification (typecheck / lint) before any
`git commit` so regressions surface at commit time instead of later in
code review. Detection ladder, first match wins:

  0. repo has its own pre-commit machinery (.husky/, lefthook,
     .pre-commit-config.yaml, core.hooksPath, an executable
     .git/hooks/pre-commit) → defer to it, exit 0
  1. package.json scripts: typecheck / type-check / lint, run via the
     lockfile-matched package manager (bun / pnpm / yarn / npm)
  2. Makefile with a `lint` target → `make lint` — the universal escape
     hatch: any ecosystem (Swift, Zig, …) can expose one
  3. .swiftlint.yml + swiftlint on PATH → swiftlint --strict
  4. Cargo.toml + cargo → cargo check -q
  5. go.mod + go → go vet ./...
  6. ruff config + ruff → ruff check .
  7. .ansible-lint + ansible-lint → ansible-lint

Only a repo whose `origin` sits under a namespace listed in
trusted-remotes.json, beside hooks/, has its checks run. A hook runs
outside the agent sandbox, so in a stranger's clone a lint script that
pipes curl into sh would run with the user's full access the moment a
commit is attempted. Elsewhere, including a repo with no origin at all
(a downloaded archive given a fresh `git init` looks exactly like a repo
the user started), the checks are skipped with a one-line note.

Check-only commands, never fixers: a `lint:fix` would mutate the tree
mid-commit and diverge staged content from what was verified.

Fail-open everywhere: unknown project type, missing binary, tool crash,
or timeout allows the commit — the gate must never lock the user out.
Only a real non-zero exit from a detected tool blocks (exit 2), feeding
the tool output back so the failure is fixed before committing.
"""

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from shutil import which
from urllib.parse import urlsplit

SUBPROCESS_TIMEOUT = 150
OUTPUT_TAIL_LINES = 60

OPTIONS_WITH_SEPARATE_ARG = {
    "-c", "-C",
    "--git-dir", "--work-tree", "--namespace",
    "--super-prefix", "--exec-path",
}

SHELL_SEPARATORS = {";", "&&", "||", "|", "&"}

# The commit skill commits through this script, so a commit made by /commit never
# shows up as `git commit` on the command line.
COMMIT_WRAPPER = re.compile(r"(^|/)skills/commit/scripts/apply\.py$")
INTERPRETERS = {"bash", "sh", "zsh", "python", "python3"}

# Every harness reaches this hook through a symlink, and only the link's target has the
# harness root as its grandparent.
TRUSTED_REMOTES = Path(os.path.realpath(__file__)).parent.parent / "trusted-remotes.json"
REMOTE_SCHEMES = {"ssh", "git", "http", "https", "git+ssh", "ssh+git"}
GIT_PROBE_TIMEOUT = 5


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


def is_git_commit(tokens):
    i = 0
    while i < len(tokens) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[i]):
        i += 1
    if i < len(tokens) and Path(tokens[i]).name in INTERPRETERS:
        i += 1
    if i < len(tokens) and COMMIT_WRAPPER.search(tokens[i]):
        return True
    if i >= len(tokens) or tokens[i] != "git":
        return False
    i += 1
    while i < len(tokens):
        tok = tokens[i]
        if not tok.startswith("-"):
            break
        if tok in OPTIONS_WITH_SEPARATE_ARG:
            i += 2
        else:
            i += 1
    return i < len(tokens) and tokens[i] == "commit"


def git_output(root, *args):
    try:
        out = subprocess.run(
            ["git", "-C", root, *args],
            capture_output=True,
            text=True,
            timeout=GIT_PROBE_TIMEOUT,
        )
    except Exception:
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def repo_root(cwd):
    return git_output(cwd, "rev-parse", "--show-toplevel") or None


def split_location(path):
    segments = [s.lower() for s in path.strip("/").removesuffix(".git").split("/") if s]
    if any(s in {".", ".."} for s in segments):
        return ()
    return tuple(segments)


def remote_location(url):
    """(host, path segments) of a remote URL, or None for a local path or anything unparseable.

    The host is taken after the last `@`, so userinfo spelled like a trusted host
    does not pass for one.
    """
    url = url.strip()
    if "://" in url:
        try:
            parts = urlsplit(url)
            host = parts.hostname or ""
        except ValueError:
            return None
        if parts.scheme.lower() not in REMOTE_SCHEMES:
            return None
        path = parts.path
    else:
        head, sep, path = url.partition(":")
        if not sep or "/" in head:
            return None
        host = head.rpartition("@")[2].lower()
    segments = split_location(path)
    if not host or not segments:
        return None
    return host, segments


def load_trusted(path):
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return None
    entries = data.get("remotes") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return None
    trusted = []
    for entry in entries:
        if not isinstance(entry, str):
            continue
        host, _, namespace = entry.strip().partition("/")
        segments = split_location(namespace)
        if host and segments:
            trusted.append((host.lower(), segments))
    return trusted


def is_trusted(url, trusted):
    location = remote_location(url)
    if not location:
        return False
    host, segments = location
    return any(
        host == trusted_host and segments[: len(namespace)] == namespace
        for trusted_host, namespace in trusted
    )


def untrusted_reason(root, trusted_path=TRUSTED_REMOTES):
    """None when the repo's checks may run, else why they may not.

    The origin is named by host and path only, since a URL can carry a token in its userinfo.
    """
    url = git_output(root, "remote", "get-url", "origin")
    if not url:
        return "the repo has no origin remote to check against the trusted list"
    trusted = load_trusted(trusted_path)
    if trusted is None:
        return f"the trusted list {trusted_path} could not be read"
    if is_trusted(url, trusted):
        return None
    location = remote_location(url)
    shown = "/".join((location[0], *location[1])) if location else "a local path"
    return f"origin {shown} is not under a namespace in {Path(trusted_path).name}"


def has_own_precommit(root):
    r = Path(root)
    if (r / ".husky").is_dir():
        return True
    if any(
        (r / f).is_file()
        for f in ("lefthook.yml", ".lefthook.yml", "lefthook.yaml", ".pre-commit-config.yaml")
    ):
        return True
    hook = r / ".git" / "hooks" / "pre-commit"
    if hook.is_file() and os.access(hook, os.X_OK):
        return True
    return bool(git_output(root, "config", "core.hooksPath"))


def package_manager(root):
    r = Path(root)
    if (r / "bun.lockb").is_file() or (r / "bun.lock").is_file():
        return "bun"
    if (r / "pnpm-lock.yaml").is_file():
        return "pnpm"
    if (r / "yarn.lock").is_file():
        return "yarn"
    return "npm"


def detect_commands(root):
    r = Path(root)

    pkg = r / "package.json"
    if pkg.is_file():
        try:
            scripts = json.loads(pkg.read_text()).get("scripts") or {}
        except Exception:
            scripts = {}
        names = [s for s in ("typecheck", "type-check", "lint") if s in scripts]
        if names:
            pm = package_manager(root)
            return [[pm, "run", s] for s in names]

    for mk in ("Makefile", "makefile", "GNUmakefile"):
        f = r / mk
        if f.is_file():
            try:
                text = f.read_text()
            except Exception:
                text = ""
            if re.search(r"^lint:", text, re.MULTILINE):
                return [["make", "lint"]]
            break

    if (r / ".swiftlint.yml").is_file() and which("swiftlint"):
        return [["swiftlint", "--strict"]]

    if (r / "Cargo.toml").is_file() and which("cargo"):
        return [["cargo", "check", "-q"]]

    if (r / "go.mod").is_file() and which("go"):
        return [["go", "vet", "./..."]]

    ruff_configured = (r / "ruff.toml").is_file() or (r / ".ruff.toml").is_file()
    pyproject = r / "pyproject.toml"
    if not ruff_configured and pyproject.is_file():
        try:
            ruff_configured = "[tool.ruff" in pyproject.read_text()
        except Exception:
            pass
    if ruff_configured and which("ruff"):
        return [["ruff", "check", "."]]

    if (r / ".ansible-lint").is_file() and which("ansible-lint"):
        return [["ansible-lint"]]

    return []


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    command = (data.get("tool_input") or {}).get("command", "") or ""
    cwd = data.get("cwd", "") or "."

    if not command or ("git" not in command and "apply.py" not in command):
        sys.exit(0)

    if not any(is_git_commit(c) for c in split_subcommands(command)):
        sys.exit(0)

    root = repo_root(cwd)
    if not root:
        sys.exit(0)

    if has_own_precommit(root):
        sys.exit(0)

    commands = detect_commands(root)
    if not commands:
        sys.exit(0)

    reason = untrusted_reason(root)
    if reason:
        skipped = ", ".join(f"`{' '.join(cmd)}`" for cmd in commands)
        print(f"pre-commit-verify: skipped {skipped} because {reason}", file=sys.stderr)
        sys.exit(0)

    for cmd in commands:
        pretty = " ".join(cmd)
        try:
            out = subprocess.run(
                cmd,
                cwd=root,
                capture_output=True,
                text=True,
                timeout=SUBPROCESS_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            print(
                f"pre-commit-verify: `{pretty}` exceeded {SUBPROCESS_TIMEOUT}s, "
                "allowing commit unverified",
                file=sys.stderr,
            )
            sys.exit(0)
        except Exception as exc:
            print(
                f"pre-commit-verify: could not run `{pretty}` ({exc}), "
                "allowing commit unverified",
                file=sys.stderr,
            )
            sys.exit(0)
        if out.returncode != 0:
            combined = (out.stdout + "\n" + out.stderr).strip()
            tail = "\n".join(combined.splitlines()[-OUTPUT_TAIL_LINES:])
            print(
                f"Verification failed before commit: `{pretty}` exited {out.returncode}.\n"
                "Fix the failures below, then retry the commit. Do not use --no-verify.\n"
                "\n"
                f"{tail}",
                file=sys.stderr,
            )
            sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
