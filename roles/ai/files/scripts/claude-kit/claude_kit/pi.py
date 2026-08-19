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

# The two leaves this module maintains, and the file that keeps them out of a project's
# git history. `.gitignore` sits *inside* `.agents/` rather than at the project root
# because the root is not ours to edit: a repo shared with other people gets no diff it
# did not ask for, and a repo keeping its own `.agents/` content keeps that content
# tracked. The skills link is relative and would survive a commit; the agent links are
# absolute paths into this dotfiles checkout, so committing one hands a teammate a
# dangling link into a directory they do not have.
IGNORE = ".gitignore"
# The file names itself, because a `.gitignore` is not covered by its own patterns and
# `git status` reports the whole directory as untracked for that one file. Naming it is
# what makes `.agents/` disappear from a project's status entirely, which is the point.
#
# These are the two names this module maintains, so the breadth is exact for every
# project on this machine: the six that keep their own `.agents/` content keep it at the
# root, which stays tracked. A project that wants its own `agents/` tracked replaces this
# file, and `write_ignore` never overwrites one it finds.
IGNORED = (LEAF, "agents", IGNORE)


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


def ignore_path(project):
    """Where the ignore file lives, given a project root."""
    return Path(project) / PARENT / IGNORE


def ignore_body():
    """What we write, and the only content we will ever delete."""
    return "".join(f"{name}\n" for name in IGNORED)


def write_ignore(project):
    """Keep our links out of the project's history. Returns whether it wrote.

    Never overwrites: a file already at this path is somebody's, and ours says so little
    that replacing theirs could only lose information. Called only when a leaf is
    actually created, so a project this module has nothing to do in gets no new file.
    """
    path = ignore_path(project)
    if path.is_symlink() or path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(ignore_body())
    return True


def prune_parent(parent):
    """Remove `.agents/` when a run emptied it, taking our own ignore file with it.

    The ignore file is ours, so it must not be the thing that keeps an otherwise empty
    directory alive. Anything else in there is somebody's, including a `.gitignore` whose
    contents are not the one we write, and then `rmdir` fails and the directory stays,
    which is the outcome we want in that case anyway.
    """
    ignore = parent / IGNORE
    try:
        if any(entry != ignore for entry in parent.iterdir()):
            return
        if ignore.is_file() and not ignore.is_symlink() and ignore.read_text() == ignore_body():
            ignore.unlink()
        parent.rmdir()
    except OSError:
        pass


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


