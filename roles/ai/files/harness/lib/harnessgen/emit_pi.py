"""pi's two permission layers and its hook table, from the neutral policy.

`pi-sandbox` contains (sandbox.json) and `@gotgenes/pi-permission-system` decides
(permission-system/config.json). What each translation cannot carry, and why, is
specified in lib/python/tests/test_pi_sandbox.py and test_pi_permissions.py.

The guardrails extension reads generated/hooks.json at load, in place of a list of its
own; test_pi_guardrails.py pins what it does with each entry.
"""

import json
import re

from harnessgen import emit_claude, mcp

NAME = "pi"
SANDBOX = "adapters/pi/sandbox.json"
PERMISSIONS = "adapters/pi/permission-system/config.json"
HOOKS = "adapters/pi/generated/hooks.json"
MCP = "adapters/pi/generated/mcp.json"

# What guardrails needs from an entry. Timeouts stay in the extension, which states why
# a gate and a rewrite get different ones.
HOOK_FIELDS = ("id", "tools", "kind", "script", "exec", "requires_env", "env")

# Reads the harness itself makes of its own installed trees, which are outside any
# project and would otherwise meet `external_directory: ask` on every session. This is
# the knob the package documents for exactly that, and none of it is user data: pi's
# own docs and examples, and the two agent payload directories this repo owns and
# symlinks into place. A project path never belongs here.
INFRASTRUCTURE_READ_PATHS = [
    "/opt/homebrew/*/@earendil-works/pi-coding-agent/*",
    "~/.pi/agent/*",
    "~/.claude/*",
]

SHARED_SKILL_PATHS = [
    "~/.claude/skills/*",
    "~/.agents/skills/*",
]

# Tool surfaces pi gates that Claude never prompts for, listed so the universal
# fallback does not have to decide them. Claude auto-allows its read-only and
# orchestration tools in the same way.
SILENT_TOOLS = ("read", "grep", "find", "ls", "write", "edit")

# What `$TMPDIR` resolves to on Darwin. pi-sandbox expands only a leading `~`, so a
# literal `$TMPDIR` entry would match nothing.
DARWIN_TEMP_ROOT = "/var/folders"

CLAUDE_CONNECTOR_PREFIX = "claude_ai_"


def to_sandbox_pattern(pattern):
    """The "anywhere" prefix, made absolute.

    pi-sandbox runs any pattern containing `*` through `resolve()`, which anchors a
    relative one to the current directory. So `**/.env` would stop meaning "any .env"
    and start meaning "an .env under this project", which is a narrowing no reader of
    the policy would expect. A leading slash restores the original reach.
    """
    if pattern.startswith("**/"):
        return "/" + pattern
    return pattern


def unique(patterns):
    """In order, without repeats.

    The policy's two read layers overlap by design (`~/.npmrc` is both a sandbox
    deny_read and a path deny_read), and concatenating them is what makes a duplicate.
    pi matches with `.some()`, so a repeat changes no verdict; it is dropped because a
    derived file nobody hand-edits should not carry noise that reads like an oversight.
    """
    return list(dict.fromkeys(patterns))


def to_path_pattern(pattern):
    """A globstar, in a dialect where one star already recurses.

    `*` matches any run of characters including a separator and `**` is documented as
    equivalent, so the doubled form is not a second, wider token: it is the same token
    spelled twice. Collapsing it keeps `**/.env` matching `/project/.env` while still
    refusing to match `/project/settings.env`, which a naive `*.env` would have caught.
    """
    return pattern.replace("**", "*")


def denial(rule):
    """A refusal that says where it came from.

    A block whose reason is empty reads to the agent as an unexplained failure and it
    retries. Naming the rule turns it into something it can report back.
    """
    return {"action": "deny", "reason": f"denied by Claude Code policy: {rule}"}


def surface(fallback, allows, denies, trailing_allows=()):
    """One surface map, in the four bands that recover deny-beats-allow.

    Fallback first so every later pattern can override it, then the allows, then the
    denies that have to beat them. `trailing_allows` is the inversion: an allow that
    exists to carve an exception out of a deny, which under last-match-wins can only
    work after it.
    """
    out = {"*": fallback}
    denied = {pattern for pattern, _ in denies}
    for pattern in allows:
        if pattern not in denied:
            out[pattern] = "allow"
    for pattern, rule in denies:
        out[pattern] = denial(rule)
    for pattern in trailing_allows:
        out[pattern] = "allow"
    return out


def native_mcp_tool(server, tool="*"):
    """pi's registered name for an MCP tool, which is also its permission surface.

    pi's built-in MCP support registers each tool as `mcp__<server>__<tool>`, with any
    character outside letters, digits and `_` replaced by `_`, and runs it through the
    ordinary tool pipeline. The package's `mcp` surface is evaluated only for a proxy
    tool literally named `mcp`, so rules written there reach nothing.
    """
    return re.sub(r"[^A-Za-z0-9_*]", "_", f"mcp__{server}__{tool}")


