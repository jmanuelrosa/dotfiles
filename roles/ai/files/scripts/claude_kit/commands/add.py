"""`claude-kit add`.

Split deliberately: plan() decides and returns data, apply() touches the disk.
Every rule worth testing lives in plan(), which needs no filesystem.
"""

from dataclasses import dataclass, field
from pathlib import Path

from .. import catalog as cat
from .. import errors, paths, scope, state, ui
from ..cli import fail


@dataclass
class Step:
    """One artifact to link, in one scope."""

    artifact: cat.Artifact
    scope: str
    # None for the artifact the user named, otherwise its immediate parent.
    required_by: str = None

    @property
    def is_dependency(self):
        return self.required_by is not None


@dataclass
class Plan:
    """The outcome for one named artifact: either a refusal, or steps to take."""

    name: str
    code: int = errors.OK
    message: str = None
    steps: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    # Already present, so not re-linked, but still worth recording provenance for.
    upgrades: list = field(default_factory=list)
    # Already linked *and* recorded as somebody's dependency, now named directly.
    # No symlink to make, but the record must change or the cascade would later
    # delete something the user asked for by name.
    promotions: list = field(default_factory=list)

    @property
    def refused(self):
        return self.code != errors.OK

    @classmethod
    def refusal(cls, name, code, message):
        return cls(name=name, code=code, message=message)


def _dependency_closure(art, skills, seen):
    """Every skill reachable from art, depth-first, immediate parent recorded.

    Transitive because a plugin's skillDependencies or a skill's dependencies may
    themselves depend on more, and shipping an artifact without something it calls
    at runtime is the failure this prevents. `seen` breaks cycles and stops a
    diamond being visited twice.
    """
    out = []
    for dep_name in art.dependencies:
        if dep_name in seen:
            continue
        seen.add(dep_name)
        dep = skills.get(dep_name)
        if dep is None:
            out.append((dep_name, None, art.name))
            continue
        out.append((dep_name, dep, art.name))
        out.extend(_dependency_closure(dep, skills, seen))
    return out


def plan(catalog, effective, kind, name, want_global, home, project, provenance):
    """Decide what adding one artifact means. Pure.

    The refusal ladder is ordered so the most specific, most actionable message
    wins. In particular the global check precedes the no-project check, so a
    global artifact named outside a repo is told to pass --global rather than told
    to find a project.
    """
    art = cat.get(catalog, kind, name)
    if art is None:
        return Plan.refusal(name, errors.NOT_FOUND, f"'{name}' is not a known {kind}.")

    if art.dependency_only:
        return Plan.refusal(
            name,
            errors.DEPENDENCY_ONLY,
            f"'{name}' exists only to satisfy other skills and installs with "
            f"whichever one needs it. Add that skill instead.",
        )

    if scope.belongs_global(art, effective) and not want_global:
        reason = "carries the global tag" if art.tagged_global else "is required by a global artifact"
        return Plan.refusal(
            name,
            errors.WRONG_SCOPE,
            f"'{name}' {reason}, so it belongs in ~/.claude.\n"
            f"  Run: claude-kit add {name} --type {kind} --global",
        )

    if not art.source.exists():
        return Plan.refusal(
            name,
            errors.NOT_FOUND,
            f"'{name}' is a registered {kind} but is missing from the repo at {art.source}.",
        )

    if not want_global and project is None:
        return Plan.refusal(
            name,
            errors.NO_PROJECT,
            f"'{name}' is project-scoped, and $HOME is the one directory that cannot "
            f"be a project: its .claude is ~/.claude, so this would install globally "
            f"without saying so.\n"
            f"  cd into any other directory, or: claude-kit add {name} --type {kind} --global",
        )

    target_scope = scope.GLOBAL if want_global else scope.PROJECT
    if scope.link_path(art, target_scope, home, project).is_symlink():
        recorded = provenance.get((kind, name))
        # Naming something that arrived as a dependency is how the user says they
        # want it in its own right. The symlink already exists, but the record has
        # to change, so this is a success with an effect rather than a refusal.
        if target_scope == scope.PROJECT and recorded is not None and not state.is_direct(recorded):
            promoted = Plan(name=name)
            promoted.promotions.append(Step(art, target_scope))
            return promoted
        where = "~/.claude" if target_scope == scope.GLOBAL else "this project"
        return Plan.refusal(name, errors.ALREADY, f"'{name}' is already installed in {where}.")

    result = Plan(name=name)
    skills = cat.skills(catalog)

    for dep_name, dep, parent in _dependency_closure(art, skills, set()):
        if dep is None:
            result.warnings.append(
                f"'{parent}' declares an unknown dependency '{dep_name}'; skipping it."
            )
            continue
        # A dependency resolves its own scope. It never inherits the parent's, and
        # never needs --global: consenting to the parent consents to what it needs.
        dep_scope = scope.GLOBAL if scope.belongs_global(dep, effective) else scope.PROJECT
        if dep_scope == scope.PROJECT and project is None:
            result.warnings.append(
                f"skipped '{dep_name}', required by '{parent}': $HOME is not a project."
            )
            continue
        if scope.link_path(dep, dep_scope, home, project).is_symlink():
            # Already present. Never a reason to abort the parent, but if we have
            # no record of why it is there, claim it so the cascade can reason.
            if dep_scope == scope.PROJECT and (cat.SKILL, dep_name) not in provenance:
                result.upgrades.append(Step(dep, dep_scope, required_by=parent))
            continue
        result.steps.append(Step(dep, dep_scope, required_by=parent))

    result.steps.append(Step(art, target_scope))
    return result


