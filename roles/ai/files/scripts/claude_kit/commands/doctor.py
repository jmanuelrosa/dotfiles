"""`claude-kit doctor`.

The one command where --type is optional, because the cross-type checks cannot run
inside a single type: a dependency edge crosses from an agent or plugin to a skill,
and a name overlap is by definition about two types at once. Requiring --type here
would stop doctor doing half its job.

Never refuses. Outside a project it runs the registry and disk checks and reports
which ones it skipped.
"""

from pathlib import Path

from .. import catalog as cat
from .. import checks, errors, paths, scope, state


def collect(catalog, effective, claude, home, project, provenance, kind=None):
    """Every finding, narrowed to `kind` when one is given. Pure.

    Narrowing filters the findings rather than the inputs, so a scoped run uses
    exactly the same checks as a full one and cannot drift from it. A finding whose
    kind is None spans types and is dropped when narrowing, which is what makes
    `--type` and the cross-type checks coexist.
    """
    findings = [
        *checks.missing_sources(catalog),
        *checks.untracked_on_disk(catalog, claude),
        *checks.dangling_dependencies(catalog),
        *checks.orphaned_dependency_only(catalog),
        *checks.plugin_manifests(catalog),
        *checks.frontmatter_parses(catalog),
        *checks.name_overlaps(catalog),
        *checks.broken_links(claude, home, project),
        *checks.wrong_scope(catalog, effective, home, project, claude),
        *checks.provenance_drift(catalog, provenance, project, claude),
    ]
    if kind is None:
        return findings
    return [f for f in findings if f.kind == kind]


def report(findings, kind, project, emit=print):
    """Print the findings and return the exit code."""
    if project is None:
        emit("Running in $HOME, which is never a project, so project-scope checks were skipped.\n")

    problems = [f for f in findings if f.is_problem]
    notes = [f for f in findings if not f.is_problem]

    for group, label in ((problems, "Problems"), (notes, "Notes")):
        if not group:
            continue
        emit(f"{label}:")
        for finding in group:
            emit(f"  {finding.subject}: {finding.detail}  [{finding.check}]")
        emit("")

    where = f"{kind}s" if kind else "skills, agents and plugins"
    if not problems and not notes:
        emit(f"✓ No drift found across {where}.")
    else:
        emit(f"{len(problems)} problem(s), {len(notes)} note(s) across {where}.")

    return errors.DRIFT if problems else errors.OK


def run(args):
    claude = paths.claude_dir()
    home = paths.home()
    catalog = cat.build_catalog(claude)
    effective = scope.global_set(catalog)
    project = scope.project_root(Path.cwd(), home)
    provenance = state.read(project)

    findings = collect(catalog, effective, claude, home, project, provenance, args.type)
    return report(findings, args.type, project)
