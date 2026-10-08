#!/usr/bin/env python3
"""Rank the read-only shell and MCP calls the shared permission policy still prompts for.

Reads Claude Code and Pi transcripts, reduces every shell call to its command and
read-only subcommand, keeps only what is safe to pre-approve, subtracts what
policy/permissions.toml already allows and what Claude Code never prompts for, and
ranks the rest by how often it ran.

Biased toward silence: a command this script cannot prove read-only is left out rather
than proposed, because a wrong allow rule is a standing grant and a missed one only
costs another prompt.
"""

import argparse
import json
import os
import re
import shlex
import sys
import tomllib
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dotkit import ui  # noqa: E402

HARNESS = Path(__file__).resolve().parents[5]
DEFAULT_POLICY = HARNESS / "policy" / "permissions.toml"
DEFAULT_MIN_COUNT = 3
DEFAULT_TOP = 20
DEFAULT_SESSIONS = 50
SKIPPED_SHOWN = 10

AUTO_ALLOWED = "auto-allowed"
ARBITRARY_EXEC = "arbitrary-exec"
NOT_READ_ONLY = "not-read-only"
SENSITIVE = "sensitive"
POLICY_ALLOWED = "policy-allowed"
POLICY_DENIED = "policy-denied"
BELOW_THRESHOLD = "below-threshold"

# Claude Code's own read-only validation. Calls matching these never prompt there, so a
# rule for them is noise.
AUTO_ANY = frozenset(
    "cal uptime cat head tail wc stat strings hexdump od nl id uname free df du locale "
    "groups nproc basename dirname realpath cut paste tr column tac rev fold expand "
    "unexpand fmt comm cmp numfmt readlink diff true false sleep which type expr seq "
    "tsort pr echo ls cd".split()
)
AUTO_NO_ARGS = frozenset({"pwd", "whoami", "alias"})
AUTO_EXACT = frozenset(
    {
        ("claude", "-h"),
        ("claude", "--help"),
        ("node", "-v"),
        ("node", "--version"),
        ("python", "--version"),
        ("python3", "--version"),
        ("ip", "addr"),
    }
)
AUTO_VALIDATED = frozenset(
    "xargs file sed sort man help netstat ps base64 grep egrep fgrep sha256sum sha1sum "
    "md5sum tree date hostname lsof pgrep tput ss fd fdfind aki rg jq uniq history arch "
    "ifconfig find printf test".split()
)
AUTO_PREFIXES = frozenset(
    tuple(prefix.split())
    for prefix in (
        "git status",
        "git log",
        "git diff",
        "git show",
        "git blame",
        "git branch",
        "git tag",
        "git remote",
        "git ls-files",
        "git ls-remote",
        "git rev-parse",
        "git rev-list",
        "git describe",
        "git stash list",
        "git stash show",
        "git reflog",
        "git shortlog",
        "git cat-file",
        "git for-each-ref",
        "git worktree list",
        "git merge-base",
        "git show-ref",
        "git grep",
        "git name-rev",
        "git config",
        "gh pr view",
        "gh pr list",
        "gh pr diff",
        "gh pr checks",
        "gh pr status",
        "gh issue view",
        "gh issue list",
        "gh issue status",
        "gh run view",
        "gh run list",
        "gh workflow list",
        "gh workflow view",
        "gh repo view",
        "gh release view",
        "gh release list",
        "gh auth status",
        "gh search",
        "docker ps",
        "docker images",
        "docker logs",
        "docker inspect",
    )
)