def expand_group(catalog, kind, tag, want_global, effective):
    """The members of `tag` belonging in the selected scope, and the rest. Pure.

    Returns (members, elsewhere) as name lists. A tag is a filter rather than a name,
    so a member that belongs in the other scope is set aside instead of refused:
    --global picks which half of the tag to act on, and nothing reaches ~/.claude
    without it. Refusing instead would make WRONG_SCOPE the normal outcome of adding
    a group, since most tags straddle both scopes.
    """
    members, elsewhere = [], []
    for art in cat.in_group(catalog, kind, tag):
        here = scope.belongs_global(art, effective) == bool(want_global)
        (members if here else elsewhere).append(art.name)
    return members, elsewhere


def provenance_entries(plan_):
    """Provenance to record for a plan. Project-scoped installs only.

    A global install records nothing: global dependencies never cascade, so there
    is no question for a record to answer.
    """
    entries = {}
    for step in [*plan_.steps, *plan_.upgrades, *plan_.promotions]:
        if step.scope != scope.PROJECT:
            continue
        key = (step.artifact.type, step.artifact.name)
        entries[key] = state.dep_of(step.required_by) if step.is_dependency else state.DIRECT
    return entries


def apply(plan_, home, project):
    """Create the symlinks a plan calls for, returning what was linked."""
    linked = []
    for step in plan_.steps:
        destination = scope.link_path(step.artifact, step.scope, home, project)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.symlink_to(step.artifact.source)
        linked.append((step, destination))
    return linked


def install_one(catalog, effective, kind, name, want_global, home, project):
    """Plan one artifact, link it, record provenance and report. Returns its Plan.

    The whole of a single add, so a caller that arrives at a name by some other
    route — `scout --add`, which starts from the project rather than from a name —
    inherits dependency resolution, the provenance record and the plugin restart
    hint instead of growing a second copy of them that drifts.

    Provenance is read here rather than passed in because each install may add to
    it, and a batch that read it once would plan later names against a stale file.
    """
    provenance = state.read(project)
    plan_ = plan(catalog, effective, kind, name, want_global, home, project, provenance)
    if plan_.refused:
        return plan_
    linked = apply(plan_, home, project)
    entries = provenance_entries(plan_)
    if entries:
        state.record(project, entries)
    _report(plan_, linked)
    return plan_


