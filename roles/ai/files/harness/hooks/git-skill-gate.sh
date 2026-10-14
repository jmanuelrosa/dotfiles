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

The command word is read past exec wrappers (`env`, `command`, `exec`, `nice`,
`nohup`, `time`, `timeout`, `xargs`), leading shell syntax, a subshell's
parentheses, a shell's `-c` line and `eval`, and by basename, so
`/opt/homebrew/bin/git` and `env git` are gated as `git`.

Hard-blocks skipping hooks regardless of skill context: `--no-verify`, an
abbreviation git still accepts (`--no-veri`), and `commit -n`, alone or in a
bundle such as `-anm`. Hard-blocks, for the same reason, setting
`core.hooksPath` or a remote's URL (`remote.*.url`, `remote.*.pushurl`,
`url.*.insteadOf`, `url.*.pushInsteadOf`) through `-c`, `--config-env`,
`GIT_CONFIG_PARAMETERS`, `GIT_CONFIG_KEY_<n>` or a `git config` write, and
`git remote add`, `set-url` and `rename`. Also hard-blocks,
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
by path (WRAPPER_SCRIPTS). The pr script needs /pr like any other push.
The commit script has its own key, allowed under /commit or /pr: when
/commit and /pr are invoked back to back, the turns that run the commit
script are stamped `pr`, the later of the two, so a /commit-only key
refused real commit flows. A raw `git commit` still needs /commit, so /pr
buys only the validated commit path. The staged `.claude/tasks/` block
covers the commit script too; its plan's messages are checked by the
script itself, since the hook never sees them on the command line.

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

A raw push that forces, deletes a remote branch, or targets main, master or
the remote's default branch is blocked even inside /pr. The deny list
matches text, so `git -C x p --force`, `git push -uf` and `git push origin
HEAD:main` slip past it; this parses the push after alias expansion. A raw
push whose repository, positional or `--repo`, is not a configured remote is
blocked too, since /pr pushes to the branch's remote and a URL there is a copy
of the work sent somewhere else.

Codex never writes `attributionSkill`, so there the skill route would refuse
every commit. Codex runs this hook with SKIP_SKILL_ROUTE_FLAG, which keeps
every check above and drops only the skill route.

Acknowledged limitations: the matcher does not parse a quoted command
substitution, backticks, or shell aliases, and for gh/glab it does not
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
SKIP_SKILL_ROUTE_FLAG = "--skip-skill-route"
COMMIT_SCRIPT = "skills/commit/scripts/apply.py"
SKILLS_FOR_SUBCOMMAND = {
    "git commit": {"commit"},
    COMMIT_SCRIPT: {"commit", "pr"},
    "git push": {"pr"},
    "gh pr create": {"pr"},
    "glab mr create": {"pr"},
}

# A skill's apply.py runs the gated command in a subprocess, with no `git
# commit` or `git push` in the command string, so executing it (directly or
# via an interpreter) gets the same gate by path. Only execution positions
# are checked: a `wc -c .../apply.py` must not trip the gate.
WRAPPER_SCRIPTS = (
    (re.compile(r"(^|/)skills/commit/scripts/apply\.py$"), COMMIT_SCRIPT),
    (re.compile(r"(^|/)skills/pr/scripts/apply\.py$"), "git push"),
)
COMMITTING = {"git commit", COMMIT_SCRIPT}
INTERPRETERS = {"bash", "sh", "zsh", "python", "python3"}

# A command word spelled by path is reduced to its name, so `/opt/homebrew/bin/git`
# is checked as `git`. Only these names: a wrapper script is matched by its path.
NAMED_BY_BASENAME = {"git", "gh", "glab", *INTERPRETERS}

