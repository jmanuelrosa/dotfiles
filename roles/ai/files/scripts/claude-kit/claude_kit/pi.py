"""The one thing pi needs from a project that claude-kit installs into.

Pi implements the same Agent Skills standard, and every skill in this repo is written
to it, so a project's skills are already the right shape for both harnesses. What pi
does not do is read `.claude/`: it discovers project skills from `.pi/skills/` and from
`.agents/skills/` in the cwd and its ancestors, and nowhere else. So everything `add`
links is invisible to pi, which is the whole of the gap this module closes.

One relative symlink closes it, `<project>/.agents/skills` -> `../.claude/skills`, and
that works because of two facts about pi's own discovery (read out of `core/skills.js`,
0.84.1, and exercised in the tests):

  - It follows symlinks, statting each entry rather than trusting the dirent, and skips
    a broken one. So a directory of absolute links into this checkout scans cleanly.
  - A directory holding `SKILL.md` is a skill root; one that does not is recursed into.
    A seat plugin therefore arrives whole: `.claude/skills/backend` is a link to the
    plugin, and pi finds `skills/backend-failure-modes/SKILL.md` inside it. Its
    `agents/` directory yields nothing, since a loose `.md` only counts at the root of
    a scanned path, and `.claude-plugin/` is skipped for starting with a dot.

Linking the directory rather than its contents is what keeps this from being a second
copy of the install: there is no per-artifact work here, nothing to converge against
the catalog, and no way for the two views to disagree. `.claude/skills/` *is* the view.

Nothing here is Claude Code's business, so nothing is recorded in `claude-kit.json`. The
link is derived from what is on disk, which means it can be recomputed at any time and
`converge` is safe to call unconditionally.

There is no counterpart for `.claude/agents/`, and that is not an omission: pi has no
subagents, so an agent has nothing to load it.
"""

import os
from pathlib import Path

from dotkit import ui

from . import scope

# Pi reads `.agents/skills/` from the cwd up through its ancestors. The parent directory
# is shared with other harnesses by design (the path is not pi's own), which is why only
# the `skills` leaf below it is ever created or removed here.
PARENT = ".agents"
LEAF = "skills"

# Relative rather than absolute, unlike every link `add` makes. Those name a skill inside
# this checkout and can only be absolute; this one names a sibling directory inside the
# project, so a relative target survives the project being moved or cloned somewhere
# else, and reads as what it is in a diff.
TARGET = os.path.join("..", ".claude", LEAF)


def link_path(project):
    """Where the link lives, given a project root."""
    return Path(project) / PARENT / LEAF


def source_path(project):
    """The directory the link points at: the project's own claude skills."""
    return Path(project) / ".claude" / LEAF


def is_ours(project):
    """Whether the path is a link this module made.

    Asked before every write and every delete, and it is the only thing standing between
    this and somebody's hand-authored `.agents/skills/`, which is a legitimate thing for
    a project to have and is none of our business. `links_to` is the same exact-target
    test `sync` uses, and it resolves our relative target through the link's own parent.
    """
    return scope.links_to(link_path(project), source_path(project))


def wanted(project):
    """Whether the project has claude skills for pi to see.

    Emptiness counts as no, so removing the last skill takes the link with it. The
    directory routinely outlives its contents: `remove` unlinks skills and never prunes
    the leaf they sat in.
    """
    source = source_path(project)
    if not source.is_dir():
        return False
    return any(source.iterdir())


def converge(project):
    """Match the link to what the project holds. Returns what changed, or None.

    Returns one of "linked", "unlinked", "blocked" or None, so the caller can report a
    change without restating the rules that produced it.

    Called after any command that adds or removes a project link. Idempotent, and
    deliberately derived rather than tracked: the answer is always recomputed from the
    two paths, so there is no state to go stale and no ordering to get wrong.
    """
    if project is None:
        return None
    link = link_path(project)
    ours = is_ours(project)

    if wanted(project):
        if ours:
            return None
        # Anything else already occupying the path stays. A real directory is content
        # someone wrote, and a link somewhere else is a decision someone made; either
        # way pi is already reading something here and replacing it silently would be
        # this tool overwriting an answer it was not asked.
        if link.is_symlink() or link.exists():
            return "blocked"
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(TARGET)
        return "linked"

    if not ours:
        return None
    link.unlink()
    # The parent goes only when this emptied it, so a project keeping other `.agents/`
    # resources (pi prompts, another harness's data) keeps them.
    try:
        link.parent.rmdir()
    except OSError:
        pass
    return "unlinked"


def report(change, project):
    """Say what converge did, once, in the one wording both commands use.

    Silent when nothing changed, which is every run after the first: a line repeating a
    link that was already right is the kind of noise that gets a whole report skipped.
    """
    if change is None or project is None:
        return
    link = ui.path(link_path(project))
    if change == "linked":
        ui.note(f"Linked {link} so pi loads this project's skills too.")
    elif change == "unlinked":
        ui.note(f"Removed {link}; no skills are linked here now.")
    elif change == "blocked":
        ui.warn(f"{link} already exists and is not ours, so pi will not see these skills.")
        ui.note(f"Point it at {ui.path(source_path(project))}, or move it aside.")
