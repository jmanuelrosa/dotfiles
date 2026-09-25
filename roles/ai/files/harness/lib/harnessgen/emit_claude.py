"""Claude Code's `permissions`, `sandbox` and `pluginConfigs` keys, from the neutral policy."""

import re

NAME = "claude"
SETTINGS = "adapters/claude/settings.json"


def allow_command_rule(pattern):
    """`rg *` as `Bash(rg:*)`.

    Claude reads both spellings as the same prefix rule. The allow list has always used
    the colon one, so keeping it makes regenerating the file a no-op rather than a
    rewrite of every entry that changes no verdict.
    """
    prefix = re.fullmatch(r"([^*]+) \*", pattern)
    return f"Bash({prefix.group(1)}:*)" if prefix else f"Bash({pattern})"


def deny_command_rule(pattern):
    return f"Bash({pattern})"


def path_rule(tool, pattern):
    return f"{tool}({pattern})"


def mcp_rule(server):
    return f"mcp__{server}"


def path_denies(deny_read, deny_edit):
    """A path refused to both tools is written as an adjacent Read/Edit pair, in edit order."""
    out, paired = [], set()
    for pattern in deny_edit:
        if pattern in deny_read and pattern not in paired:
            out.append(path_rule("Read", pattern))
            paired.add(pattern)
        out.append(path_rule("Edit", pattern))
    out += [path_rule("Read", pattern) for pattern in deny_read if pattern not in paired]
    return out


def permissions(policy):
    commands, paths, tools = policy["commands"], policy["paths"], policy["tools"]
    return {
        "allow": [
            *tools["allow"],
            *(allow_command_rule(p) for p in commands["allow"]),
            *(path_rule("Edit", p) for p in paths["allow_edit"]),
        ],
        "deny": [
            *tools["deny"],
            *path_denies(paths["deny_read"], paths["deny_edit"]),
            *(deny_command_rule(p) for p in commands["deny"]),
            *(mcp_rule(s) for s in policy["mcp"]["deny"]),
        ],
    }


def sandbox(policy, knobs):
    network, filesystem = policy["network"], policy["filesystem"]
    return {
        **knobs,
        "network": {
            "allowedDomains": list(network["allow_domains"]),
            "allowLocalBinding": network["allow_local_binding"],
        },
        "filesystem": {
            "allowWrite": list(filesystem["allow_write"]),
            "denyRead": list(filesystem["deny_read"]),
            "allowRead": list(filesystem["allow_read"]),
        },
    }


def owned(manifest):
    """Dotted settings path to value, for every key this generator replaces."""
    adapter = manifest.adapter(NAME)
    rendered = {
        "permissions": permissions(manifest.permissions),
        "sandbox": sandbox(manifest.sandbox, adapter["sandbox"]),
    }
    for plugin, config in adapter.get("plugin_configs", {}).items():
        rendered[f"pluginConfigs.{plugin}"] = config
    return rendered