# A wildcard rule over any of these is a rule allowing arbitrary code.
INTERPRETER = re.compile(r"(python|pypy|ruby|perl|php|lua|node|bun|deno|java|R)[\d.]*")
EXEC_COMMANDS = frozenset(
    "sh bash zsh fish dash ksh csh tcsh nu pwsh eval exec source ssh mosh script expect "
    "tmux screen watch xargs parallel awk gawk mawk nawk osascript swift kotlin scala "
    "groovy irb pry ghci julia rscript tclsh wish npx bunx pnpx uvx pipx rtk sudo doas "
    "su pyright basedpyright make gmake just task rake gradle gradlew mvn ant ninja turbo "
    "nx lerna dotenv direnv nix-shell".split()
)
EXEC_SUBCOMMANDS = frozenset(
    tuple(prefix.split())
    for prefix in (
        "npm run",
        "npm run-script",
        "npm exec",
        "npm x",
        "npm test",
        "npm t",
        "npm start",
        "npm restart",
        "npm stop",
        "yarn run",
        "yarn exec",
        "yarn dlx",
        "yarn test",
        "yarn start",
        "pnpm run",
        "pnpm exec",
        "pnpm dlx",
        "pnpm test",
        "pnpm start",
        "uv run",
        "uv tool",
        "poetry run",
        "pdm run",
        "hatch run",
        "pipenv run",
        "conda run",
        "cargo run",
        "go run",
        "go generate",
        "go test",
        "dotnet run",
        "deno task",
        "mise exec",
        "mise x",
        "mise run",
        "asdf exec",
        "nix run",
        "nix develop",
        "gh api",
        "glab api",
        "docker run",
        "docker exec",
        "docker compose run",
        "docker compose exec",
        "podman run",
        "podman exec",
        "kubectl exec",
        "kubectl run",
        "kubectl debug",
        "kubectl attach",
    )
)
EXEC_WORDS = frozenset({"run", "exec", "x", "dlx", "eval", "shell", "ssh", "console", "repl"})
EXEC_FLAGS = frozenset({"-exec", "-execdir", "-ok", "-okdir"})

# Single-purpose tools with no write or exec mode, so `cmd *` is as narrow as it gets.
READ_ONLY_COMMANDS = frozenset(
    "sw_vers system_profiler mdfind mdls otool nm shasum md5 eza exa tokei dig nslookup "
    "host whois ping traceroute vm_stat iostat w who users last zipinfo".split()
)
# A subcommand word that only reads, wherever it sits in the first three words. Not
# `version`: `npm version patch` bumps, commits and tags.
READ_ONLY_VERBS = frozenset(
    "status log logs diff show list ls view get describe inspect info search whoami "
    "outdated doctor help explain top history tree why read current deps leaves uses ps "
    "images checks".split()
)
MUTATING_WORDS = frozenset(
    "add apply approve cancel clean close cp create delete deploy destroy disable drop "
    "edit enable install kill login logout merge mv patch prune publish purge push put "
    "remove rename rerun reset restart revert rm rollback scale set start stop sync "
    "uninstall update upgrade upload write".split()
)
# Wider than the shell set because an MCP tool name is all verb, while a shell word after
# the subcommand is as likely a package or resource name (`npm view react`).
MCP_MUTATING_WORDS = MUTATING_WORDS | frozenset(
    "append archive assign change comment complete execute insert invite join label leave "
    "mark modify move mute pin post react replace reply run save schedule send share star "
    "store submit toggle transition trigger unarchive unpin".split()
)
EXCLUDED_KEYS = frozenset({("go", "get")})
VERSION_FLAGS = frozenset({"--version", "-V", "version", "--help", "-h", "help"})
SECRET_COMMANDS = frozenset(
    {"op", "security", "pass", "gopass", "bw", "lpass", "vault", "printenv", "env", "pbpaste"}
)
SECRET_WORD = re.compile(r"token|secret|password|credential|keychain")
# Read-only prefixes whose wildcard would also reach secrets (`kubectl get secret`,
# `kubectl config view --raw`), so only an exact or longer observed prefix may be allowed.
WILDCARD_UNSAFE = frozenset(
    tuple(prefix.split())
    for prefix in ("kubectl get", "kubectl describe", "kubectl config view", "aws configure get")
)

MCP_READ_WORDS = frozenset({"read", "get", "list", "search", "view"})