# Words that run the rest of the line, each with the options that take a separate
# value, so `env -u X git push` and `timeout 30 git push` are checked as the push.
EXEC_WRAPPERS = {
    "env": {"-u", "--unset", "-C", "--chdir", "-P"},
    "command": set(),
    "exec": {"-a"},
    "nice": {"-n", "--adjustment"},
    "nohup": set(),
    "time": set(),
    "timeout": {"-s", "--signal", "-k", "--kill-after"},
    "xargs": {"-I", "-J", "-L", "-n", "-P", "-R", "-S", "-s", "-E", "-d", "-a"},
}
WRAPPERS_WITH_A_DURATION = {"timeout"}
ENV_SPLIT_OPTIONS = {"-S", "--split-string"}
SHELL_SYNTAX = {"{", "}", "!", "if", "then", "else", "elif", "do", "while", "until"}
SHELLS = {"bash", "sh", "zsh", "dash", "ksh", "fish"}
SHELL_OPTIONS_WITH_SEPARATE_ARG = {"-o", "+o", "-O", "+O"}
MAX_UNWRAP_DEPTH = 3

OPTIONS_WITH_SEPARATE_ARG = {
    "-c", "-C",
    "--git-dir", "--work-tree", "--namespace",
    "--super-prefix", "--exec-path", "--config-env",
}

CONFIG_LOCATING_OPTIONS = {"-C", "--git-dir", "--work-tree"}

SHELL_SEPARATORS = {";", "&&", "||", "|", "&", "(", ")"}

ENV_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

COMBINED_MESSAGE_FLAG_RE = re.compile(r"^-[A-Za-z]+m$")

SHELL_FUNCTION_SYNTAX_RE =re.compile(r"^(\{|\}|\(|\)|[A-Za-z_][A-Za-z0-9_-]*\(\))$")

TASKS_PATH_RE = re.compile(r"(^|/)\.claude/tasks/")

ATTRIBUTION_RE = re.compile(r"(?i)co-authored-by:.*claude|generated with.*\bclaude\b|🤖")

DASH_RE = re.compile("[\u2014\u2013]")

PUSH_OPTIONS_WITH_SEPARATE_ARG = {"-o", "--push-option", "--repo", "--receive-pack", "--exec"}
FORCE_PUSH_OPTIONS = {"--force", "--force-with-lease"}
DELETING_PUSH_OPTIONS = {"--delete", "--mirror", "--prune"}
FALLBACK_PROTECTED_BRANCHES = {"main", "master"}
FORCE_PUSH, DELETING_PUSH = "a force push", "a push that deletes remote branches"
UNKNOWN_REMOTE_PUSH = "a push to a URL or to a remote that is not configured"
URL_SHAPED_RE = re.compile(r"[:@]")

NO_VERIFY_ABBREVIATION_RE = re.compile(r"^--no-veri(?:fy?)?$")
COMMIT_SHORT_OPTIONS_WITH_ARG = set("mFCct")
COMMIT_SHORT_OPTIONS_WITH_ATTACHED_ARG = set("Su")
COMMIT_LONG_OPTIONS_WITH_ARG = {
    "--message", "--file", "--reuse-message", "--reedit-message", "--template",
    "--author", "--date", "--fixup", "--squash", "--trailer", "--cleanup",
    "--pathspec-from-file",
}

# Config that decides which hooks run or where a push lands. Setting it for one
# call or for good is as good as --no-verify, or as a push to a URL.
PROTECTED_CONFIG_KEY = r"core\.hookspath|remote\.[^'=\s]+\.(?:push)?url|url\.[^'=\s]+\.(?:push)?insteadof"
PROTECTED_CONFIG_KEY_RE = re.compile(rf"(?i)^(?:{PROTECTED_CONFIG_KEY})$")
PROTECTED_CONFIG_SEARCH_RE = re.compile(rf"(?i)(?:{PROTECTED_CONFIG_KEY})")
GIT_CONFIG_ENV_RE = re.compile(r"^GIT_CONFIG_(?:PARAMETERS|KEY_\d+)$")
CONFIG_WRITE_WORDS = {"set", "unset", "rename-section", "remove-section"}
CONFIG_WRITE_FLAGS = {"--unset", "--unset-all", "--add", "--replace-all"}
CONFIG_READ_FLAGS = {"--get", "--get-all", "--get-regexp", "--get-urlmatch", "-l", "--list"}
CONFIG_OPTIONS_WITH_ARG = {"-f", "--file", "--blob", "--type", "--default", "--comment", "--value", "--url"}
REMOTE_REDIRECTS = {"add", "set-url", "rename"}


