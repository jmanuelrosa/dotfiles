"""`claude-kit restore`: install what a project's claude-kit.json already records.

The inverse of `adopt`. That command reads the disk and writes the manifest; this
one reads the manifest and writes the disk. A clone is the case both exist for: the
symlinks point into this dotfiles checkout and are never committed, so a repo that
ships `.claude/claude-kit.json` arrives with a complete record of what it needs and,
until now, no command that acts on it. `doctor` named that gap and pointed nowhere.

Two rules decide the whole command.

**Only the `direct` entries are installed.** Each goes through `add.install_one`, so
an entry restored here resolves its dependency closure, records provenance and prints
the plugin restart hint exactly as a hand-typed `add` does. Naming the `dep-of:` rows
too would install them as though they had been asked for and record them `direct`,
disarming the cascade the manifest exists to preserve.

**Nothing is ever deleted.** A recorded entry still unlinked once the run finishes is
reported and exits DRIFT, never forgotten: a manifest can go stale (its parent stopped
declaring it, the registry dropped the row), and dropping a record is `remove`'s job.
D10 and D14 both err toward keeping, and a restore that pruned would make a bad
manifest cost the user something rather than merely fail to help.
"""

from pathlib import Path

from .. import catalog as cat
from .. import errors, paths, scope, state
from dotkit import ui
from ..cli import fail
from . import add

TITLE = "📦"


def wanted(provenance, installed, kind=None):
    """The direct entries to install and the ones already linked, as key lists. Pure.

    `kind` narrows the output. Unlike adopt's, this filter has nothing to reason
    across: every entry stands alone, so narrowing the input would give the same
    answer.
    """
    missing, present = [], []
    for key in sorted(provenance):
        if kind is not None and key[0] != kind:
            continue
        if not state.is_direct(provenance[key]):
            continue
        (present if key in installed else missing).append(key)
    return missing, present


def unlinked(provenance, installed, kind=None):
    """Recorded entries with no link, whatever their reason. Pure.

    Called after the installs rather than before, because a `dep-of:` row is expected
    to arrive as somebody's dependency and only what is still absent afterwards is
    worth reporting.
    """
    return [
        key
        for key in sorted(provenance)
        if (kind is None or key[0] == kind) and key not in installed
    ]


def label(key):
    return f"{key[0]} '{key[1]}'"


def _already(present, noun):
    names = ui.names_or_count([name for _, name in present], noun)
    return ui.render("note", f"Already installed: {names}")


def planned_links(plans):
    """Every (type, name) a set of plans would link, deduped, in plan order. Pure.

    A dry run has to show the closure rather than the manifest: a single recorded
    entry routinely brings four skills with it, and a preview reading `1 of 1` next
    to a real run printing four ✓ lines is a preview nobody would trust again. Two
    direct entries sharing a dependency plan it twice, hence the dedupe.

    A key planned both ways keeps the unqualified label: the manifest records it in
    its own right, so annotating it `(required by …)` because some other entry also
    needs it would describe the wrong half of the truth.
    """
    out = {}
    for plan_ in plans:
        for step in plan_.steps:
            key = (step.artifact.type, step.artifact.name)
            if key in out and (out[key] is None or step.required_by is not None):
                continue
            out[key] = step.required_by
    return list(out.items())


def preview(plans, present, kind, project, emit=print):
    """The --dry-run report. Its code is OK; a refused plan is reported by the caller."""
    noun = kind or "artifact"
    emit(ui.render("title", f"{TITLE} Would restore from {ui.path(state.path_for(project))}:"))
    links = planned_links(plans)
    for key, required_by in links:
        suffix = f"  (required by {required_by})" if required_by else ""
        emit(ui.render("item", f"{label(key)}{suffix}"))
    named = len([p for p in plans if not p.refused])
    emit(ui.render("done", f"{len(links)} link(s) for {named} recorded {noun}(s)."))
    if present:
        emit(_already(present, noun))
    emit(ui.render("note", "Nothing written (--dry-run).", indent=0))
    return errors.OK


