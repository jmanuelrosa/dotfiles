"""`claude-kit remove`, including the cascade.

The cascade never leaves the project it starts in. Two reasons, and the second is
the one that makes it a correctness matter rather than a preference:

  ~/.claude is shared, so one stale link there costs nothing.
  claude-kit standing in ~/work/api cannot see ~/work/web. Removing a global
  dependency because *this* project no longer needs it would silently break every
  other project that still does.

So a global dependency is always kept, and removing a global artifact cascades
nothing at all. Getting cross-scope removal right would need a machine-wide index
of every project that ever installed something, which goes stale the moment a
checkout moves.
"""

from dataclasses import dataclass, field
from pathlib import Path

from .. import catalog as cat
from .. import errors, paths, scope, state
from ..cli import fail


@dataclass
class Removal:
    """The outcome for one named artifact."""

    name: str
    code: int = errors.OK
    message: str = None
    # (artifact, path) pairs to unlink: the named one first, then cascaded deps.
    unlink: list = field(default_factory=list)
    cascaded: list = field(default_factory=list)
    kept: list = field(default_factory=list)

    @property
    def refused(self):
        return self.code != errors.OK

    @classmethod
    def refusal(cls, name, code, message):
        return cls(name=name, code=code, message=message)


def dependants(catalog, installed, exclude):
    """Which installed artifacts declare each skill, as {skill: [dependant names]}.

    Computed from the registry against what is actually linked, not from recorded
    parents, so a hand-made symlink still counts as a dependant. `exclude` is the
    set of (type, name) pairs already being removed.

    Only *project* artifacts count. A global artifact's dependencies are global
    too, and global links are never cascade candidates.
    """
    out = {}
    for key in installed:
        if key in exclude:
            continue
        art = cat.get(catalog, *key)
        if art is None:
            continue
        for dep in art.dependencies:
            out.setdefault(dep, []).append(art.name)
    return out


def cascade(catalog, installed, provenance, removing):
    """Which project skills become unneeded once `removing` goes. Pure.

    `installed` is the set of (type, name) currently linked in the project.
    `removing` is the set of (type, name) being removed.

    Returns (to_remove, kept) where kept is [(name, reasons)] explaining each
    survivor, so the caller can say why rather than silently keeping things.

    Transitive: a cascaded skill's own dependencies may become unneeded in turn.
    Iterates to a fixed point rather than recursing, because removing one skill
    can free several and the order should not matter.
    """
    doomed = set(removing)
    kept = {}

    while True:
        edges = dependants(catalog, installed, doomed)
        candidates = set()
        for key in doomed:
            art = cat.get(catalog, *key)
            if art is None:
                continue
            for dep in art.dependencies:
                dep_key = (cat.SKILL, dep)
                if dep_key in doomed or dep_key not in installed:
                    continue
                candidates.add(dep_key)

        newly = set()
        for dep_key in sorted(candidates):
            name = dep_key[1]
            reason = provenance.get(dep_key)
            # No record means we cannot know it arrived as a dependency, and a
            # wrong delete costs more than a stale link. Keep it.
            if reason is None:
                kept[name] = ["not tracked by claude-kit"]
                continue
            # Named directly at some point, so it is wanted in its own right.
            if state.is_direct(reason):
                kept[name] = ["installed directly"]
                continue
            still = edges.get(name) or []
            if still:
                kept[name] = [f"still needed by {other}" for other in sorted(set(still))]
                continue
            kept.pop(name, None)
            newly.add(dep_key)

        if not newly:
            return sorted(doomed - set(removing)), sorted(kept.items())
        doomed |= newly


def plan(catalog, kind, name, want_global, home, project, provenance, no_cascade, claude):
    """Decide what removing one artifact means. Pure apart from stat calls.

    Takes no `effective` set, unlike add.plan: --global alone decides the scope here.
    Where an artifact belongs is a question about installing it, and a removal never
    leaves the scope it starts in, so there is nothing for the global set to resolve.
    """
    art = cat.get(catalog, kind, name)
    if art is None:
        return Removal.refusal(name, errors.NOT_FOUND, f"'{name}' is not a known {kind}.")

    if not want_global and project is None:
        return Removal.refusal(
            name,
            errors.NO_PROJECT,
            f"$HOME is the one directory that cannot be a project: its .claude is "
            f"~/.claude, so this would act on the global scope without saying so.\n"
            f"  cd into any other directory, or: claude-kit remove {name} --type {kind} --global",
        )

    target_scope = scope.GLOBAL if want_global else scope.PROJECT
    link = scope.link_path(art, target_scope, home, project)

    if not link.is_symlink():
        # A real directory is somebody's hand-authored content. Refusing rather
        # than deleting is the whole point: this tool only owns its own symlinks.
        if link.exists():
            return Removal.refusal(
                name,
                errors.USAGE,
                f"{link} is a real directory, not a link claude-kit made. Leaving it alone.",
            )
        where = "~/.claude" if target_scope == scope.GLOBAL else "this project"
        return Removal.refusal(name, errors.NOT_INSTALLED, f"'{name}' is not installed in {where}.")

    result = Removal(name=name)
    result.unlink.append((art, link))

    # Global removal cascades nothing: ~/.claude carries no provenance, and other
    # projects we cannot see may still depend on what is there.
    if no_cascade or target_scope == scope.GLOBAL:
        return result

    installed = scope.installed_pairs(project, claude)
    doomed, kept = cascade(catalog, installed, provenance, {(kind, name)})
    result.kept = kept
    for dep_key in doomed:
        dep = cat.get(catalog, *dep_key)
        dep_link = scope.link_path(dep, scope.PROJECT, home, project)
        if dep_link.is_symlink():
            result.cascaded.append((dep, dep_link))
    return result


def apply(removal, project):
    """Unlink what the plan calls for and drop the matching provenance."""
    forget = []
    for art, link in [*removal.unlink, *removal.cascaded]:
        link.unlink()
        forget.append((art.type, art.name))
    if project is not None and forget:
        state.forget(project, forget)
    return forget


def _report(removal, want_global):
    for art, link in removal.unlink:
        print(f"✓ Unlinked '{art.name}' from {link.parent}")
    for art, link in removal.cascaded:
        print(f"✓ Unlinked '{art.name}' too; nothing installed needs it now")
    for name, reasons in removal.kept:
        print(f"  Kept '{name}': {'; '.join(reasons)}")
    if want_global and removal.unlink:
        art = removal.unlink[0][0]
        if art.dependencies:
            print(
                "  Its dependencies stay in ~/.claude: other projects may still "
                "need them, and claude-kit cannot see them from here."
            )


def run(args):
    claude = paths.claude_dir()
    home = paths.home()
    catalog = cat.build_catalog(claude)
    project = scope.project_root(Path.cwd(), home)

    first_failure = errors.OK
    for name in args.names:
        provenance = state.read(project)
        removal = plan(
            catalog, args.type, name, args.want_global,
            home, project, provenance, args.no_cascade, claude,
        )
        if removal.refused:
            fail(removal.code, removal.message)
            if first_failure == errors.OK:
                first_failure = removal.code
            continue
        apply(removal, None if args.want_global else project)
        _report(removal, args.want_global)
    return first_failure
