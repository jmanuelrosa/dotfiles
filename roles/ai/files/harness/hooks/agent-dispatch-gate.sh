#!/usr/bin/env python3
# vim: ft=python
# Filename keeps the .sh extension every hook in this directory carries, since the
# emitters spell a hook's path from its policy `script`. The shebang decides execution.
"""agent-dispatch-gate.sh: refuse a spawn of an agent that only its parent may dispatch.

Some agents exist as workers for one parent. code-review-worker is a sampling pass that
code-reviewer fans out and then verifies, and run from the main conversation it hands
unverified candidates to a reader who takes them as findings. No harness has a frontmatter
field that hides an agent from the Agent tool or from an @-mention, so the refusal happens
at dispatch: an agent whose frontmatter carries

    dispatched-by: [code-reviewer]

is spawned only when the payload's `agent_type`, the agent the call is made from, is in
that list. The main conversation carries no `agent_type` and is refused.

Claude sends the Agent tool's `subagent_type`. Pi's guardrails maps its `subagent` tool onto
the same payload, with the workflow script passed through so a child named inside
`runs.all([...])` is caught too; a Pi child never loads guardrails, so under Pi only the
main session's dispatch is gated, which is the one that needs it.

The agent file is read on every call rather than rendered into the hook, as
dependency-skill-gate reads the registry: the catalog's agents/ first, then the project's
and the user's agent directories, so a project-local worker is covered the same way.

Fail-open: an unreadable payload or agent file exits 0.
"""

import json
import os
import re
import sys
from pathlib import Path

CATALOG_ENV = "AGENT_CATALOG"
DEFAULT_CATALOG = "~/.config/kura/catalog"
PARENTS_KEY = "dispatched-by"
MAIN_THREAD = "main conversation"
REFUSED = 2

FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---", re.DOTALL)


def catalog_root():
    return Path(os.environ.get(CATALOG_ENV) or DEFAULT_CATALOG).expanduser()


def agent_dirs(cwd):
    project = Path(cwd)
    home = Path.home()
    return [
        catalog_root() / "agents",
        project / ".claude" / "agents",
        project / ".pi" / "agents",
        home / ".claude" / "agents",
        home / ".pi" / "agent" / "agents",
    ]


def parents_in(text):
    """The `dispatched-by` list of one agent file, inline or block form, or []."""
    match = FRONTMATTER.match(text)
    if not match:
        return []
    lines = match.group(1).splitlines()
    for index, line in enumerate(lines):
        key = re.match(rf"{PARENTS_KEY}:\s*(.*)$", line)
        if not key:
            continue
        inline = key.group(1).strip()
        if inline.startswith("["):
            return [item.strip().strip("'\"") for item in inline.strip("[]").split(",") if item.strip()]
        if inline:
            return [inline.strip("'\"")]
        block = []
        for following in lines[index + 1:]:
            item = re.match(r"\s+-\s*(.+)$", following)
            if not item:
                break
            block.append(item.group(1).strip().strip("'\""))
        return block
    return []


def parents_of(name, cwd):
    for directory in agent_dirs(cwd):
        path = directory / f"{name}.md"
        try:
            return parents_in(path.read_text(encoding="utf-8"))
        except OSError:
            continue
    return []


def gated_agents(cwd):
    """Every agent name that carries the key, for scanning a workflow script by name."""
    names = {}
    for directory in agent_dirs(cwd):
        try:
            files = sorted(directory.glob("*.md"))
        except OSError:
            continue
        for path in files:
            if path.stem in names:
                continue
            try:
                parents = parents_in(path.read_text(encoding="utf-8"))
            except OSError:
                continue
            if parents:
                names[path.stem] = parents
    return names


def requested(tool_input, cwd):
    """The gated agents this call would spawn, each with its parents."""
    targets = {}
    name = tool_input.get("subagent_type")
    if isinstance(name, str) and name:
        parents = parents_of(name, cwd)
        if parents:
            targets[name] = parents
    workflow = tool_input.get("workflow")
    if isinstance(workflow, str) and workflow:
        for gated, parents in gated_agents(cwd).items():
            if re.search(rf"(?<![\w-]){re.escape(gated)}(?![\w-])", workflow):
                targets.setdefault(gated, parents)
    return targets


def refusal(name, parents, caller):
    return (
        f"agent-dispatch-gate: `{name}` is a worker dispatched only by {', '.join(parents)}, "
        f"never from the {caller}. Dispatch the parent instead."
    )


def main():
    try:
        payload = json.load(sys.stdin)
        tool_input = payload.get("tool_input") or {}
        cwd = payload.get("cwd") or os.getcwd()
        caller = payload.get("agent_type") or ""
    except (ValueError, AttributeError):
        return 0
    if not isinstance(tool_input, dict):
        return 0
    for name, parents in requested(tool_input, cwd).items():
        if caller not in parents:
            print(refusal(name, parents, caller or MAIN_THREAD), file=sys.stderr)
            return REFUSED
    return 0


if __name__ == "__main__":
    sys.exit(main())
