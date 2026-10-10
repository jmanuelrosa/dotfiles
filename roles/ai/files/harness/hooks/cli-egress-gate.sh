#!/usr/bin/env python3
# vim: ft=python
# Filename keeps .sh extension to match the other hooks referenced from
# settings.json (hooks.PreToolUse) and symlinked into ~/.claude/hooks.
"""cli-egress-gate.sh - PreToolUse hook for the allowlisted CLIs that can publish.

gh, glab, ntn and bru run OUTSIDE Claude's sandbox
(sandbox.excludedCommands) so they can reach their own credential stores,
and all four are allowlisted, so neither the network allowlist nor a
permission prompt stands between an agent and the service. That makes
them an egress channel: a gist, snippet, release asset, secret, CI
variable, Notion file upload, worker deploy or API body publishes
whatever local file the agent names, and a Bruno collection reaches any
host it lists. This hook is the guardrail on what they may do, in three
tiers. The gh and glab rules come first; ntn and bru follow them.

  block (exit 2): uploads and writes with no review step between the
    agent and a published copy. `gh gist create/edit`, `glab snippet
    create`, `gh secret set`, `gh/glab variable set`, `glab securefile
    create`, `release upload`, a `release create` that attaches assets,
    any release verb that reads a notes file, `gh repo create/edit/delete`, `glab repo
    create/update/delete/transfer/mirror`, any `api` call whose method is
    not GET (a body flag implies POST), and the token-printing forms
    (`gh auth token`, `auth status --show-token`, `config get token`,
    `glab token create/rotate`).

  ask (permissionDecision "ask"): every other verb that is not a
    recognized read, any alias or extension (its expansion is invisible
    here), `api` calls that redirect the host (`--hostname`, a full URL,
    a GH_/GITLAB_ variable) or read a local file into a GET, GraphQL
    mutations, any gated call carrying a variable or command substitution,
    and a gated CLI reached through a wrapper or interpreter.

  allow (exit 0, no output): reads (list/view/status/diff/checks/...),
    `gh search`, and GET or read-only GraphQL `api` calls.

  ntn: blocks `files create` (an upload), `workers deploy`, `workers env
    set/push` (secrets to the worker), `auth token`, and an `api` call
    that attaches `--file`. Allows `pages get`, `datasources`, `files
    get/list`, `workers get/list`, GET `api` calls and the POST reads
    Notion exposes (`search`, `.../query`). Asks on everything else,
    which includes `pages create/edit`, the research skill's delivery path.

  bru: asks on everything but help and version. A collection is a
    file the agent can write, and a run sends whatever requests it
    lists to whatever hosts they name, so no `run` shape is read-only.

The /pr skill's apply.py opens the PR/MR in a subprocess, so this hook
never sees that `gh pr create`.

Segment splitting respects quotes but not every shell construct; where it
cannot place a word it asks rather than allows. What no text gate can see
is a command name assembled at runtime (`${G}h`, base64 into a shell), so
this catches mistakes and naive injections, not a determined adversary.
block beats ask beats allow when a compound command mixes tiers.
Fail-closed for these CLIs; fail-open only when stdin is not valid
hook JSON. It is a guardrail plus a tripwire, not a kernel boundary.
"""

import json
import os
import re
import shlex
import sys

FORGES = ("gh", "glab")
NOTION, BRUNO = "ntn", "bru"
CLIS = (*FORGES, NOTION, BRUNO)
CLI_ALTERNATION = "|".join(re.escape(cli) for cli in CLIS)

CLI_WORD_RE = re.compile(rf"(?<![\w.-])(?:{CLI_ALTERNATION})(?![\w./-])")

QUOTING_RE = re.compile(r"[\"'\\]")

PATH_TO_CLI_RE = re.compile(rf"/(?:{CLI_ALTERNATION})$")

# A substitution runs its text, and a leading `!` is how a git alias shells out.
SHELL_ESCAPE_RE = re.compile(r"\$\(|`|(?:^|=)!")

ENV_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

REDIRECT_ENV_RE = re.compile(r"\b(?:GH|GITHUB|GLAB|GITLAB|NOTION)_[A-Z_]*=")

