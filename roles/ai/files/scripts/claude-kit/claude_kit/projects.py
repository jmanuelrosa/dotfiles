"""Which projects a sweep converges, and why one list cannot come from one place.

`pi.converge` answers "does this project's pi view match its claude view", and every
command that installs or removes calls it for the project it was run in. Nothing asked
the question for a project nobody is currently standing in, which is what left 28
directories on this machine holding a `.claude/skills` that pi could not see.

Discovery is a union of two sources, and each covers the other's blind spot:

  - **Claude Code's own registry**, the `projects` keys of `~/.claude.json`. Authoritative
    about where Claude Code has actually been used, including checkouts outside any
    directory this module would think to look in. It knows nothing about a repo whose
    skills were installed from a parent directory, and it keeps entries for directories
    that no longer exist.
  - **A walk of the roots**, `~/Developer` by default. Finds a project the registry never
    recorded, and finds nothing outside the roots.

Neither is filtered on being a git repo. A project is a directory here exactly as it is
in `scope.project_root`, because that is the rule `add` already installed by: a
subdirectory of a monorepo that had skills installed into it is its own project, and it
is also, separately, the only shape pi can read them from (pi's `.agents/skills` walk
stops at the git root, so skills installed one level above it are already unreachable and
this module is not the place to hide that).

The filter that matters is the last one: a directory is only a project *for this purpose*
if pi has something to miss there, which is `pi.wanted` or a non-empty `desired_agents`.
That keeps a sweep's report to the projects it could act on, and keeps the walk's output
from turning every stray `.claude` into a line of noise.
"""

import os
from pathlib import Path

from . import pi, scope
from . import workspace as ws

#: Where a bare sweep looks, relative to $HOME. One entry, because this is a default
#: rather than a policy: `--root` names any other tree, and the registry covers the
#: checkouts that live nowhere near here.
DEFAULT_ROOTS = ("Developer",)

#: How deep below a root to look. Four is what reaches `work/<org>/<repo>/<subdir>` on
#: this machine, and stopping there is what keeps the walk off `node_modules` depths in
#: a repo that has one at every level.
DEPTH = 4

#: Never descended into. A dot directory is either ours (`.claude`, `.agents`, and
#: descending would be circular) or somebody's cache, and the three named trees hold
#: thousands of directories that cannot be projects.
SKIP = {"node_modules", "vendor", "Library"}


def marks_a_project(directory):
    """Whether this directory looks like somewhere claude-kit has installed.

    Either mark is enough. `claude-kit.json` is the record, and `skills/` is what a
    project provisioned before the manifest existed has instead; asking for both would
    miss exactly the old projects this sweep is for.
    """
    claude = Path(directory) / ".claude"
    return (claude / "skills").is_dir() or (claude / "claude-kit.json").is_file()


def registered(home):
    """The project keys Claude Code has recorded, as strings. Never raises.

    An unreadable or absent `~/.claude.json` yields nothing rather than failing: this is
    one of two sources and the sweep is still worth running on the other. Read through
    `workspace`, which is the only module that touches Claude Code's config.
    """
    try:
        config = ws.read(ws.config_path(home))
    except ws.Unreadable:
        return []
    projects = config.get("projects")
    if not isinstance(projects, dict):
        return []
    return list(projects)


def scan(root, depth=DEPTH):
    """Directories at or below `root` that look like projects, as strings.

    Prunes rather than filters: a pruned directory's whole subtree is skipped, which is
    what keeps this cheap enough to run from a hook. A project found at one level is
    still descended into, because a monorepo can hold both.
    """
    root = Path(root)
    if not root.is_dir():
        return []
    found = []
    base = len(root.parts)
    for current, dirs, _ in os.walk(root, followlinks=False):
        here = Path(current)
        if len(here.parts) - base >= depth:
            dirs[:] = []
        else:
            dirs[:] = sorted(d for d in dirs if d not in SKIP and not d.startswith("."))
        if marks_a_project(here):
            found.append(str(here))
    return found


def discover(home, roots=None):
    """Every project a sweep should converge, sorted and de-duplicated.

    Sorted so a report reads the same twice, and de-duplicated on the resolved path
    because the two sources spell the same project differently: the registry stores what
    Claude Code was handed, and the walk stores what it found.
    """
    if roots is None:
        roots = [Path(home) / name for name in DEFAULT_ROOTS]
    candidates = list(registered(home))
    for root in roots:
        candidates.extend(scan(root))

    seen = {}
    for candidate in candidates:
        project = keep(candidate, home)
        if project is not None:
            seen[str(project)] = project
    return [seen[key] for key in sorted(seen)]


def keep(candidate, home):
    """The project to converge for this candidate, or None to drop it.

    Four reasons to drop one, and each is a real entry on this machine: the directory is
    gone (the registry holds two such keys), it is `$HOME` (whose `.claude` *is*
    `~/.claude`, so there is no project view to converge), it has no claude artifacts at
    all, or it has some but none that pi could see anyway. The last is what stops a
    project holding only `.claude/commands/` from being reported forever: commands are
    Claude-only by construction and no amount of converging changes that.
    """
    path = Path(candidate)
    if not path.is_dir():
        return None
    project = scope.project_root(path, home)
    if project is None:
        return None
    if not marks_a_project(project):
        return None
    if not pi.wanted(project) and not pi.desired_agents(project)[0]:
        return None
    return project
