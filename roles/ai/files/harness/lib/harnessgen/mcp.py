"""Translate the shared MCP inventory and merge only names installed by this harness."""

import json
import re
from pathlib import Path

ENV_REF = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}\Z")
STATE_FILE = ".harness-mcp-owned.json"


def load(root):
    servers = json.loads((Path(root) / "mcp.json").read_text())
    if set(servers) != {"mcpServers"} or not isinstance(servers["mcpServers"], dict):
        raise ValueError("mcp.json must contain only an mcpServers object")
    for name, entry in servers["mcpServers"].items():
        if not isinstance(name, str) or not name:
            raise ValueError("mcp.json: server names must be non-empty strings")
        if not isinstance(entry, dict):
            raise ValueError(f"mcp.json: {name}: expected a server object")
        if entry.get("type") == "http":
            if set(entry) != {"type", "url"} or not isinstance(entry["url"], str):
                raise ValueError(f"mcp.json: {name}: unsupported HTTP fields")
        elif "command" in entry and entry.get("type", "stdio") == "stdio":
            if set(entry) - {"type", "command", "args", "env", "cwd"}:
                raise ValueError(f"mcp.json: {name}: unsupported stdio fields")
            if not isinstance(entry["command"], str) or not isinstance(entry.get("args", []), list) or any(not isinstance(arg, str) for arg in entry.get("args", [])):
                raise ValueError(f"mcp.json: {name}: invalid stdio command or args")
            if "cwd" in entry and not isinstance(entry["cwd"], str):
                raise ValueError(f"mcp.json: {name}: invalid cwd")
            env = entry.get("env", {})
            if not isinstance(env, dict) or any(not isinstance(key, str) or not isinstance(value, str) or not ENV_REF.fullmatch(value) for key, value in env.items()):
                raise ValueError(f"mcp.json: {name}: env must contain only variable references")
        else:
            raise ValueError(f"mcp.json: {name}: unsupported transport")
    return servers["mcpServers"]


def for_claude(entry):
    return entry if "type" in entry else {"type": "stdio", **entry}


def for_codex(entry):
    if entry.get("type") == "http":
        return {"url": entry["url"]}
    config = {key: entry[key] for key in ("command", "args", "cwd") if key in entry}
    if "env" in entry:
        config["env_vars"] = sorted({ENV_REF.fullmatch(value).group(1) for value in entry["env"].values()})
        if any(key != ENV_REF.fullmatch(value).group(1) for key, value in entry["env"].items()):
            raise ValueError("Codex cannot rename inherited stdio environment variables")
    return config


def plan(config, state_path, desired, key):
    old_names = set(json.loads(state_path.read_text())) if state_path.is_file() else set()
    installed = config.get(key, {})
    if not isinstance(installed, dict):
        raise ValueError(f"{key} must be an object")
    collisions = (desired.keys() - old_names) & installed.keys()
    if collisions:
        raise ValueError(f"unmanaged MCP server name collision: {', '.join(sorted(collisions))}")
    changes = sorted(name for name in old_names | desired.keys()
                     if (name in old_names and name not in desired) or
                     (name in installed) != (name in desired) or installed.get(name) != desired.get(name))
    return changes, sorted(desired)


def merge(config, key, old_names, desired):
    installed = config.setdefault(key, {})
    for name in old_names - desired.keys():
        installed.pop(name, None)
    installed.update(desired)


def names(state_path):
    return set(json.loads(state_path.read_text())) if state_path.is_file() else set()


def save_names(state_path, names):
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(names, indent=2) + "\n")
