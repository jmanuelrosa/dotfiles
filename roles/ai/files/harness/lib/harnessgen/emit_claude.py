"""Claude Code's `permissions`, `sandbox`, `pluginConfigs`, `skillOverrides` and `hooks` keys, from the neutral policy."""

import re
from pathlib import PurePosixPath

from harnessgen import merge

NAME = "claude"
SETTINGS = "adapters/claude/settings.json"

EVENTS = {
    "pre_tool": "PreToolUse",
    "post_tool": "PostToolUse",
    "session_start": "SessionStart",
    "stop": "Stop",
    "prompt_submit": "UserPromptSubmit",
}
TOOLS = {"bash": "Bash", "write": "Write", "edit": "Edit", "exit_plan_mode": "ExitPlanMode"}
# SessionStart takes a source matcher rather than a tool one; Stop and UserPromptSubmit take none.
MATCH_EVERY_SOURCE = "*"
# Not `off` or `user-invocable-only`: the parent skill still loads its dependency through
# the Skill tool, so the dependency must stay invocable and only lose its description.
DEPENDENCY_ONLY_STATE = "name-only"


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
            # In user settings "." resolves to ~/.claude, not the project, and the
            # working directory is already writable without it.
            "allowWrite": [p for p in filesystem["allow_write"] if p != "."],
            "denyRead": list(filesystem["deny_read"]),
            "allowRead": list(filesystem["allow_read"]),
        },
    }


def rewrite_command(hook):
    """A rewrite hook as the one line Claude runs: skipped unless opted in and installed.

    `|| true` because a rewriter that fails has proposed nothing, and a nonzero exit from
    a PreToolUse hook would read to Claude as an error in the call instead.
    """
    return (
        f'if [ -n "${hook["requires_env"]}" ] && command -v {hook["exec"][0]} >/dev/null 2>&1; '
        f'then {" ".join(hook["exec"])} || true; fi'
    )


def hook_command(hook, hooks_dir):
    if hook.get("kind") == "rewrite":
        return rewrite_command(hook)
    return hook.get("command") or f"{hooks_dir}/{hook['script']}"


def hook_entries(hook, hooks_dir):
    """One Claude entry per `claude_if` rule, since an entry takes a single `if`."""
    command = hook_command(hook, hooks_dir)
    timeout = {"timeout": hook["timeout"]} if "timeout" in hook else {}
    rules = hook.get("claude_if") or [None]
    return [
        {"type": "command", "command": command, **({"if": rule} if rule else {}), **timeout}
        for rule in rules
    ]


def matcher(hook):
    if "tools" in hook:
        return "|".join(TOOLS[tool] for tool in hook["tools"])
    if hook["event"] == "session_start":
        return MATCH_EVERY_SOURCE
    return None


def hooks(manifest, hooks_dir):
    """Every managed hook, grouped by event and then by matcher, in manifest order."""
    out = {}
    for hook in manifest.hooks_for(NAME):
        groups = out.setdefault(EVENTS[hook["event"]], [])
        match = matcher(hook)
        group = next((g for g in groups if g.get("matcher") == match), None)
        if group is None:
            group = {"matcher": match, "hooks": []} if match else {"hooks": []}
            groups.append(group)
        group["hooks"] += hook_entries(hook, hooks_dir)
    return out


def commands_in(block):
    return {h.get("command") for groups in block.values() for g in groups for h in g.get("hooks", [])}


def managed_view(block, commands):
    """`block` with every hook this generator does not render taken out.

    What is compared for drift, so an entry herdr appends is never reported, while a
    managed entry edited, dropped or reordered by hand is.
    """
    out = {}
    for event, groups in block.items():
        kept = []
        for group in groups:
            ours = [h for h in group.get("hooks", []) if h.get("command") in commands]
            if ours:
                kept.append({**group, "hooks": ours})
        if kept:
            out[event] = kept
    return out


def merge_hooks(block, rendered):
    """The rendered hooks, with every foreign entry in `block` kept after them.

    A hook is ours when its command is one this generator renders. A foreign hook in a
    group whose matcher a managed group shares joins that group, after the managed
    entries; any other foreign group stays whole, after the managed groups of its event.
    Events keep the order `block` gave them.
    """
    ours = commands_in(rendered)
    out = {}
    for event in [*block, *(e for e in rendered if e not in block)]:
        groups = [{**g, "hooks": list(g["hooks"])} for g in rendered.get(event, [])]
        managed = {g.get("matcher"): g for g in groups}
        for group in block.get(event, []):
            foreign = [h for h in group.get("hooks", []) if h.get("command") not in ours]
            if not foreign:
                continue
            home = managed.get(group.get("matcher"))
            if home is not None:
                home["hooks"] += foreign
            else:
                groups.append({**group, "hooks": foreign})
        if groups:
            out[event] = groups
    return out


def skill_name(entry):
    """The name kura installs a registry entry under: its rename, else its upstream directory."""
    return entry.get("name") or PurePosixPath(entry["upstream_path"]).name


def dependency_only_skills(registry):
    entries = [skill for repo in registry["upstream"].values() for skill in repo["skills"]]
    entries += registry.get("local", [])
    return [skill_name(entry) for entry in entries if entry.get("dependency_only")]


def skill_overrides(registry, adapter_overrides):
    """Every dependency-only skill reduced to its name, with the adapter's own entries winning."""
    derived = {name: DEPENDENCY_ONLY_STATE for name in dependency_only_skills(registry)}
    return {**derived, **adapter_overrides}


def owned(manifest):
    """Dotted settings path to value, for every key this generator replaces whole."""
    adapter = manifest.adapter(NAME)
    rendered = {
        "permissions": permissions(manifest.permissions),
        "sandbox": sandbox(manifest.sandbox, adapter["sandbox"]),
        "skillOverrides": skill_overrides(manifest.skill_registry(), adapter.get("skill_overrides", {})),
    }
    for plugin, config in adapter.get("plugin_configs", {}).items():
        rendered[f"pluginConfigs.{plugin}"] = config
    return rendered


def rendered_hooks(manifest):
    return hooks(manifest, manifest.adapter(NAME)["hooks"]["dir"])


def apply(settings, manifest):
    """`settings` with every owned key replaced and the managed hooks merged in."""
    for key, value in owned(manifest).items():
        merge.put(settings, key, value)
    settings["hooks"] = merge_hooks(settings.get("hooks", {}), rendered_hooks(manifest))
    return settings


def drifted(settings, manifest):
    """The owned keys of `settings` that no longer match, `hooks` included."""
    found = [key for key, value in owned(manifest).items() if merge.get(settings, key) != value]
    rendered = rendered_hooks(manifest)
    if managed_view(settings.get("hooks", {}), commands_in(rendered)) != rendered:
        found.append("hooks")
    return found