def converge(project, dry_run=False):
    """Match the link to what the project holds. Returns what changed, or None.

    Returns one of "linked", "unlinked", "blocked" or None, so the caller can report a
    change without restating the rules that produced it.

    Called after any command that adds or removes a project link, and directly by
    `claude-kit converge`. Idempotent, and deliberately derived rather than tracked: the
    answer is always recomputed from the two paths, so there is no state to go stale and
    no ordering to get wrong.

    `dry_run` reports the same answer and writes nothing. It guards the writes rather
    than returning early, so the decision a dry run reports is the one a real run makes
    and the two cannot drift.
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
        if not dry_run:
            link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(TARGET)
            write_ignore(project)
        return "linked"

    if not ours:
        return None
    if not dry_run:
        link.unlink()
        # The parent goes only when this emptied it, so a project keeping other
        # `.agents/` resources (pi prompts, another harness's data) keeps them.
        prune_parent(link.parent)
    return "unlinked"


def report(change, project, dry_run=False, stream=None):
    """Say what converge did, once, in the one wording every caller uses.

    Silent when nothing changed, which is every run after the first: a line repeating a
    link that was already right is the kind of noise that gets a whole report skipped.

    `stream` exists because `claude-kit converge --quiet` runs from a SessionStart hook,
    where Claude Code feeds a hook's stdout back into the session as context. A warning
    still has to reach a human, so quiet means "nothing on stdout" rather than silence.
    """
    if change is None or project is None:
        return
    link = ui.path(link_path(project))
    if change == "linked":
        verb = "Would link" if dry_run else "Linked"
        ui.note(f"{verb} {link} so pi loads this project's skills too.", stream=stream)
    elif change == "unlinked":
        verb = "Would remove" if dry_run else "Removed"
        ui.note(f"{verb} {link}; no skills are linked here now.", stream=stream)
    elif change == "blocked":
        ui.warn(
            f"{link} already exists and is not ours, so pi will not see these skills.",
            stream=stream,
        )
        ui.note(f"Point it at {ui.path(source_path(project))}, or move it aside.", stream=stream)


# --- the .agents/agents/ view, for pi-subagents -------------------------------------

# Unlike the skills leaf this one is a real directory of per-file links, because its
# contents come from *inside* each installed plugin and no single directory exists to
# point one link at.
AGENTS_LEAF = "agents"


def agents_path(project):
    """Where the per-file agent links live, given a project root."""
    return Path(project) / PARENT / AGENTS_LEAF


def agents_dir_blocked(project):
    """Whether something that is not a plain directory occupies .agents/agents/.

    A symlink or a file wearing the directory's name is somebody's decision, exactly as
    a foreign .agents/skills is, so nothing below it is written. One predicate rather
    than the same condition in two files, because doctor's remedy for the missing links
    is to run the very command this refuses: the two disagreeing is a note the user
    cannot clear by doing what it says.
    """
    directory = agents_path(project)
    return directory.is_symlink() or (directory.exists() and not directory.is_dir())


def desired_agents(project):
    """({basename: source}, {basename: [plugin, ...]}) for the installed plugins' agents.

    Derived from disk, never from the catalog or the manifest: a plugin link under
    .claude/skills/ that resolves into this repo's plugins store, and holds an
    `agents/` directory, contributes each of its `agents/*.md`. `installed_names` is
    what keeps a hand-copied plugin directory or a foreign link out, for the same
    reason it keeps them out of everything else this tool removes.

    The basename is the only name pi has for an agent, so two plugins shipping
    `agents/<same-name>.md` cannot both be linked here. The first in plugin order takes
    the name and the rest are returned as a collision for the caller to report: the
    repo's rule is that a name means one artifact, and this is the one place breaking it
    changes what loads, so resolving it quietly is what hides it.
    """
    claude = paths.claude_dir()
    out = {}
    owners = {}
    collisions = {}
    for plugin, link in sorted(scope.installed_names(project, cat.PLUGIN, claude).items()):
        agents = scope.link_target(link) / AGENTS_LEAF
        if not agents.is_dir():
            continue
        for source in sorted(agents.glob("*.md")):
            if source.name in out:
                collisions.setdefault(source.name, [owners[source.name]]).append(plugin)
                continue
            out[source.name] = source
            owners[source.name] = plugin
    return out, collisions


@dataclass
class AgentLinks:
    """What one agents convergence did. Empty lists mean a steady-state run."""

    linked: list = field(default_factory=list)
    pruned: list = field(default_factory=list)
    blocked: list = field(default_factory=list)
    # {basename: [plugin, ...]}: two installed plugins claiming one agent filename.
    collided: dict = field(default_factory=dict)
    # The .agents/agents path itself is occupied by something that is not a plain
    # directory, so nothing below it could be written at all.
    blocked_dir: bool = False

    @property
    def quiet(self):
        return not (self.linked or self.pruned or self.blocked or self.collided or self.blocked_dir)


def converge_agents(project, dry_run=False):
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

    A filename two plugins both claim is carried through as `collided` rather than
    settled here, so a run reporting nothing else still reports that one, every time,
    until the repo stops shipping the name twice.

    `dry_run` guards the writes and nothing else, exactly as in converge: what a dry run
    reports is what a real run would do, decided by the same code.
    """
    if project is None:
        return None
    claude = paths.claude_dir()
    desired, collisions = desired_agents(project)
    directory = agents_path(project)
    result = AgentLinks(collided=collisions)

    if agents_dir_blocked(project):
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
            if not dry_run:
                entry.unlink()
            result.pruned.append(entry.name)

    for name, source in sorted(desired.items()):
        entry = directory / name
        if scope.links_to(entry, source):
            continue
        if entry.is_symlink() and scope.points_into(entry, claude):
            # Ours, pointing at a stale source: re-pointing is the fix, exactly as
            # sync relinks a right-named link at a wrong target.
            if not dry_run:
                entry.unlink()
                entry.symlink_to(source)
            result.linked.append(name)
            continue
        if entry.is_symlink() or entry.exists():
            result.blocked.append(name)
            continue
        if not dry_run:
            directory.mkdir(parents=True, exist_ok=True)
            entry.symlink_to(source)
        result.linked.append(name)

    if result.linked and not dry_run:
        write_ignore(project)

    # The directory goes only when this run emptied it, so one somebody made (or one
    # still holding their files) stays. Same parent rule as the skills link.
    if result.pruned and not desired and not dry_run:
        try:
            directory.rmdir()
        except OSError:
            pass
        else:
            prune_parent(directory.parent)

    return None if result.quiet else result


def report_agents(result, project, dry_run=False, stream=None):
    """Say what converge_agents did, in the same register as report.

    Counts rather than a line per file, because a seat fleet install is fifteen
    plugins and one line each is the noise that gets a report skipped.
    """
    if result is None or project is None:
        return
    where = ui.path(agents_path(project))
    if result.linked:
        verb = "Would link" if dry_run else "Linked"
        ui.note(
            f"{verb} {ui.names_or_count(result.linked, 'agent')} into {where} "
            "for pi's subagents.",
            stream=stream,
        )
    if result.pruned:
        verb = "Would remove" if dry_run else "Removed"
        ui.note(
            f"{verb} {ui.names_or_count(result.pruned, 'agent link')} from {where}; "
            "no installed plugin ships them now.",
            stream=stream,
        )
    if result.blocked_dir:
        ui.warn(
            f"{where} already exists and is not a directory claude-kit will write into, "
            "so pi will not see the plugin agents.",
            stream=stream,
        )
        ui.note("Move it aside, then run: claude-kit converge", stream=stream)
    for name in result.blocked:
        ui.warn(
            f"{where}/{name} already exists and is not ours, so pi loads that one instead.",
            stream=stream,
        )
    for name, plugins in sorted(result.collided.items()):
        ui.warn(
            f"{', '.join(plugins)} each ship agents/{name}, so pi loads only {plugins[0]}'s.",
            stream=stream,
        )
    if result.collided:
        ui.note("Rename one of them, since a name has to mean one artifact.", stream=stream)
