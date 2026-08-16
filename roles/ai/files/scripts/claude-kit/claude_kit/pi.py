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

Agents need a second view, and it cannot be one link. The pi-subagents extension reads
project agents from `.pi/agents/*.md` and `.agents/agents/*.md`, never from `.claude/`,
and it does not scan a skills tree for them; yet a seat plugin keeps its agent at
`.claude/skills/<seat>/agents/<seat>-staff-engineer.md`, inside the plugin. No single
directory holds every agent the installed plugins ship, so `converge_agents` maintains
one file link per agent instead, derived from the plugin links on disk exactly as the
skills link is. Pruning mirrors `sync`'s narrowings: only symlinks, and only ones
resolving into this repo's files/claude/, so a hand-authored agent kept beside ours is
never a candidate. The global half of the same story is the ai role's
`~/.pi/agent/agents -> ~/.claude/agents` link, which needs no code here because `sync`
already converges its target.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotkit import ui

from . import catalog as cat
from . import paths, scope

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


# --- the .agents/agents/ view, for pi-subagents -------------------------------------

# Unlike the skills leaf this one is a real directory of per-file links, because its
# contents come from *inside* each installed plugin and no single directory exists to
# point one link at.
AGENTS_LEAF = "agents"


def agents_path(project):
    """Where the per-file agent links live, given a project root."""
    return Path(project) / PARENT / AGENTS_LEAF


def desired_agents(project):
    """{basename: source} for every agent the installed plugins ship.

    Derived from disk, never from the catalog or the manifest: a plugin link under
    .claude/skills/ that resolves into this repo's plugins store, and holds an
    `agents/` directory, contributes each of its `agents/*.md`. `installed_names` is
    what keeps a hand-copied plugin directory or a foreign link out, for the same
    reason it keeps them out of everything else this tool removes.
    """
    claude = paths.claude_dir()
    out = {}
    for _, link in sorted(scope.installed_names(project, cat.PLUGIN, claude).items()):
        agents = scope.link_target(link) / AGENTS_LEAF
        if not agents.is_dir():
            continue
        for source in sorted(agents.glob("*.md")):
            out[source.name] = source
    return out


@dataclass
class AgentLinks:
    """What one agents convergence did. Empty lists mean a steady-state run."""

    linked: list = field(default_factory=list)
    pruned: list = field(default_factory=list)
    blocked: list = field(default_factory=list)
    # The .agents/agents path itself is occupied by something that is not a plain
    # directory, so nothing below it could be written at all.
    blocked_dir: bool = False

    @property
    def quiet(self):
        return not (self.linked or self.pruned or self.blocked or self.blocked_dir)


def converge_agents(project):
    """Match .agents/agents/ to the agents the installed plugins ship.

    Returns an AgentLinks describing what changed, or None on a steady-state run, so
    the caller reports exactly as it does for converge.

    Idempotent and derived, like converge: the desired set is recomputed from the
    plugin links every time, so removing a plugin drops its agent links on the next
    call and there is no record to go stale. The pruning narrowings mirror sync's
    first two: only symlinks, and only ones resolving into files/claude/. Sync's
    third (refuse an empty set) deliberately does not apply, because here an empty
    set is the ordinary state of a project with no plugins rather than a registry
    that lost its tags.
    """
    if project is None:
        return None
    claude = paths.claude_dir()
    desired = desired_agents(project)
    directory = agents_path(project)
    result = AgentLinks()

    # A symlink or a file wearing the directory's name is somebody's decision, exactly
    # as a foreign .agents/skills is: report it when it stands in the way, never
    # replace it.
    if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
        if desired:
            result.blocked_dir = True
            return result
        return None

    if directory.is_dir():
        for entry in sorted(directory.iterdir()):
            if entry.name in desired:
                continue
            if not entry.is_symlink():
                continue
            if not scope.points_into(entry, claude):
                continue
            entry.unlink()
            result.pruned.append(entry.name)

    for name, source in sorted(desired.items()):
        entry = directory / name
        if scope.links_to(entry, source):
            continue
        if entry.is_symlink() and scope.points_into(entry, claude):
            # Ours, pointing at a stale source: re-pointing is the fix, exactly as
            # sync relinks a right-named link at a wrong target.
            entry.unlink()
            entry.symlink_to(source)
            result.linked.append(name)
            continue
        if entry.is_symlink() or entry.exists():
            result.blocked.append(name)
            continue
        directory.mkdir(parents=True, exist_ok=True)
        entry.symlink_to(source)
        result.linked.append(name)

    # The directory goes only when this run emptied it, so one somebody made (or one
    # still holding their files) stays. Same parent rule as the skills link.
    if result.pruned and not desired:
        try:
            directory.rmdir()
            directory.parent.rmdir()
        except OSError:
            pass

    return None if result.quiet else result


def report_agents(result, project):
    """Say what converge_agents did, in the same register as report.

    Counts rather than a line per file, because a seat fleet install is fifteen
    plugins and one line each is the noise that gets a report skipped.
    """
    if result is None or project is None:
        return
    where = ui.path(agents_path(project))
    if result.linked:
        ui.note(f"Linked {ui.names_or_count(result.linked, 'agent')} into {where} for pi's subagents.")
    if result.pruned:
        ui.note(f"Removed {ui.names_or_count(result.pruned, 'agent link')} from {where}; no installed plugin ships them now.")
    if result.blocked_dir:
        ui.warn(f"{where} already exists and is not a directory, so pi will not see the plugin agents.")
        ui.note("Move it aside, then rerun any add or remove.")
    for name in result.blocked:
        ui.warn(f"{where}/{name} already exists and is not ours, so pi loads that one instead.")