SHELL_KEYWORDS = {"do", "then", "else", "elif", "if", "while", "until", "time", "!", "{"}

SEGMENT_BREAKS = set(";&|\n()")

EVALUATORS = {"bash", "sh", "zsh", "fish", "dash", "ksh", "eval"}

INTERPRETERS = {"python", "python3", "node", "perl", "ruby", "osascript"}

ARG_FLAGS = {"-R", "--repo", "-g", "--group"}

READ_VERBS = {"list", "ls", "view", "status", "diff", "checks", "watch", "item-list", "field-list"}

HELP_FLAGS = {"-h", "--help"}

TOP_LEVEL_READS = {
    "gh": {"search", "status", "version", "help"},
    "glab": {"search", "version", "help"},
}

# Built-in groups only: anything else is an alias or an extension, whose read-looking
# verb says nothing about what it expands to.
GROUPS = {
    "gh": {
        "agent-task", "alias", "attestation", "auth", "browse", "cache", "codespace", "config",
        "discussion", "extension", "gist", "gpg-key", "issue", "label", "org", "pr", "preview",
        "project", "release", "repo", "ruleset", "run", "secret", "skill", "ssh-key", "variable",
        "workflow",
    },
    "glab": {
        "alias", "attestation", "auth", "changelog", "ci", "cluster", "config", "container-registry",
        "deploy-key", "gpg-key", "incident", "issue", "iteration", "job", "label", "milestone", "mr",
        "packages", "release", "repo", "runner", "schedule", "securefile", "snippet", "ssh-key",
        "stack", "todo", "token", "user", "variable", "work-items",
    },
}

EXTRA_READS = {
    "glab": {("ci", "trace"), ("ci", "get")},
}

ASK_GROUPS = {
    "glab": {"variable"},
}

BLOCKED_VERBS = {
    "gh": {
        "gist": {"create", "new", "edit"},
        "secret": {"set"},
        "variable": {"set"},
        "release": {"upload"},
        "repo": {"create", "new", "edit", "delete"},
    },
    "glab": {
        "snippet": {"create", "new"},
        "variable": {"set", "update", "import"},
        "securefile": {"create", "update"},
        "release": {"upload"},
        "repo": {"create", "new", "update", "delete", "transfer", "mirror"},
        "token": {"create", "rotate"},
    },
}

RELEASE_CREATE_VERBS = {"create", "new"}

RELEASE_CREATE_ARG_FLAGS = {
    "-n", "--notes", "-N", "-t", "--title", "--target", "--discussion-category",
    "--notes-start-tag", "-R", "--repo", "-a", "--assets-links", "-m", "--milestone",
    "--name", "--package-name", "-r", "--ref", "-D", "--released-at", "-T", "--tag-message",
}
NOTES_FILE_FLAGS = {"-F", "--notes-file"}

API_METHOD_FLAGS = {"-X", "--method"}
API_FIELD_FLAGS = {"-f", "-F", "--field", "--raw-field", "--form"}
API_INPUT_FLAGS = {"--input"}
API_HOST_FLAGS = {"--hostname"}
API_OTHER_ARG_FLAGS = {
    "-H", "--header", "-q", "--jq", "-t", "--template", "--cache", "-p", "--preview", "--output",
}
READ_METHODS = {"GET", "HEAD"}
GRAPHQL_ENDPOINT = "graphql"
MUTATION_RE = re.compile(r"\bmutation\b")

SHOW_TOKEN_RE = re.compile(r"^(?:--show-token(?:=.*)?|-[A-Za-z]*t[A-Za-z]*)$")