def split_line(line):
    try:
        return shlex.split(line, comments=False, posix=True)
    except ValueError:
        return line.split()


def split_subcommands(line):
    padded = re.sub(r"(\|\||&&|;|\||&|\(|\))", r" \1 ", line)
    tokens = split_line(padded)
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


def shell_line(name, command):
    """The line a shell's `-c` or an `eval` runs, or None."""
    if name == "eval":
        return " ".join(command[1:])
    if name not in SHELLS:
        return None
    j, runs_line = 1, False
    while j < len(command) and command[j][:1] in ("-", "+") and command[j] not in ("-", "--"):
        flag = command[j]
        runs_line = runs_line or (not flag.startswith("--") and "c" in flag[1:])
        j += 2 if flag in SHELL_OPTIONS_WITH_SEPARATE_ARG else 1
    return command[j] if runs_line and j < len(command) else None


def unwrapped(tokens, depth=0):
    """The chunks a chunk really runs, each as its env assignments then a command.

    Leading shell syntax and exec wrappers are dropped, a shell's `-c` line and
    an `eval` are split into chunks of their own, and a git, forge or interpreter
    spelled by path is reduced to its name."""
    assignments, i = [], 0
    while i < len(tokens):
        tok = tokens[i]
        wrapper = Path(tok).name
        if ENV_ASSIGNMENT_RE.match(tok):
            assignments.append(tok)
            i += 1
        elif tok in SHELL_SYNTAX:
            i += 1
        elif wrapper in EXEC_WRAPPERS:
            i += 1
            durations = 1 if wrapper in WRAPPERS_WITH_A_DURATION else 0
            while i < len(tokens):
                option = tokens[i]
                if wrapper == "env" and option in ENV_SPLIT_OPTIONS and i + 1 < len(tokens):
                    tokens = [*tokens[:i], *split_line(tokens[i + 1]), *tokens[i + 2:]]
                elif option == "--":
                    i += 1
                    break
                elif option.startswith("-") and len(option) > 1:
                    i += 2 if option in EXEC_WRAPPERS[wrapper] else 1
                elif durations:
                    durations -= 1
                    i += 1
                else:
                    break
        else:
            break
    command = tokens[i:]
    if not command:
        return [assignments] if assignments else []
    name = Path(command[0]).name
    line = shell_line(name, command) if depth < MAX_UNWRAP_DEPTH else None
    if line is not None:
        return [
            [*assignments, *inner]
            for chunk in split_subcommands(line)
            for inner in unwrapped(chunk, depth + 1)
        ]
    if name in NAMED_BY_BASENAME:
        command = [name, *command[1:]]
    return [[*assignments, *command]]


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
        return [
            expanded
            for chunk in chunks
            for plain in unwrapped(chunk)
            for expanded in expand_git_aliases(plain, cwd, seen)
        ]
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


def protected_branches(remote, lookup, cwd):
    """The remote's default branch beside main and master, since a repo that
    defaults to develop can still deploy from master."""
    head = run_git([*lookup, "symbolic-ref", "--short", f"refs/remotes/{remote}/HEAD"], cwd)
    default = head.strip().split("/", 1)[-1] if head else None
    return FALLBACK_PROTECTED_BRANCHES | ({default} if default else set())


