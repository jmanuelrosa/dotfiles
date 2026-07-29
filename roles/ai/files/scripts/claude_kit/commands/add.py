"""`claude-kit add`.

Split deliberately: plan() decides and returns data, apply() touches the disk.
Every rule worth testing lives in plan(), which needs no filesystem.
"""

from dataclasses import dataclass, field
from pathlib import Path

from .. import catalog as cat
from .. import errors, paths, scope, state
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


def _report(plan_, linked):
    for warning in plan_.warnings:
        print(f"⚠ {warning}")
    for step, destination in linked:
        if step.is_dependency:
            print(f"✓ Linked '{step.artifact.name}' into {destination.parent}  (required by {step.required_by})")
        else:
            print(f"✓ Linked '{step.artifact.name}' into {destination.parent}")
    for step in plan_.upgrades:
        print(f"  Recorded '{step.artifact.name}' as required by {step.required_by}; it was already installed.")
    for step in plan_.promotions:
        print(
            f"✓ '{step.artifact.name}' was already installed as a dependency and is "
            f"now marked as wanted in its own right; removing its parent will keep it."
        )
    named = plan_.steps[-1].artifact if plan_.steps else None
    if named is not None and named.type == cat.PLUGIN:
        print(
            f"  Restart Claude Code from the project root to load "
            f"'{named.name}@skills-dir'; the workspace must be trusted."
        )


def run(args):
    claude = paths.claude_dir()
    home = paths.home()
    catalog = cat.build_catalog(claude)
    effective = scope.global_set(catalog)
    project = scope.project_root(Path.cwd(), home)

    # Continue past a failure so one bad name in a batch does not strand the rest,
    # then exit with the first failure's code. A single code cannot describe
    # several outcomes, so the per-name report carries the detail.
    first_failure = errors.OK
    for name in args.names:
        provenance = state.read(project)
        plan_ = plan(
            catalog, effective, args.type, name, args.want_global, home, project, provenance
        )
        if plan_.refused:
            fail(plan_.code, plan_.message)
            if first_failure == errors.OK:
                first_failure = plan_.code
            continue
        linked = apply(plan_, home, project)
        entries = provenance_entries(plan_)
        if entries:
            state.record(project, entries)
        _report(plan_, linked)
    return first_failure