NOTION_ARG_FLAGS = {"--workers-config-file"}
NOTION_BOOL_FLAGS = {"-v", "--verbose", "-V", "--version"}
NOTION_TOP_LEVEL_READS = {"whoami", "doctor", "help"}
NOTION_BLOCKED = {
    ("files", "create"): "a Notion file upload",
    ("workers", "deploy"): "a Notion worker deploy, which ships local code",
    ("auth", "token"): "`ntn auth token`, which prints a live credential",
}
NOTION_BLOCKED_ENV_VERBS = {"set", "push"}
NOTION_READS = {
    ("pages", "get"), ("datasources", "query"), ("datasources", "resolve"),
    ("files", "get"), ("files", "list"), ("files", "ls"),
    ("workers", "get"), ("workers", "list"), ("workers", "ls"), ("workers", "usage"),
    ("api", "ls"),
}
NOTION_API_METHOD_FLAGS = {"-X", "--method"}
NOTION_API_DATA_FLAGS = {"-d", "--data"}
NOTION_API_FILE_FLAGS = {"--file"}
NOTION_API_OTHER_ARG_FLAGS = {"--notion-version"}
NOTION_API_DOC_FLAGS = {"--spec", "--docs", "-h", "--help"}
# Notion's search and query endpoints are POST, but they only read.
NOTION_POST_READ_RE = re.compile(r"(?:^|/)(?:search|query)/?$")
NOTION_QUERY_PARAM_RE = re.compile(r"^[^=:]+==")
NOTION_BODY_INPUT_RE = re.compile(r"^[^=:]+:?=")

BRUNO_READS = {"--version", "--help", "-h"}

MAX_DEPTH = 3

BLOCK, ASK = "block", "ask"


def rank(verdict):
    return {None: 0, ASK: 1, BLOCK: 2}[verdict[0]]


def worst(*verdicts):
    return max(verdicts, key=rank)


ALLOWED = (None, None)


def segments(command):
    """(text, expands, piped) per simple command, split on unquoted ; & | ( ) and newlines.

    `expands` is whether a `$` or backtick sits outside single quotes, where the
    shell would substitute it before the CLI ever sees the argument. `piped` is
    whether a single `|` feeds the command its stdin, which some CLIs send as a body.
    """
    out, buf, expands, piped, quote = [], [], False, False, None
    i = 0
    while i < len(command):
        c = command[i]
        before, after = command[i - 1:i], command[i + 1:i + 2]
        if quote == "'":
            buf.append(c)
            if c == "'":
                quote = None
        elif c == "\\" and i + 1 < len(command):
            buf.append(command[i:i + 2])
            i += 1
        elif quote == '"':
            buf.append(c)
            if c == '"':
                quote = None
            elif c in "$`":
                expands = True
        elif c in "'\"":
            quote = c
            buf.append(c)
        elif c == "`":
            out.append(("".join(buf), True, piped))
            buf, expands, piped = [], True, False
        elif c in SEGMENT_BREAKS:
            pipe = c == "|" and "|" not in (before, after)
            if "".join(buf).strip():
                out.append(("".join(buf), expands, piped))
                buf, expands, piped = [], False, pipe
            else:
                piped = piped or pipe
        else:
            if c == "$":
                expands = True
            buf.append(c)
        i += 1
    out.append(("".join(buf), expands, piped))
    return [(text.strip(), expands, piped) for text, expands, piped in out if text.strip()]


def tokenize(text):
    try:
        return shlex.split(text, comments=False, posix=True)
    except ValueError:
        return text.split()


def runs_cli(token):
    return token in CLIS or bool(PATH_TO_CLI_RE.search(token))


def mentions_cli(text):
    return bool(CLI_WORD_RE.search(QUOTING_RE.sub("", text)))


def first_positional(args, arg_flags):
    return locate_positional(args, arg_flags)[0]


def locate_positional(args, arg_flags, bool_flags=frozenset()):
    """The first positional's index, and whether an unknown flag before it might own it.

    gh and glab accept a subcommand's own flags ahead of it, and one that takes a
    value swallows the next word, so `gh gist -d list create` runs `gist create`.
    """
    i, ambiguous = 0, False
    while i < len(args):
        token = args[i]
        if not token.startswith("-") or token == "-":
            return i, ambiguous
        if token in arg_flags:
            i += 2
            continue
        if "=" not in token and token not in HELP_FLAGS and token not in bool_flags:
            ambiguous = True
        i += 1
    return None, ambiguous


