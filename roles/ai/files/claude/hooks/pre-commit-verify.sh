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

SUBPROCESS_TIMEOUT = 150
OUTPUT_TAIL_LINES = 60

OPTIONS_WITH_SEPARATE_ARG = {
    "-c", "-C",
    "--git-dir", "--work-tree", "--namespace",
    "--super-prefix", "--exec-path",
}

SHELL_SEPARATORS = {";", "&&", "||", "|", "&"}


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


def repo_root(cwd):
    try:
        out = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip() or None


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
    try:
        out = subprocess.run(
            ["git", "-C", root, "config", "core.hooksPath"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode == 0 and out.stdout.strip():
            return True
    except Exception:
        pass
    return False


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

    if not command or "git" not in command:
        sys.exit(0)

    if not any(is_git_commit(c) for c in split_subcommands(command)):
        sys.exit(0)

    root = repo_root(cwd)
    if not root:
        sys.exit(0)

    if has_own_precommit(root):
        sys.exit(0)

    for cmd in detect_commands(root):
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