def destructive_push_reason(tokens, cwd):
    """Why a raw `git push` must never run, or None.

    Parsed rather than globbed, so a force flag after the remote, a bundled
    `-uf`, a `:branch` or `HEAD:main` refspec, and a global option before the
    subcommand are all seen. Aliases are already expanded by the caller."""
    start = 0
    while start < len(tokens) and ENV_ASSIGNMENT_RE.match(tokens[start]):
        start += 1
    if start >= len(tokens) or tokens[start] != "git":
        return None
    i = start + git_subcommand_index(tokens[start:])
    lookup = lookup_options(tokens[start + 1:i])
    args, positionals, repository, j = tokens[i + 1:], [], None, 0
    while j < len(args):
        tok = args[j]
        if tok == "--":
            positionals += args[j + 1:]
            break
        if tok.startswith("--"):
            name = tok.split("=", 1)[0]
            if name in FORCE_PUSH_OPTIONS:
                return FORCE_PUSH
            if name in DELETING_PUSH_OPTIONS:
                return DELETING_PUSH
            if name == "--repo":
                repository = tok.split("=", 1)[1] if "=" in tok else (args[j + 1] if j + 1 < len(args) else None)
            if name in PUSH_OPTIONS_WITH_SEPARATE_ARG and "=" not in tok:
                j += 1
        elif tok.startswith("-") and len(tok) > 1:
            for k, letter in enumerate(tok[1:], start=2):
                if letter == "f":
                    return FORCE_PUSH
                if letter == "d":
                    return DELETING_PUSH
                if letter == "o":
                    j += 1 if k == len(tok) else 0
                    break
        else:
            positionals.append(tok)
        j += 1

    if positionals:
        repository = positionals[0]
    if repository and not is_configured_remote(repository, lookup, cwd):
        return UNKNOWN_REMOTE_PUSH
    remote = repository or "origin"
    current = (run_git([*lookup, "symbolic-ref", "--short", "HEAD"], cwd) or "").strip()
    protected = protected_branches(remote, lookup, cwd)
    refspecs = positionals[1:] or [current]
    for spec in refspecs:
        if spec.startswith("+"):
            return FORCE_PUSH
        source, colon, destination = spec.partition(":")
        if colon and not source:
            return DELETING_PUSH
        target = (destination if colon else source).removeprefix("refs/heads/")
        if target == "HEAD":
            target = current
        if target in protected:
            return f"a push to {target}"
    return None


def is_configured_remote(repository, lookup, cwd):
    """Whether a push's repository names a configured remote. When the remotes
    cannot be listed, only a URL-shaped repository is refused."""
    remotes = run_git([*lookup, "remote"], cwd)
    if remotes is None:
        return not URL_SHAPED_RE.search(repository)
    return repository in remotes.split()


def git_command(tokens):
    """(index of `git`, index of its subcommand) past env assignments, or None."""
    start = 0
    while start < len(tokens) and ENV_ASSIGNMENT_RE.match(tokens[start]):
        start += 1
    if start >= len(tokens) or tokens[start] != "git":
        return None
    return start, start + git_subcommand_index(tokens[start:])


def skips_hooks(tokens):
    """Whether a git call skips hooks without spelling `--no-verify`: an
    abbreviation git still accepts, or `commit -n` alone or in a bundle."""
    located = git_command(tokens)
    if not located:
        return False
    _, i = located
    args = tokens[i + 1:]
    if any(NO_VERIFY_ABBREVIATION_RE.match(tok) for tok in args):
        return True
    if i >= len(tokens) or tokens[i] != "commit":
        return False
    j = 0
    while j < len(args):
        tok = args[j]
        if tok == "--":
            break
        if tok in COMMIT_LONG_OPTIONS_WITH_ARG:
            j += 1
        elif tok.startswith("-") and not tok.startswith("--"):
            for k, letter in enumerate(tok[1:], start=2):
                if letter == "n":
                    return True
                if letter in COMMIT_SHORT_OPTIONS_WITH_ARG:
                    j += 1 if k == len(tok) else 0
                    break
                if letter in COMMIT_SHORT_OPTIONS_WITH_ATTACHED_ARG:
                    break
        j += 1
    return False