def api_verdict(cli, args):
    method, fields, file_input, redirect, endpoint = None, [], False, False, None
    i = 0
    while i < len(args):
        token = args[i]
        value = args[i + 1] if i + 1 < len(args) else ""
        flag, eq, attached = token.partition("=")
        if token in API_METHOD_FLAGS:
            method, i = value, i + 2
            continue
        if flag == "--method" and eq:
            method = attached
        elif token.startswith("-X") and len(token) > 2:
            method = token[2:]
        elif token in API_FIELD_FLAGS:
            fields.append(value)
            i += 2
            continue
        elif flag in API_FIELD_FLAGS and eq:
            fields.append(attached)
        elif token[:2] in ("-f", "-F") and len(token) > 2 and not token.startswith("--"):
            fields.append(token[2:])
        elif token in API_INPUT_FLAGS or (flag in API_INPUT_FLAGS and eq):
            file_input = True
            i += 1 if eq else 2
            continue
        elif token in API_HOST_FLAGS or (flag in API_HOST_FLAGS and eq):
            redirect = True
            i += 1 if eq else 2
            continue
        elif token in API_OTHER_ARG_FLAGS:
            i += 2
            continue
        elif not token.startswith("-") and endpoint is None:
            endpoint = token
        i += 1

    if endpoint and "://" in endpoint:
        redirect = True
    reads_file = file_input or any(f.startswith("@") or "=@" in f for f in fields)
    effective = (method or ("POST" if fields or file_input else "GET")).upper()

    if endpoint == GRAPHQL_ENDPOINT:
        if reads_file or any(MUTATION_RE.search(f) for f in fields):
            verdict = (ASK, f"a {cli} api GraphQL call that is a mutation or reads its document from a file")
        else:
            verdict = ALLOWED
    elif effective not in READ_METHODS:
        verdict = (BLOCK, f"a {cli} api {effective} request, which writes local data to the forge")
    elif reads_file:
        verdict = (ASK, f"a {cli} api request that reads a local file into its parameters")
    else:
        verdict = ALLOWED
    if redirect:
        verdict = worst(verdict, (ASK, f"a {cli} api request sent to a host or URL named on the command line"))
    return verdict


def reads_notes_file(args):
    return any(t.partition("=")[0] in NOTES_FILE_FLAGS for t in args)


def release_create_verdict(cli, args):
    positionals, i = 0, 0
    while i < len(args):
        token = args[i]
        if token.startswith("-") and token != "-":
            i += 2 if token in RELEASE_CREATE_ARG_FLAGS else 1
            continue
        positionals += 1
        i += 1
    if positionals > 1:
        return BLOCK, f"a {cli} release create that uploads local files as release assets"
    return ASK, f"a {cli} release create, which publishes to the forge"


def notion_api_verdict(args, stdin_fed):
    if any(t in NOTION_API_DOC_FLAGS for t in args):
        return ALLOWED
    method, path, body, reads_file, i = None, None, stdin_fed, stdin_fed, 0
    while i < len(args):
        token = args[i]
        value = args[i + 1] if i + 1 < len(args) else ""
        flag, eq, attached = token.partition("=")
        if flag in NOTION_API_FILE_FLAGS:
            return BLOCK, "an ntn api call that uploads a local file"
        if token in NOTION_API_METHOD_FLAGS or flag == "--method" and eq:
            method = attached if eq else value
            i += 1 if eq else 2
            continue
        if token.startswith("-X") and len(token) > 2:
            method = token[2:]
        elif token in NOTION_API_DATA_FLAGS:
            body, reads_file = True, reads_file or value.startswith("@")
            i += 2
            continue
        elif flag == "--data" and eq:
            body, reads_file = True, reads_file or attached.startswith("@")
        elif token.startswith("-d") and len(token) > 2:
            body, reads_file = True, reads_file or token[2:].lstrip("=").startswith("@")
        elif token in NOTION_API_OTHER_ARG_FLAGS:
            i += 2
            continue
        elif token.startswith("-"):
            pass
        elif path is None:
            path = token
        elif not NOTION_QUERY_PARAM_RE.match(token) and NOTION_BODY_INPUT_RE.match(token):
            body = True
        i += 1

    effective = (method or ("POST" if body else "GET")).upper()
    if effective in READ_METHODS:
        return ALLOWED
    if effective == "POST" and path and NOTION_POST_READ_RE.search(path):
        if reads_file:
            return ASK, "an ntn api search or query whose body comes from a file or stdin"
        return ALLOWED
    return ASK, f"an ntn api {effective} request, which writes to the Notion workspace"