COMMAND_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]*")
SUBCOMMAND_TOKEN = re.compile(r"[a-z][a-z0-9-]*")
SAFE_TOKEN = re.compile(r"[A-Za-z0-9._,:/=@%+-]+")
ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*")
HEREDOC = re.compile(r"(?<!<)<<-?(?!<)\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
PUNCTUATION = ";&|<>()\n"
SEPARATOR_CHARS = set(";|()\n")
REDIRECT_CHARS = set("<>")
SKIPPED_KEYWORDS = frozenset(
    {"!", "{", "}", "then", "do", "else", "elif", "and", "or", "not", "if", "while", "until",
     "time", "nohup", "command", "builtin", "caffeinate"}
)
BLOCK_KEYWORDS = frozenset({"for", "case", "select", "function", "done", "fi", "esac", "end", "in"})
MAX_WORDS = 3
MAX_EXACT_LENGTH = 100


def claude_projects():
    root = os.environ.get("CLAUDE_CONFIG_DIR")
    return (Path(root).expanduser() if root else Path.home() / ".claude") / "projects"


def pi_sessions():
    configured = os.environ.get("PI_CODING_AGENT_SESSION_DIR")
    if configured:
        return Path(configured).expanduser()
    agent = os.environ.get("PI_CODING_AGENT_DIR")
    agent_dir = Path(agent).expanduser() if agent else Path.home() / ".pi" / "agent"
    try:
        setting = json.loads((agent_dir / "settings.json").read_text()).get("sessionDir")
    except (OSError, ValueError, AttributeError):
        setting = None
    if isinstance(setting, str) and Path(setting).expanduser().is_absolute():
        return Path(setting).expanduser()
    return agent_dir / "sessions"


def recent_transcripts(root, limit):
    if not root.is_dir():
        return []
    dated = []
    for path in root.rglob("*.jsonl"):
        try:
            dated.append((path.stat().st_mtime, path))
        except OSError:
            continue
    files = [path for _, path in sorted(dated, reverse=True)]
    return files if limit <= 0 else files[:limit]


def json_lines(path):
    try:
        handle = path.open(encoding="utf-8", errors="replace")
    except OSError:
        return
    with handle:
        for line in handle:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if isinstance(entry, dict):
                yield entry


def content_blocks(message):
    content = message.get("content") if isinstance(message, dict) else None
    return [block for block in content if isinstance(block, dict)] if isinstance(content, list) else []


def claude_calls(path):
    """`(id, kind, value)` for every Bash and MCP `tool_use` an assistant turn made."""
    for entry in json_lines(path):
        if entry.get("type") != "assistant":
            continue
        for block in content_blocks(entry.get("message")):
            if block.get("type") != "tool_use":
                continue
            name, arguments = block.get("name"), block.get("input") or {}
            if name == "Bash" and isinstance(arguments.get("command"), str):
                yield block.get("id"), "shell", arguments["command"]
            elif isinstance(name, str) and name.startswith("mcp__"):
                yield block.get("id"), "mcp", name


def pi_calls(path):
    """`(id, kind, value)` for every bash and `mcp__`-named `toolCall` an assistant message made.

    Calls through Pi's `mcp` proxy tool are not counted: they carry Pi's server names,
    which do not spell Claude Code's tool names, so a rule built from one would match
    nothing the policy renders.
    """
    for entry in json_lines(path):
        message = entry.get("message")
        if entry.get("type") != "message" or not isinstance(message, dict):
            continue
        if message.get("role") != "assistant":
            continue
        for block in content_blocks(message):
            if block.get("type") != "toolCall":
                continue
            name, arguments = block.get("name"), block.get("arguments") or {}
            if not isinstance(arguments, dict):
                continue
            if name == "bash" and isinstance(arguments.get("command"), str):
                yield block.get("id"), "shell", arguments["command"]
            elif isinstance(name, str) and name.startswith("mcp__"):
                yield block.get("id"), "mcp", name


def strip_heredocs(text):
    """Drop heredoc bodies, whose lines are data rather than commands."""
    out, pending = [], []
    for line in text.replace("\\\n", " ").split("\n"):
        if pending:
            if line.strip() == pending[0]:
                pending.pop(0)
            continue
        out.append(line)
        pending = [match.group(2) for match in HEREDOC.finditer(line)]
    return "\n".join(out)


def segments(command):
    """Each simple command in a shell string, as tokens, with redirections removed."""
    lexer = shlex.shlex(strip_heredocs(command), posix=True, punctuation_chars=PUNCTUATION)
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        return None
    out, current, skip_next = [], [], False
    for token in tokens:
        if skip_next:
            skip_next = False
            continue
        if token and set(token) <= set(PUNCTUATION):
            if set(token) & REDIRECT_CHARS and not set(token) & SEPARATOR_CHARS:
                if current and current[-1].isdigit():
                    current.pop()
                skip_next = True
                continue
            if current:
                out.append(current)
            current = []
            continue
        current.append(token)
    if current:
        out.append(current)
    return out


def skip_timeout(tokens):
    rest = tokens[1:]
    while rest and rest[0].startswith("-"):
        flag = rest.pop(0)
        if flag in ("-s", "-k", "--signal", "--kill-after"):
            rest = rest[1:]
    return rest[1:]


def skip_nice(tokens):
    rest = tokens[1:]
    if rest and rest[0] == "-n":
        return rest[2:]
    if rest and re.fullmatch(r"-\d+", rest[0]):
        return rest[1:]
    return rest


def skip_env(tokens):
    rest = tokens[1:]
    while rest and (rest[0].startswith("-") or ASSIGNMENT.fullmatch(rest[0])):
        flag = rest.pop(0)
        if flag in ("-u", "--unset", "-C", "--chdir"):
            rest = rest[1:]
    return rest or ["env"]


def strip_prefixes(tokens):
    """The command a segment runs, past env assignments and transparent wrappers."""
    while tokens:
        head = tokens[0]
        if ASSIGNMENT.fullmatch(head) or head in SKIPPED_KEYWORDS:
            tokens = tokens[1:]
        elif head == "timeout":
            tokens = skip_timeout(tokens)
        elif head == "nice":
            tokens = skip_nice(tokens)
        elif head == "env" and len(tokens) > 1:
            tokens = skip_env(tokens)
        else:
            return tokens
    return tokens


def subcommand_words(tokens):
    words = []
    for token in tokens[1 : 1 + MAX_WORDS]:
        if not SUBCOMMAND_TOKEN.fullmatch(token):
            break
        words.append(token)
    return words


def has_prefix(words, prefixes):
    return any(tuple(words[: len(prefix)]) == prefix for prefix in prefixes)


def classify(tokens):
    """`(reason, key)`: reason is None when `key` is a read-only command prefix."""
    command = tokens[0]
    words = subcommand_words(tokens)
    full = [command, *words]
    if EXEC_FLAGS & set(tokens):
        return ARBITRARY_EXEC, tuple(full[:2])
    if tuple(tokens) in AUTO_EXACT or has_prefix(full, AUTO_PREFIXES):
        return AUTO_ALLOWED, tuple(full[:2])
    if command in AUTO_ANY or command in AUTO_VALIDATED:
        return AUTO_ALLOWED, (command,)
    if command in AUTO_NO_ARGS and len(tokens) == 1:
        return AUTO_ALLOWED, (command,)
    if (
        command in EXEC_COMMANDS
        or INTERPRETER.fullmatch(command)
        or has_prefix(full, EXEC_SUBCOMMANDS)
    ):
        return ARBITRARY_EXEC, tuple(full[:2])
    if command in SECRET_COMMANDS or any(SECRET_WORD.search(token.lower()) for token in tokens):
        return SENSITIVE, tuple(full[:2])
    if command in READ_ONLY_COMMANDS:
        return None, (command,)
    if len(tokens) == 2 and tokens[1] in VERSION_FLAGS:
        return None, tuple(tokens)
    for index, word in enumerate(words):
        if word in READ_ONLY_VERBS:
            key = tuple(full[: index + 2])
            tail = set(words[index + 1 :])
            if tail & EXEC_WORDS:
                return ARBITRARY_EXEC, key
            if key in EXCLUDED_KEYS or tail & MUTATING_WORDS:
                return NOT_READ_ONLY, key
            return None, key
        if word in EXEC_WORDS:
            return ARBITRARY_EXEC, tuple(full[: index + 2])
        if word in MUTATING_WORDS:
            break
    return NOT_READ_ONLY, tuple(full[:2])


def shell_invocations(command):
    """`(reason, key, tokens)` for each simple command in a shell string."""
    parsed = segments(command)
    if parsed is None:
        return
    for raw in parsed:
        tokens = strip_prefixes(raw)
        if not tokens or tokens[0] in BLOCK_KEYWORDS:
            continue
        if not COMMAND_TOKEN.fullmatch(tokens[0]):
            continue
        reason, key = classify(tokens)
        yield reason, key, tuple(tokens)


def mcp_reason(name):
    parts = name.split("__", 2)
    if len(parts) < 3:
        return NOT_READ_ONLY
    words = set(re.split(r"[_\-]+", parts[2].lower()))
    if words & MCP_MUTATING_WORDS or not words & MCP_READ_WORDS:
        return NOT_READ_ONLY
    return None


def common_prefix(key, invocations):
    """The longest run of shared plain tokens every invocation starts with, never shorter than `key`."""
    prefix = list(key)
    shortest = min(len(tokens) for tokens in invocations)
    for position in range(len(key), shortest):
        column = {tokens[position] for tokens in invocations}
        if len(column) != 1:
            break
        (token,) = column
        if not SAFE_TOKEN.fullmatch(token) or token.startswith("-"):
            break
        prefix.append(token)
    return tuple(prefix)


def narrowest(key, invocations):
    """The tightest rule covering every observed invocation of `key`, or None if none is safe."""
    distinct = set(invocations)
    if distinct == {key}:
        return " ".join(key)
    if len(distinct) == 1:
        (only,) = distinct
        text = " ".join(only)
        if all(SAFE_TOKEN.fullmatch(token) for token in only) and len(text) <= MAX_EXACT_LENGTH:
            return text
    prefix = common_prefix(key, distinct)
    if prefix == key and key in WILDCARD_UNSAFE:
        return None
    return " ".join(prefix) + " *"


def split_rule(rule):
    return (rule[:-2], True) if rule.endswith(" *") else (rule, False)


def rule_covers(rule, pattern):
    """Whether a policy rule already matches everything `pattern` would allow."""
    rule_prefix, rule_wild = split_rule(rule)
    prefix, wild = split_rule(pattern)
    if rule_wild:
        return prefix == rule_prefix or prefix.startswith(rule_prefix + " ")
    return not wild and prefix == rule_prefix


def overlaps(rule, pattern):
    """Whether a wildcard `pattern` would also allow something `rule` names."""
    rule_prefix, _ = split_rule(rule)
    prefix, wild = split_rule(pattern)
    return wild and (rule_prefix == prefix or rule_prefix.startswith(prefix + " "))


def load_policy(path):
    data = tomllib.loads(path.read_text())
    commands, tools, mcp = data.get("commands", {}), data.get("tools", {}), data.get("mcp", {})
    return {
        "commands_allow": list(commands.get("allow", [])),
        "commands_deny": list(commands.get("deny", [])),
        "tools_allow": set(tools.get("allow", [])),
        "tools_deny": set(tools.get("deny", [])),
        "mcp_deny": list(mcp.get("deny", [])),
    }


def policy_reason(kind, pattern, policy):
    if kind == "mcp":
        if pattern in policy["tools_deny"] or any(
            pattern == f"mcp__{server}" or pattern.startswith(f"mcp__{server}__")
            for server in policy["mcp_deny"]
        ):
            return POLICY_DENIED
        return POLICY_ALLOWED if pattern in policy["tools_allow"] else None
    if any(rule_covers(rule, pattern) or overlaps(rule, pattern) for rule in policy["commands_deny"]):
        return POLICY_DENIED
    if any(rule_covers(rule, pattern) for rule in policy["commands_allow"]):
        return POLICY_ALLOWED
    return None


def mine(sources, policy, min_count, top):
    """Rank candidates from `{harness: [transcript, ...]}` against a loaded policy."""
    seen = set()
    shell = defaultdict(list)
    mcp = defaultdict(list)
    skipped = defaultdict(Counter)
    for harness, files in sources.items():
        reader = claude_calls if harness == "claude" else pi_calls
        for path in files:
            for call_id, kind, value in reader(path):
                if call_id is not None:
                    if (harness, call_id) in seen:
                        continue
                    seen.add((harness, call_id))
                if kind == "mcp":
                    reason = mcp_reason(value)
                    if reason:
                        skipped[reason][value] += 1
                    else:
                        mcp[value].append(harness)
                    continue
                for reason, key, tokens in shell_invocations(value):
                    if reason:
                        skipped[reason][" ".join(key)] += 1
                    else:
                        shell[key].append((harness, tokens))

    candidates = []
    for key, calls in shell.items():
        pattern = narrowest(key, [tokens for _, tokens in calls])
        if pattern is None:
            skipped[SENSITIVE][" ".join(key) + " *"] += len(calls)
            continue
        candidates.append(("shell", pattern, Counter(harness for harness, _ in calls)))
    for name, harnesses in mcp.items():
        candidates.append(("mcp", name, Counter(harnesses)))

    kept = []
    for kind, pattern, sources_count in candidates:
        count = sum(sources_count.values())
        reason = policy_reason(kind, pattern, policy)
        if reason is None and count < min_count:
            reason = BELOW_THRESHOLD
        if reason:
            skipped[reason][pattern] += count
            continue
        kept.append((kind, pattern, count, sources_count))

    kept.sort(key=lambda item: (-item[2], item[1]))
    ranked = [
        {
            "rank": rank,
            "pattern": pattern,
            "kind": kind,
            "section": "tools.allow" if kind == "mcp" else "commands.allow",
            "count": count,
            "sources": dict(sorted(sources_count.items())),
        }
        for rank, (kind, pattern, count, sources_count) in enumerate(kept[:top], start=1)
    ]
    return ranked, {
        reason: {
            "calls": sum(counter.values()),
            "top": [{"pattern": p, "count": c} for p, c in counter.most_common(SKIPPED_SHOWN)],
        }
        for reason, counter in sorted(skipped.items())
    }


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    parser.add_argument("--min-count", type=int, default=DEFAULT_MIN_COUNT,
                        help=f"drop patterns seen fewer times (default {DEFAULT_MIN_COUNT})")
    parser.add_argument("--top", type=int, default=DEFAULT_TOP,
                        help=f"how many candidates to rank (default {DEFAULT_TOP})")
    parser.add_argument("--sessions", type=int, default=DEFAULT_SESSIONS,
                        help="most recent transcripts read per harness, 0 for all "
                             f"(default {DEFAULT_SESSIONS})")
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY,
                        help="the neutral permissions.toml to subtract")
    parser.add_argument("--claude-projects", type=Path, default=None,
                        help="Claude Code transcript root (default $CLAUDE_CONFIG_DIR/projects)")
    parser.add_argument("--pi-sessions", type=Path, default=None,
                        help="Pi session root (default the configured Pi session directory)")
    return parser.parse_args(argv)


