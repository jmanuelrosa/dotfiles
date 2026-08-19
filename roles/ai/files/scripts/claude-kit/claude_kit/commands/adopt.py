"""`claude-kit adopt`: rebuild a missing claude-kit.json from what is on disk.

A project only acquires a provenance file by being set up with claude-kit, so two
ordinary situations leave links with no record: cloning a repo that ships
.claude/skills/ but not the manifest, and every project set up before claude-kit existed,
by the fish functions it replaced, which never wrote one.

Those projects degrade quietly rather than loudly. `remove` takes the "no record,
so keep it" branch and the cascade never fires, while `doctor` files each link as
an untracked-install note. The project then accumulates dependency links nothing
needs and no command will ever clean up.

What can and cannot be recovered:

  recoverable    whether anything installed *declares* an artifact. That is a fact
                 about the registry read against the current directory, not about
                 history, so it survives the loss of the file.
  lost           whether a declared skill was *also* named directly at some point.
                 History A and History B leave byte-identical directories, and
                 state.py exists precisely because state cannot recover that.

So a declared skill is recorded as a dependency, which is what a clean
`add <parent>` would have written and what did in fact happen in the common case:
eight of the ten dependency edges in the registry point at ordinary addable
skills, so treating the ambiguous case as direct would leave this command doing
almost nothing. The cost when the guess is wrong is one link cascading away that
one command restores, and `remove` prints everything it cascaded.

Writes claude-kit.json, and converges the `.agents/` links pi reads. No `.claude/`
symlink is created, moved or deleted: the pi links are a derived view of what is
already there, and the projects this command exists for are the ones most likely
to be missing them.
"""

from pathlib import Path

from .. import catalog as cat
from .. import errors, paths, pi, scope, state
from dotkit import ui
from ..cli import fail


def declared_by(catalog, installed):
    """Which installed artifacts declare each installed skill, as {skill: [names]}.

    Only skills appear as keys. Every dependency edge in either registry, and every
    entry in a plugin's skillDependencies, names a skill, so nothing else can be
    reached this way.
    """
    out = {}
    for key in sorted(installed):
        art = cat.get(catalog, *key)
        if art is None:
            continue
        for dep in art.dependencies:
            if (cat.SKILL, dep) in installed:
                out.setdefault(dep, []).append(art.name)
    return out


def infer(catalog, installed, provenance, kind=None):
    """Provenance to record as {(type, name): reason}. Pure.

    An artifact already in `provenance` is skipped, which is what makes this
    idempotent and lets it top up a partially recorded project. Skipping rather
    than recomputing also means a recorded `direct` can never be demoted to a
    dependency, so re-running after an `add` cannot arm the cascade against
    something the user named.

    `kind` narrows the *output*, never the inputs, exactly as doctor.collect does.
    An installed agent or plugin has to stay visible to the parent lookup even
    under `--type skill`, or a skill would be called direct because the artifact
    that needs it was filtered out before the question was asked.
    """
    parents = declared_by(catalog, installed)
    entries = {}
    for key in sorted(installed):
        if key in provenance:
            continue
        artifact_kind, name = key
        if kind is not None and artifact_kind != kind:
            continue
        # sorted()[0] rather than a real choice among several dependants. The
        # recorded parent is display-only: remove.cascade recomputes dependants
        # from the registry and consults the record solely through is_direct, so
        # which name is stored changes the wording of `list` and doctor's
        # `removable` note, never what gets deleted.
        candidates = parents.get(name) if artifact_kind == cat.SKILL else None
        entries[key] = state.dep_of(sorted(candidates)[0]) if candidates else state.DIRECT
    return entries


def report(entries, kind, dry_run, project, emit=print):
    """Print what was or would be recorded. Returns the exit code.

    Always OK. Finding nothing to adopt is the healthy state, not a refusal.
    """
    if not entries:
        emit(
            ui.render(
                "ok", f"Nothing to adopt: every installed {kind or 'artifact'} is already recorded."
            )
        )
        return errors.OK

    verb = "Would record" if dry_run else "Recorded"
    emit(ui.render("title", f"📋 {verb} in {ui.path(state.path_for(project))}:"))
    labels = {key: f"{key[0]} '{key[1]}'" for key in entries}
    width = max(len(label) for label in labels.values())
    for key, reason in sorted(entries.items()):
        emit(f"  {labels[key].ljust(width)}  {reason}")
    emit("")

    counts = {}
    for artifact_kind, _ in entries:
        counts[artifact_kind] = counts.get(artifact_kind, 0) + 1
    emit(ui.render("done", ", ".join(f"{counts[k]} {k}(s)" for k in sorted(counts)) + "."))
    if dry_run:
        emit(ui.render("note", "Nothing written (--dry-run).", indent=0))
    return errors.OK


def run(args):
    claude = paths.claude_dir()
    home = paths.home()
    project = scope.project_root(Path.cwd(), home)

    if project is None:
        return fail(
            errors.NO_PROJECT,
            "$HOME is the one directory that cannot be a project: its .claude is "
            "~/.claude, which carries no provenance because a global dependency "
            "never cascades.\n"
            "  cd into the project whose links you want to adopt.",
        )

    catalog = cat.build_catalog(claude)
    entries = infer(
        catalog, scope.installed_pairs(project, claude), state.read(project), args.type
    )
    if entries and not args.dry_run:
        state.record(project, entries)
    if not args.dry_run:
        # The one thing written besides the manifest, and it is written for the same
        # reason the manifest is: this command's population is the projects that
        # predate claude-kit, which is exactly the population with no .agents/ link
        # and therefore no skills visible to pi. Converging is idempotent and derived
        # from the disk, so it records nothing and is safe when there was nothing to
        # adopt. Unlike the manifest it does not depend on `entries`: a project whose
        # every link is already recorded can still be missing pi's view of them.
        pi.report(pi.converge(project), project)
        pi.report_agents(pi.converge_agents(project), project)
    return report(entries, args.type, args.dry_run, project)
