#!/usr/bin/env python3
# vim: ft=python
# Filename keeps the .sh extension every hook in this directory carries, since the
# emitters spell a hook's path from its policy `script`. The shebang decides execution.
"""dependency-skill-gate.sh: refuse a prompt that invokes a dependency-only skill directly.

A skill the catalog marks `dependency_only` exists to be loaded by another skill, and no
harness has a setting that hides a skill from the user while leaving it to the model:
Claude's skillOverrides keeps every visible state in the `/` menu, Pi's
enableSkillCommands only hides discovery, and Codex's allow_implicit_invocation is the
inverse. So the refusal happens on the prompt, which every harness hands over before it
expands the skill:

    /grilling         Claude
    /skill:grilling   Pi
    $grilling         Codex

The model and parent skills load the skill through their own tools and never pass here.

The registry is read on every prompt rather than rendered into the hook, so a skill that
`kura update` marks dependency-only is refused without re-running `make harness`.
Name and path resolution mirror harnessgen's manifest.catalog_root and
emit_claude.dependency_only_skills; a test holds the two together.

Fail-open: an unreadable payload or registry exits 0, so a missing catalog costs the
refusal, never the user's prompt.
"""

import json
import os
import re
import sys
from pathlib import Path, PurePosixPath

CATALOG_ENV = "AGENT_CATALOG"
DEFAULT_CATALOG = "~/.config/kura/catalog"
SKILL_REGISTRY = "skill-registry.json"
REFUSED = 2


def catalog_root():
    return Path(os.environ.get(CATALOG_ENV) or DEFAULT_CATALOG).expanduser()


def registry_entries(registry):
    entries = [skill for repo in registry.get("upstream", {}).values() for skill in repo.get("skills", [])]
    return entries + registry.get("local", [])


def skill_name(entry):
    return entry.get("name") or PurePosixPath(entry["upstream_path"]).name


def load_entries():
    try:
        registry = json.loads((catalog_root() / SKILL_REGISTRY).read_text(encoding="utf-8"))
        return registry_entries(registry)
    except (OSError, ValueError, AttributeError, TypeError):
        return []


def dependency_only(entries):
    return {skill_name(entry) for entry in entries if entry.get("dependency_only")}


def dependents(entries, name):
    return sorted(skill_name(entry) for entry in entries if name in entry.get("dependencies", []))


def invoked(prompt, names):
    """The dependency-only skill the prompt invokes, or None.

    A trailing `(?![\\w-])` rather than `\\b`, since skill names carry hyphens and `\\b`
    would read `/grilling-notes` as `/grilling`.
    """
    alternatives = "|".join(re.escape(name) for name in sorted(names, key=len, reverse=True))
    if not alternatives:
        return None
    slash = re.match(rf"/(?:skill:)?({alternatives})(?![\w-])", prompt.lstrip())
    if slash:
        return slash.group(1)
    mention = re.search(rf"(?:^|\s)\$({alternatives})(?![\w-])", prompt)
    return mention.group(1) if mention else None


def refusal(name, parents):
    message = f"`{name}` is a dependency-only skill: it is loaded by other skills, not invoked directly."
    if parents:
        message += f" Use one that depends on it: {', '.join(parents)}."
    return message


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    prompt = data.get("prompt") if isinstance(data, dict) else None
    if not isinstance(prompt, str):
        return 0
    entries = load_entries()
    name = invoked(prompt, dependency_only(entries))
    if name is None:
        return 0
    print(refusal(name, dependents(entries, name)), file=sys.stderr)
    return REFUSED


if __name__ == "__main__":
    sys.exit(main())