def report(result):
    ui.title("🔎 Permission rules worth adding")
    ui.note(f"policy {ui.path(result['policy'])}", indent=0)
    for candidate in result["candidates"]:
        origin = ", ".join(f"{h} {n}" for h, n in candidate["sources"].items())
        ui.item(f"{candidate['rank']:>2}. {candidate['pattern']}  ×{candidate['count']}  "
                f"[{candidate['section']}] ({origin})")
    if not result["candidates"]:
        ui.ok("Nothing new to allow")
    for reason, summary in result["skipped"].items():
        examples = ui.names_or_count([entry["pattern"] for entry in summary["top"]], "pattern")
        ui.note(f"skipped {reason}: {summary['calls']} calls ({examples})", indent=0)
    scanned = result["scanned"]
    ui.done(f"{len(result['candidates'])} candidates from "
            f"{scanned['claude']} Claude and {scanned['pi']} Pi transcripts")


def main(argv=None):
    args = parse_args(argv)
    policy_path = args.policy.expanduser().resolve()
    if not policy_path.is_file():
        ui.err(f"No policy at {ui.path(policy_path)}; pass --policy <permissions.toml>")
        return 1
    try:
        policy = load_policy(policy_path)
    except (tomllib.TOMLDecodeError, OSError) as error:
        ui.err(f"Cannot read {ui.path(policy_path)}: {error}")
        return 1
    sources = {
        "claude": recent_transcripts(args.claude_projects or claude_projects(), args.sessions),
        "pi": recent_transcripts(args.pi_sessions or pi_sessions(), args.sessions),
    }
    candidates, skipped = mine(sources, policy, args.min_count, args.top)
    result = {
        "policy": str(policy_path),
        "scanned": {harness: len(files) for harness, files in sources.items()},
        "thresholds": {"min_count": args.min_count, "top": args.top},
        "candidates": candidates,
        "skipped": skipped,
    }
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        report(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