def ambiguous_flag(cli):
    return ASK, f"a flag ahead of a {cli} subcommand that may swallow the word after it"


def notion_verdict(cli, args, stdin_fed=False):
    start, ambiguous = locate_positional(args, NOTION_ARG_FLAGS, NOTION_BOOL_FLAGS)
    if start is None:
        return ALLOWED
    if ambiguous:
        return worst(ambiguous_flag(cli), notion_verdict(cli, args[start:], stdin_fed),
                     notion_verdict(cli, args[start + 1:], stdin_fed))
    group, rest = args[start], args[start + 1:]
    if group in NOTION_TOP_LEVEL_READS:
        return ALLOWED
    if group == "api" and not (rest and rest[0] == "ls"):
        return notion_api_verdict(rest, stdin_fed)
    offset, ambiguous = locate_positional(rest, NOTION_ARG_FLAGS, NOTION_BOOL_FLAGS)
    if ambiguous:
        return worst(ambiguous_flag(cli), notion_verdict(cli, [group, *rest[offset:]], stdin_fed),
                     notion_verdict(cli, [group, *rest[offset + 1:]], stdin_fed))
    verb = rest[offset] if offset is not None else None
    after = rest[offset + 1:] if offset is not None else []
    if (group, verb) in NOTION_BLOCKED:
        return BLOCK, NOTION_BLOCKED[(group, verb)]
    if group == "workers" and verb == "env":
        index = first_positional(after, NOTION_ARG_FLAGS)
        sub = after[index] if index is not None else None
        if sub in NOTION_BLOCKED_ENV_VERBS:
            return BLOCK, f"`ntn workers env {sub}`, which sends local values to a worker"
    if (group, verb) in NOTION_READS:
        return ALLOWED
    if verb is None and any(t in HELP_FLAGS for t in rest):
        return ALLOWED
    return ASK, f"`ntn {group} {verb or ''}`, which is not a recognized read-only call"


def bruno_verdict(cli, args, stdin_fed=False):
    if args and all(t in BRUNO_READS for t in args):
        return ALLOWED
    return ASK, "a bru call, which sends whatever requests a collection lists to the hosts it names"


def cli_verdict(cli, args, stdin_fed=False):
    return VERDICTS[cli](cli, args, stdin_fed)


def forge_verdict(cli, args, stdin_fed=False):
    start, ambiguous = locate_positional(args, ARG_FLAGS)
    if start is None:
        return ALLOWED
    if ambiguous:
        return worst(ambiguous_flag(cli), forge_verdict(cli, args[start:]), forge_verdict(cli, args[start + 1:]))
    group, rest = args[start], args[start + 1:]
    if group == "api":
        return api_verdict(cli, rest)
    if group in TOP_LEVEL_READS[cli]:
        return ALLOWED
    offset, ambiguous = locate_positional(rest, ARG_FLAGS)
    if ambiguous:
        return worst(ambiguous_flag(cli), forge_verdict(cli, [group, *rest[offset:]]),
                     forge_verdict(cli, [group, *rest[offset + 1:]]))
    verb = rest[offset] if offset is not None else None
    after = rest[offset + 1:] if offset is not None else []

    if group not in GROUPS[cli]:
        return ASK, f"`{cli} {group}`, an alias or extension this gate cannot see into"
    if group == "auth" and verb == "token":
        return BLOCK, f"`{cli} auth token`, which prints a live credential"
    if group == "auth" and verb == "status" and any(SHOW_TOKEN_RE.match(t) for t in after):
        return BLOCK, f"`{cli} auth status` asked to print the token"
    if group == "config" and verb == "get" and any("token" in t for t in after):
        return BLOCK, f"`{cli} config get` on a token key"
    if verb in BLOCKED_VERBS[cli].get(group, ()):
        return BLOCK, f"`{cli} {group} {verb}`, which uploads or publishes data to the forge"
    if group == "release" and reads_notes_file(after):
        return BLOCK, f"a {cli} release {verb} that publishes a local file as its notes"
    if group == "release" and verb in RELEASE_CREATE_VERBS:
        return release_create_verdict(cli, after)
    if group in ASK_GROUPS.get(cli, ()):
        return ASK, f"`{cli} {group}`, whose values can hold CI secrets"
    if verb is None and any(t in HELP_FLAGS for t in rest):
        return ALLOWED
    if verb in READ_VERBS or (group, verb) in EXTRA_READS.get(cli, ()):
        return ALLOWED
    return ASK, f"`{cli} {group} {verb or ''}`, which is not a recognized read-only call"


