"""`claude-kit converge`: make pi's view of a project match Claude Code's.

Every other command that touches `.agents/` does it as a side effect of installing or
removing something. That is the whole gap: a project provisioned before `pi.py` existed,
or one whose link was deleted by hand, stays invisible to pi until somebody happens to
run `add` there. `doctor` reported it (G19, G20) and pointed at commands that install.

This command does only the convergence. It resolves no dependencies, records nothing in
`claude-kit.json`, fetches nothing, and installs nothing, which is what makes it safe to
fire from a SessionStart hook and from the `ai` role on every apply. Everything it can
write is the two `.agents` leaves and the ignore file beside them, and every refusal it
can make is `pi.converge`'s own.

Two shapes, and the second is the point:

  - **`converge`** acts on the cwd, like every other project command.
  - **`converge --all`** sweeps `projects.discover`, which is Claude Code's own project
    registry unioned with a walk of `~/Developer`. That is the one pass that clears a
    backlog nobody is standing in.

In `$HOME` with no `--all` it reports that and exits OK rather than refusing, following
`doctor` rather than `add`. `$HOME` is never a project, and a hook that fires wherever a
session starts must not paint a refusal for a directory where there was nothing to do.
"""

import sys
from pathlib import Path

from .. import errors, paths, pi, projects, scope
from dotkit import ui

TITLE = "🔗"


def one(project, dry_run=False):
    """Converge both halves of one project's pi view. Returns (skills, agents).

    The two are converged separately and fail separately, exactly as G19 and G20 are two
    checks: a project can have a foreign `.agents/skills` and perfectly good agent links.
    """
    skills = pi.converge(project, dry_run=dry_run)
    agents = pi.converge_agents(project, dry_run=dry_run)
    # The ignore file is converged rather than only written when a leaf is created, so a
    # project linked before it existed, or one where it was deleted by hand, gets it on
    # the next sweep. `write_ignore` never overwrites, so this cannot take a file that is
    # somebody else's, and it is a single `exists()` on a steady-state run.
    if not dry_run and pi.is_ours(project):
        pi.write_ignore(project)
    return skills, agents


def changes(skills, agents):
    """How many links one project's convergence touched. Pure.

    A `blocked` skills answer is not a change: nothing was written, and counting it would
    make the summary claim work the run refused to do.
    """
    count = 1 if skills in ("linked", "unlinked") else 0
    if agents is not None:
        count += len(agents.linked) + len(agents.pruned)
    return count


def blocked(skills, agents):
    """Whether this project ended up short of what pi should see. Pure.

    A collision is deliberately not blocking. Two plugins shipping one agent filename is
    a fact about this repo's registries rather than about the project being swept, and
    failing every sweep on it would make the exit code useless for the thing it is for.
    """
    if skills == "blocked":
        return True
    if agents is None:
        return False
    return bool(agents.blocked) or agents.blocked_dir


def summary(total, count, dry_run):
    """The closing line, and the one the `ai` role reads to decide `changed`.

    Shaped like `sync`'s deliberately: both keep `, 0 changes` as a stable thing for a
    `changed_when` to match on, and test_converge.py pins the wording for the same
    reason test_provision.py pins that one.
    """
    projects_word = "project" if total == 1 else "projects"
    if count == 0:
        return ui.done(f"{total} {projects_word}, 0 changes")
    tail = ", dry run" if dry_run else ""
    return ui.done(f"{total} {projects_word}, {count} changes{tail}")


def targets(args, home):
    """The projects this run acts on, or None when there is nothing to act on.

    None is not an error. It means the cwd is `$HOME`, where a project view cannot
    exist, and the caller reports that the way `doctor` does.
    """
    if args.all:
        roots = [Path(root) for root in args.roots] if args.roots else None
        return projects.discover(home, roots)
    project = scope.project_root(Path.cwd(), home)
    return None if project is None else [project]


def run(args):
    home = paths.home()
    dry_run = args.dry_run
    # Quiet means "nothing on stdout", not silence. Claude Code feeds a SessionStart
    # hook's stdout into the session as context, so an ordinary report there would spend
    # tokens on a line about a symlink; a warning still has to reach a human.
    stream = sys.stderr if args.quiet else None

    found = targets(args, home)
    if found is None:
        if not args.quiet:
            ui.note(
                "Running in $HOME, which is never a project, so there is no pi view to "
                "converge. Use --all to sweep every project instead."
            )
        return errors.OK

    if not args.quiet:
        scoped = "every project" if args.all else "this project"
        verb = "Checking" if dry_run else "Converging"
        ui.title(f"{TITLE} {verb} pi's view of {scoped}")

    count = 0
    refused = False
    for project in found:
        skills, agents = one(project, dry_run=dry_run)
        pi.report(skills, project, dry_run=dry_run, stream=stream)
        pi.report_agents(agents, project, dry_run=dry_run, stream=stream)
        count += changes(skills, agents)
        refused = blocked(skills, agents) or refused

    if not args.quiet:
        summary(len(found), count, dry_run)
    # A blocked path is a real conflict a person has to resolve, and it leaves pi short
    # of what the project holds. Same reading as sync's: reporting it and exiting 0 is
    # how it goes unnoticed.
    return errors.DRIFT if refused else errors.OK