def summarise(linked, restored, attempted, present, remaining, kind, first_failure, emit=print):
    """The closing lines of a real run, and its exit code.

    A failure's own code wins over DRIFT: the per-artifact refusal `add` already
    printed says more than "something is still unlinked" does.
    """
    noun = kind or "artifact"
    failed = attempted - restored
    suffix = f" ({failed} failed)" if failed else ""
    # Both numbers, because they differ whenever anything had dependencies: `restored`
    # counts the manifest's rows and `linked` counts what actually reached the disk.
    extra = f", {linked} link(s)" if linked != restored else ""
    emit(ui.render("done", f"Restored {restored} of {attempted} recorded {noun}(s){extra}{suffix}"))
    if present:
        emit(_already(present, noun))
    if remaining:
        emit(ui.render("warn", f"{len(remaining)} recorded entry(s) are still not linked:"))
        for key in remaining:
            emit(ui.render("item", label(key)))
        emit(
            ui.render(
                "note",
                "Nothing was forgotten. Run `claude-kit doctor` for the detail, and "
                "`claude-kit remove` to drop one for good.",
            )
        )
    if first_failure != errors.OK:
        return first_failure
    return errors.DRIFT if remaining else errors.OK


def run(args):
    claude = paths.claude_dir()
    home = paths.home()
    project = scope.project_root(Path.cwd(), home)

    if project is None:
        return fail(
            errors.NO_PROJECT,
            "$HOME is the one directory that cannot be a project: its .claude is "
            "~/.claude, which carries no manifest because a global dependency never "
            "cascades.\n"
            "  cd into the project you want to restore, or run: claude-kit sync",
        )

    path = state.path_for(project)
    if not path.is_file():
        return fail(
            errors.NOT_FOUND,
            f"No {state.FILENAME} in {ui.path(path.parent)}, so there is nothing to "
            f"restore from.\n"
            f"  If the project already has links, write one with: claude-kit adopt",
        )
    try:
        provenance = state.read_strict(project)
    except state.Malformed as exc:
        return fail(
            errors.DRIFT,
            f"{ui.path(path)} does not parse: {exc}\n"
            f"  Fix it by hand, or delete it and rebuild with: claude-kit adopt",
        )

    catalog = cat.build_catalog(claude)
    effective = scope.global_set(catalog)
    installed = scope.installed_pairs(project, claude)
    missing, present = wanted(provenance, installed, args.type)

    if not missing:
        # Finding nothing to install is the healthy state, so it is an `ok` line
        # rather than a refusal, as adopt's is. A stale dep-of row still exits DRIFT.
        ui.ok(f"Nothing to restore: every recorded {args.type or 'artifact'} is already linked.")
        remaining = unlinked(provenance, installed, args.type)
        if not remaining:
            return errors.OK
        return summarise(0, 0, 0, [], remaining, args.type, errors.OK)

    first_failure = errors.OK

    def refuse(plan_):
        nonlocal first_failure
        fail(plan_.code, plan_.message)
        if first_failure == errors.OK:
            first_failure = plan_.code

    # Never global: the manifest is project-scoped by construction, since
    # add.provenance_entries records nothing for an artifact landing in ~/.claude.
    if args.dry_run:
        plans = [
            add.plan(catalog, effective, kind, name, False, home, project, provenance)
            for kind, name in missing
        ]
        for plan_ in plans:
            if plan_.refused:
                refuse(plan_)
        preview(plans, present, args.type, project)
        return first_failure

    ui.title(f"{TITLE} Restoring from {ui.path(path)}:")
    linked = restored = 0
    for kind, name in missing:
        plan_ = add.install_one(catalog, effective, kind, name, False, home, project)
        if plan_.refused:
            refuse(plan_)
            continue
        restored += 1
        linked += len(plan_.steps)

    remaining = unlinked(provenance, scope.installed_pairs(project, claude), args.type)
    return summarise(linked, restored, len(missing), present, remaining, args.type, first_failure)