VERDICTS = {**{forge: forge_verdict for forge in FORGES}, NOTION: notion_verdict, BRUNO: bruno_verdict}


def substitutions_verdict(tokens, depth):
    """A `$(...)` or backtick inside a quoted argument runs before the CLI does."""
    verdict = ALLOWED
    for token in tokens:
        if SHELL_ESCAPE_RE.search(token) and mentions_cli(token):
            verdict = worst(verdict, decide(token.replace("!", " ", 1), depth + 1))
    return verdict


def segment_verdict(text, expands, piped, depth):
    tokens = tokenize(text)
    i, env_prefix = 0, False
    while i < len(tokens) and (ENV_ASSIGNMENT_RE.match(tokens[i]) or tokens[i] in SHELL_KEYWORDS):
        env_prefix = env_prefix or bool(ENV_ASSIGNMENT_RE.match(tokens[i]))
        i += 1
    if i >= len(tokens):
        return ALLOWED
    stdin_fed = piped or any(t.startswith("<") for t in tokens[i + 1:])
    cli = os.path.basename(tokens[i])
    if cli in CLIS:
        verdict = worst(cli_verdict(cli, tokens[i + 1:], stdin_fed), substitutions_verdict(tokens[i + 1:], depth))
        if env_prefix:
            verdict = worst(verdict, (ASK, f"a {cli} call with an environment prefix, which can redirect its host or token"))
        if expands:
            verdict = worst(verdict, (ASK, f"a variable or command substitution inside a {cli} call, which this gate cannot validate"))
        return verdict
    if tokens[i].startswith("$"):
        return ASK, "a command name taken from a variable or substitution beside a gated CLI"
    wrapped = (ASK, "a gated CLI invoked through a wrapper, interpreter, or substitution instead of directly")
    verdict = ALLOWED
    for j in range(i + 1, len(tokens)):
        token = tokens[j]
        if runs_cli(token):
            return worst(verdict, wrapped, cli_verdict(os.path.basename(token), tokens[j + 1:], stdin_fed))
        if not mentions_cli(token):
            continue
        evaluated = any(os.path.basename(t) in EVALUATORS for t in tokens[i:j])
        if evaluated or SHELL_ESCAPE_RE.search(token):
            verdict = worst(verdict, wrapped, decide(token.replace("!", " ", 1), depth + 1))
        elif os.path.basename(tokens[i]) in INTERPRETERS:
            verdict = worst(verdict, wrapped)
    return verdict


def decide(command, depth=0):
    if not mentions_cli(command):
        return ALLOWED
    if depth > MAX_DEPTH:
        return ASK, "gated CLI calls nested too deeply for this gate to read"
    verdict = ALLOWED
    if REDIRECT_ENV_RE.search(command):
        verdict = (ASK, "a gh, glab or ntn environment variable set beside the call, which can redirect its host or token")
    for text, expands, piped in segments(command):
        verdict = worst(verdict, segment_verdict(text, expands, piped, depth))
    return verdict


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    if (data.get("tool_name") or "") != "Bash":
        sys.exit(0)
    command = (data.get("tool_input") or {}).get("command") or ""
    if not command:
        sys.exit(0)

    try:
        verdict, reason = decide(command)
    except Exception:
        verdict, reason = ASK, "a gated CLI call the egress gate could not parse"

    if verdict == BLOCK:
        print(
            f"cli-egress-gate: blocked. This command contains {reason}. "
            "Reads (list/view/status/diff/checks, GET api calls) run without a prompt; "
            "run uploads, secret or variable writes and api writes in a real terminal instead.",
            file=sys.stderr,
        )
        sys.exit(2)
    if verdict == ASK:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": f"cli-egress-gate: command contains {reason}",
        }}))
    sys.exit(0)


if __name__ == "__main__":
    main()