def _report(plan_, linked):
    for warning in plan_.warnings:
        ui.warn(warning)
    for step, destination in linked:
        if step.is_dependency:
            ui.ok(
                f"Linked '{step.artifact.name}' into {ui.path(destination.parent)}"
                f"  (required by {step.required_by})"
            )
        else:
            ui.ok(f"Linked '{step.artifact.name}' into {ui.path(destination.parent)}")
    for step in plan_.upgrades:
        ui.note(
            f"Recorded '{step.artifact.name}' as required by {step.required_by}; "
            f"it was already installed."
        )
    for step in plan_.promotions:
        ui.ok(
            f"'{step.artifact.name}' was already installed as a dependency and is "
            f"now marked as wanted in its own right; removing its parent will keep it."
        )
    named = plan_.steps[-1].artifact if plan_.steps else None
    if named is not None and named.type == cat.PLUGIN:
        ui.note(
            f"Restart Claude Code from the project root to load "
            f"'{named.name}@skills-dir'; the workspace must be trusted."
        )


def _report_group(kind, tag, want_global, elsewhere, tally):
    """The asides and the one closing summary of a --group run.

    Each aside names what it skipped, and the summary counts what happened, so
    neither repeats the other. Already-installed members are summarised here rather
    than reported one by one: on the second run of a group that is every member.
    """
    if tally["already"]:
        ui.note(f"Already installed: {ui.names_or_count(tally['already'], kind)}")
    if elsewhere:
        half = "project" if want_global else "global"
        flag = "" if want_global else " --global"
        ui.note(f"The {half} half of '{tag}' is untouched: {ui.names_or_count(elsewhere, kind)}")
        ui.note(f"Install that half with: claude-kit add --type {kind} --group {tag}{flag}")
    suffix = f" ({len(tally['failed'])} failed)" if tally["failed"] else ""
    ui.done(f"Linked {tally['linked']} of {tally['total']} {kind}s tagged '{tag}'{suffix}")


def run(args):
    claude = paths.claude_dir()
    home = paths.home()
    catalog = cat.build_catalog(claude)
    effective = scope.global_set(catalog)
    project = scope.project_root(Path.cwd(), home)

    names, elsewhere = list(args.names), []
    grouped = args.group is not None
    if grouped:
        if names:
            return fail(
                errors.USAGE,
                f"--group names a set to act on, so it takes no names of its own. "
                f"Run it alone, then: claude-kit add {' '.join(names)} --type {args.type}",
            )
        # Checked once here rather than per member: every member would otherwise
        # refuse with the same message, and none of them is the one at fault.
        if not args.want_global and project is None:
            return fail(
                errors.NO_PROJECT,
                f"A group is project-scoped unless --global says otherwise, and $HOME "
                f"is the one directory that cannot be a project: its .claude is "
                f"~/.claude, so this would install globally without saying so.\n"
                f"  cd into any other directory, or: claude-kit add --type {args.type} "
                f"--group {args.group} --global",
            )
        names, elsewhere = expand_group(catalog, args.type, args.group, args.want_global, effective)
        if not names and not elsewhere:
            return fail(
                errors.NOT_FOUND,
                f"No {args.type} carries the tag '{args.group}'.\n"
                f"  Run: claude-kit list --type {args.type} --group",
            )
    elif not names:
        return fail(errors.USAGE, f"Name at least one {args.type}, or pass --group TAG.")

    tally = {"total": len(names) + len(elsewhere), "linked": 0, "already": [], "failed": []}

    # Continue past a failure so one bad name in a batch does not strand the rest,
    # then exit with the first failure's code. A single code cannot describe
    # several outcomes, so the per-name report carries the detail.
    first_failure = errors.OK
    for name in names:
        plan_ = install_one(
            catalog, effective, args.type, name, args.want_global, home, project
        )
        if plan_.refused:
            # A tag describes a set to converge on, not a list of names somebody
            # typed, so a member that is already there is the steady state rather
            # than a refusal. Every other code still fails, and still sets the exit.
            if grouped and plan_.code == errors.ALREADY:
                tally["already"].append(name)
                continue
            fail(plan_.code, plan_.message)
            tally["failed"].append(name)
            if first_failure == errors.OK:
                first_failure = plan_.code
            continue
        tally["linked"] += 1

    if grouped:
        _report_group(args.type, args.group, args.want_global, elsewhere, tally)
    return first_failure
