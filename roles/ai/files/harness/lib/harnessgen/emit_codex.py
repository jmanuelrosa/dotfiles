"""Codex CLI's sandbox, approvals, execpolicy rules and hooks, from the neutral policy.

Codex has one sandbox and one rules engine, both coarser than Claude's, so this is the
emitter that drops the most. `untranslatable()` names every drop, and `harness-build
report` prints it.
"""

import json

from harnessgen import emit_claude, tomlw

NAME = "codex"
CONFIG = "adapters/codex/generated/config.owned.toml"
RULES = "adapters/codex/generated/rules/dotfiles.rules"
HOOKS = "adapters/codex/generated/hooks.json"

EVENTS = emit_claude.EVENTS
# Codex matches a regex against the tool name, so each is anchored to mean only itself.
TOOLS = {"bash": "^Bash$"}

RULES_HEADER = (
    "# Rendered by harness-build from policy/permissions.toml. Edit there, never here.\n"
    "# Each rule is a token prefix: anything after it matches too.\n"
)


def workspace_write(policy):
    """The sandbox's writable roots, and the network, which Codex can only switch off.

    `.` is the workspace, which workspace-write already opens, and which Codex would read
    relative to its own config directory. A `$VAR` is taken literally, and `$TMPDIR` is
    writable by default anyway. Codex has no domain allowlist, so the policy's domains
    have nowhere to go: network stays off, and a command that needs it asks to leave the
    sandbox under `on-request`.
    """
    writable = [p for p in policy["filesystem"]["allow_write"] if p != "." and not p.startswith("$")]
    return {"writable_roots": writable, "network_access": False}


def owned(manifest):
    """Dotted config.toml path to value, for every key `apply` replaces whole."""
    return {
        **manifest.adapter(NAME)["config"],
        "sandbox_workspace_write": workspace_write(manifest.sandbox),
    }


def prefix(pattern):
    """`git push --force *` as its tokens, or None when a wildcard is not a trailing one.

    execpolicy matches exact tokens and has no glob, so only a pure prefix translates.
    A pattern with no trailing `*` becomes a prefix too, which forbids it with arguments
    as well; for a deny that only ever widens the refusal.
    """
    tokens = pattern.split()
    if tokens and tokens[-1] == "*":
        tokens = tokens[:-1]
    if not tokens or any("*" in token for token in tokens):
        return None
    return tokens


def rule(tokens, source):
    return (
        "prefix_rule(\n"
        f"    pattern = {json.dumps(tokens)},\n"
        '    decision = "forbidden",\n'
        f"    justification = {json.dumps(f'denied by dotfiles policy: {source}')},\n"
        ")\n"
    )


def rules(manifest):
    """One forbidden rule per distinct prefix; `lazygit` and `lazygit *` are the same one."""
    seen, out = set(), [RULES_HEADER]
    for pattern in manifest.permissions["commands"]["deny"]:
        tokens = prefix(pattern)
        if tokens is None or tuple(tokens) in seen:
            continue
        seen.add(tuple(tokens))
        out.append("\n" + rule(tokens, pattern))
    return "".join(out)


def hook_entry(hook, hooks_dir):
    entry = {"type": "command", "command": hook.get("command") or f"{hooks_dir}/{hook['script']}"}
    if "timeout" in hook:
        entry["timeout"] = hook["timeout"]
    return entry


def hooks(manifest):
    """Every hook Codex is listed for, grouped like Claude's: by event, then by matcher."""
    hooks_dir = manifest.adapter(NAME)["hooks"]["dir"]
    out = {}
    for hook in manifest.hooks_for(NAME):
        groups = out.setdefault(EVENTS[hook["event"]], [])
        match = "|".join(TOOLS[tool] for tool in hook.get("tools", []))
        group = next((g for g in groups if g["matcher"] == match), None)
        if group is None:
            group = {"matcher": match, "hooks": []}
            groups.append(group)
        group["hooks"].append(hook_entry(hook, hooks_dir))
    return {"hooks": out}


def untranslatable(manifest):
    """Each policy rule Codex receives no counterpart for, as `section: rule`.

    The command allows are not among them: they exist to spare a prompt, and under
    `on-request` a command that stays inside the sandbox is never prompted for.
    """
    permissions, sandbox = manifest.permissions, manifest.sandbox
    kept = set(workspace_write(sandbox)["writable_roots"])
    return [
        *(f"commands.deny: {p}" for p in permissions["commands"]["deny"] if prefix(p) is None),
        *(f"paths.{kind}: {p}" for kind, patterns in permissions["paths"].items() for p in patterns),
        *(f"mcp.deny: {server}" for server in permissions["mcp"]["deny"]),
        *(f"tools.{kind}: {tool}" for kind, tools in permissions["tools"].items() for tool in tools),
        *(f"network.allow_domains: {d}" for d in sandbox["network"]["allow_domains"]),
        *(f"filesystem.allow_write: {p}" for p in sandbox["filesystem"]["allow_write"] if p not in kept),
        *(f"filesystem.{kind}: {p}" for kind in ("allow_read", "deny_read") for p in sandbox["filesystem"][kind]),
    ]


def files(manifest):
    """Relative path to the whole document: a dict for JSON, text for everything else."""
    return {
        CONFIG: tomlw.dumps(owned(manifest)),
        RULES: rules(manifest),
        HOOKS: hooks(manifest),
    }
