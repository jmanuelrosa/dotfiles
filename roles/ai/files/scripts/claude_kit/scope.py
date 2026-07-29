"""Where an artifact belongs, and where it currently is.

The `global` group tag decides scope, never the working directory. A tagged
artifact belongs in ~/.claude; everything else belongs in a project, which is
simply the directory you are standing in. Landing in ~/.claude by direct request
always needs --global, so the call site says so.

Dependencies resolve their own scope rather than inheriting the parent's, which
is why resolution takes a name rather than a parent.
"""

import os
from pathlib import Path

from . import catalog as cat

GLOBAL = "global"
PROJECT = "project"


def global_set(catalog):
    """**Skill** names that belong in ~/.claude.

    Skills only, deliberately. Every dependency edge names a skill, so this is the
    only set that needs deriving; an agent or plugin is global exactly when it
    carries the tag. Returning bare names across all three types would let a skill
    inherit globalness from an identically-named agent, which is precisely the
    shadowing that explicit --type exists to rule out.

    Tag membership alone is not enough. A global artifact's declared dependencies
    reach ~/.claude too, or a global skill would load with a dependency missing;
    and a global *agent*'s skill dependencies expand one level further, because
    those skills may themselves declare others the agent needs at runtime.

    In the current registry this is why grilling, jira, domain-modeling,
    documentation-and-adrs and planning-and-task-breakdown are global without
    carrying the tag.
    """
    skills = cat.skills(catalog)
    effective = {art.name for art in catalog.values() if art.tagged_global and art.type == cat.SKILL}
    for art in catalog.values():
        if not art.tagged_global:
            continue
        for dep in art.dependencies:
            if dep not in skills:
                continue
            effective.add(dep)
            if art.type == cat.AGENT:
                effective.update(d for d in skills[dep].dependencies if d in skills)
    return effective


def belongs_global(art, effective):
    """Whether this artifact belongs in ~/.claude, ignoring any --global override.

    The tag is authoritative for every type. The derived set only adds skills
    reached as dependencies, so it is consulted for skills alone.
    """
    if art.tagged_global:
        return True
    return art.type == cat.SKILL and art.name in effective


def project_root(cwd, home):
    """cwd itself, or None when cwd is $HOME.

    A project is any directory. There is no detection and no git: run the command
    where you want the artifact, and that is where it lands. A subdirectory is
    therefore its own project, not a window onto an enclosing repo.

    $HOME is the sole exception, and not as project detection by the back door.
    Its .claude *is* ~/.claude, so a project-scoped install there would write into
    the global directory, load in every repo, be pruned by the ai role on the next
    run, and leave a claude-kit.json somewhere the design says one never exists.
    --global is how to write there deliberately.
    """
    root = Path(cwd).resolve()
    if root == Path(home).resolve():
        return None
    return root


def link_path(art, scope, home, project):
    """Where this artifact's symlink lives in the given scope."""
    root = Path(home) if scope == GLOBAL else Path(project)
    return root / ".claude" / art.leaf / art.basename


def link_target(link):
    """Where a symlink points, absolute and normalised, without requiring the
    target to exist.

    readlink rather than resolve, because a broken link still has to be classified:
    it is exactly the thing doctor reports and remove cleans up.
    """
    try:
        raw = Path(os.readlink(link))
    except OSError:
        return None
    if not raw.is_absolute():
        raw = Path(link).parent / raw
    # normpath rather than resolve: no filesystem access, so a dangling target
    # still yields a usable path.
    return Path(os.path.normpath(raw))


def points_into(link, directory):
    """True if this symlink points somewhere inside `directory`.

    How a skill is told apart from a plugin: both install into .claude/skills/, so
    the name alone is ambiguous and only the target says which store it came from.
    """
    target = link_target(link)
    if target is None:
        return False
    try:
        target.relative_to(Path(os.path.normpath(directory)))
    except ValueError:
        return False
    return True


def installed_scope(art, home, project, claude=None):
    """Which scope this artifact is currently linked in, or None.

    is_symlink rather than exists, so a broken symlink still counts as installed:
    it occupies the path and is exactly what needs cleaning.

    When `claude` is given, the link must also point into this artifact's own
    store. Without that check a plugin named X would report an identically-named
    skill as installed, since both occupy .claude/skills/X.
    """
    for candidate, root in ((GLOBAL, home), (PROJECT, project)):
        if root is None:
            continue
        link = link_path(art, candidate, home, project)
        if not link.is_symlink():
            continue
        if claude is not None and not points_into(link, Path(claude) / cat.STORE[art.type]):
            continue
        return candidate
    return None


def _links_in(directory):
    if not directory.is_dir():
        return {}
    return {entry.name: entry for entry in sorted(directory.iterdir()) if entry.is_symlink()}


def all_links(root):
    """Every symlink under root/.claude's artifact leaves, as (leaf, name, path).

    Type-agnostic on purpose. Broken-link detection wants everything present,
    including links pointing outside our store, which no per-type view would show.
    """
    if root is None:
        return []
    out = []
    for leaf in sorted(set(cat.LEAF.values())):
        for name, path in _links_in(Path(root) / ".claude" / leaf).items():
            out.append((leaf, name, path))
    return out


def installed_names(root, kind, claude):
    """Names of `kind` linked under root/.claude, as {name: path}.

    Only symlinks count: a real directory is hand-authored content and is never a
    candidate for anything this tool removes.

    `claude` is required rather than optional because skills and plugins share the
    .claude/skills/ leaf. Classifying by filename alone double-counts every link
    as both a skill and a plugin, so the target has to decide.
    """
    if root is None:
        return {}
    leaf = cat.LEAF[kind]
    suffix = cat.SUFFIX[kind]
    store = Path(claude) / cat.STORE[kind]
    out = {}
    for filename, path in _links_in(Path(root) / ".claude" / leaf).items():
        if suffix and not filename.endswith(suffix):
            continue
        if not points_into(path, store):
            continue
        out[filename[: -len(suffix)] if suffix else filename] = path
    return out


def installed_pairs(root, claude):
    """Every (type, name) linked under root/.claude, across all three types.

    The one place this set is built. Its subtlety is that type comes from which store
    a link resolves into and never from its filename, since skills and plugins share
    the .claude/skills/ leaf and a name alone counts every link as both. Three callers
    once each carried their own copy of that reasoning, and two carried it silently.
    """
    return {
        (kind, name)
        for kind in (cat.SKILL, cat.AGENT, cat.PLUGIN)
        for name in installed_names(root, kind, claude)
    }