def shared_servers(name, servers):
    """The shared servers a Claude MCP server name refers to.

    Claude names a claude.ai connector `claude_ai_Slack`, while pi reaches the same
    service through the shared inventory's bare `slack`.
    """
    wanted = name.lower().removeprefix(CLAUDE_CONNECTOR_PREFIX)
    return [server for server in servers if server.lower() == wanted]


def native_mcp_tools(rule, servers):
    """A Claude `mcp__<server>[__<tool>]` rule, renamed onto the shared servers pi connects.

    A rule that names no shared server yields nothing, so an allow pi cannot place stays
    at the `ask` fallback rather than widening onto a server it was not written for.
    """
    server, _, tool = rule.removeprefix("mcp__").partition("__")
    return [native_mcp_tool(shared, tool or "*") for shared in shared_servers(server, servers)]


def sandbox(manifest):
    network = manifest.sandbox["network"]
    filesystem = manifest.sandbox["filesystem"]
    paths = manifest.permissions["paths"]
    adapter = manifest.adapter(NAME)["sandbox"]
    allow_write = [p for p in filesystem["allow_write"] if not p.startswith("$")]
    return {
        "enabled": True,
        "excludedCommands": list(adapter["excludedCommands"]),
        "permissionPromptTimeoutSeconds": adapter["permissionPromptTimeoutSeconds"],
        "permissionPromptMaxAttempts": adapter["permissionPromptMaxAttempts"],
        "network": {
            "allowedDomains": list(network["allow_domains"]),
            "allowLocalBinding": bool(network["allow_local_binding"]),
        },
        "filesystem": {
            "allowWrite": allow_write + [DARWIN_TEMP_ROOT],
            "allowRead": unique(list(filesystem["allow_read"]) + adapter["filesystem"]["allowRead"]),
            "denyRead": unique(
                list(filesystem["deny_read"]) + [to_sandbox_pattern(p) for p in paths["deny_read"]]
            ),
            "denyWrite": unique(to_sandbox_pattern(p) for p in paths["deny_edit"]),
        },
    }


def permissions(manifest):
    policy = manifest.permissions
    commands, paths = policy["commands"], policy["paths"]
    rules = {
        "*": "allow",
        **{tool: "allow" for tool in SILENT_TOOLS},
        "bash": surface(
            "allow",
            list(commands["allow"]),
            [(p, emit_claude.deny_command_rule(p)) for p in commands["deny"]],
        ),
        "path_read": surface(
            "allow",
            [],
            [(to_path_pattern(p), emit_claude.path_rule("Read", p)) for p in paths["deny_read"]],
        ),
        "path_write": surface(
            "allow",
            [],
            [(to_path_pattern(p), emit_claude.path_rule("Edit", p)) for p in paths["deny_edit"]],
            [to_path_pattern(p) for p in paths["allow_edit"]],
        ),
        "external_directory": surface("ask", SHARED_SKILL_PATHS, []),
        "mcp": surface(
            "ask",
            [],
            [(f"{server}*", emit_claude.mcp_rule(server)) for server in policy["mcp"]["deny"]],
        ),
        native_mcp_tool("*"): "ask",
    }
    servers = mcp.load(manifest.root)
    for rule in policy["tools"]["allow"]:
        if rule.startswith("mcp__"):
            for name in native_mcp_tools(rule, servers):
                rules[name] = "allow"
    for server in policy["mcp"]["deny"]:
        rule = emit_claude.mcp_rule(server)
        for name in unique([native_mcp_tool(server), *native_mcp_tools(rule, servers)]):
            if not isinstance(rules.get(name), dict):
                rules[name] = {"*": denial(rule)}
    for name in policy["tools"]["deny"]:
        native = native_mcp_tools(name, servers) if name.startswith("mcp__") else []
        for target in unique([name, *native]):
            rules[target] = {"*": denial(name)}

    return {
        "debugLog": False,
        "permissionReviewLog": True,
        "yoloMode": False,
        "shellTools": {},
        "authorizerChain": [],
        "piInfrastructureReadPaths": list(INFRASTRUCTURE_READ_PATHS),
        "permission": rules,
    }


def hooks(manifest):
    """pi's hooks by neutral event, each entry carrying only what guardrails reads."""
    out = {}
    for hook in manifest.hooks_for(NAME):
        entry = {"kind": "gate", **hook}
        out.setdefault(hook["event"], []).append({k: entry[k] for k in HOOK_FIELDS if k in entry})
    return out


def files(manifest):
    """Relative path to the whole document, for every file this generator owns outright."""
    servers = mcp.load(manifest.root)
    overrides = json.loads((manifest.root / "adapters/pi/mcp.json").read_text())["mcpServers"]
    if overrides.keys() - servers.keys():
        raise ValueError("Pi MCP overrides must name shared servers")
    pi_servers = {name: {**entry, **overrides.get(name, {})} for name, entry in servers.items()}
    return {SANDBOX: sandbox(manifest), PERMISSIONS: permissions(manifest), HOOKS: hooks(manifest),
            MCP: {"mcpServers": pi_servers}}