def config_reason(tokens):
    """What a chunk does to config that decides which hooks run or where a push
    lands, or None."""
    start = 0
    while start < len(tokens) and ENV_ASSIGNMENT_RE.match(tokens[start]):
        start += 1
    exported = tokens[start + 1:] if start < len(tokens) and tokens[start] == "export" else []
    for assignment in [*tokens[:start], *exported]:
        name, _, value = assignment.partition("=")
        found = GIT_CONFIG_ENV_RE.match(name) and PROTECTED_CONFIG_SEARCH_RE.search(value)
        if found:
            return f"Setting {found.group(0)} through {name}"
    located = git_command(tokens)
    if not located:
        return None
    start, i = located
    j = start + 1
    while j < i:
        tok = tokens[j]
        if tok in ("-c", "--config-env") and j + 1 < i:
            setting = tokens[j + 1]
        elif tok.startswith("--config-env="):
            setting = tok.split("=", 1)[1]
        else:
            setting = ""
        key = setting.split("=", 1)[0]
        if PROTECTED_CONFIG_KEY_RE.match(key):
            return f"Setting {key}"
        j += 2 if tok in OPTIONS_WITH_SEPARATE_ARG else 1
    if i >= len(tokens):
        return None
    subcommand, args = tokens[i], tokens[i + 1:]
    words, flags, j = [], [], 0
    while j < len(args):
        tok = args[j]
        if tok.startswith("-"):
            flags.append(tok.split("=", 1)[0])
            j += 2 if subcommand == "config" and tok in CONFIG_OPTIONS_WITH_ARG else 1
        else:
            words.append(tok)
            j += 1
    if subcommand == "remote" and words and words[0] in REMOTE_REDIRECTS:
        return f"`git remote {words[0]}`"
    if subcommand != "config":
        return None
    keys = [word for word in words if PROTECTED_CONFIG_KEY_RE.match(word)]
    if not keys:
        return None
    legacy_set = words[0] == keys[0] and len(words) > 1 and not CONFIG_READ_FLAGS.intersection(flags)
    if words[0] in CONFIG_WRITE_WORDS or CONFIG_WRITE_FLAGS.intersection(flags) or legacy_set:
        return f"Changing {keys[0]}"
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
        for plain in unwrapped(chunk)
        for expanded in expand_git_aliases(plain, cwd)
    ]

    if (
        "--no-verify" in command
        or any("--no-verify" in tok for chunk in chunks for tok in chunk)
        or any(skips_hooks(chunk) for chunk in chunks)
    ):
        print(
            "Skipping git hooks is blocked: --no-verify, its abbreviations, and commit -n.\n"
            "Pre-commit hooks exist for a reason. If a hook is failing, fix the\n"
            "underlying issue or disable the hook in its own config, don't skip it.",
            file=sys.stderr,
        )
        sys.exit(2)

    reason = next((found for chunk in chunks if (found := config_reason(chunk))), None)
    if reason:
        print(
            f"{reason} is blocked for agents, even inside /commit or /pr:\n"
            "it decides which git hooks run or where a push lands.\n"
            "Hand the user the exact command to run in their own terminal.",
            file=sys.stderr,
        )
        sys.exit(2)

    keyed = [(chunk, gated_subcommand(chunk)) for chunk in chunks]
    gated = [key for _, key in keyed if key]
    if not gated:
        sys.exit(0)

    for chunk, key in keyed:
        reason = destructive_push_reason(chunk, cwd) if key == "git push" else None
        if reason:
            print(
                f"{reason[0].upper()}{reason[1:]} is blocked for agents, even inside /pr.\n"
                "Hand the user the exact command to run in their own terminal.",
                file=sys.stderr,
            )
            sys.exit(2)

    if COMMITTING.intersection(gated):
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

    if SKIP_SKILL_ROUTE_FLAG in sys.argv[1:]:
        sys.exit(0)

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
