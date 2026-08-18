"""`claude-kit list`.

The layout came from `claude-skill list`, the fish function this replaced: same header,
markers, colours and suffix order, so the two were indistinguishable while both shipped.
Palette in colors.py, line vocabulary in ui.py, and test_list_format pins every row
shape as a literal, escape codes included.

    🧩 Available skills:
      ✓ coderabbit (linked) [productivity, review, workflow]
      · cc-review [ai, claude, global, prompt engineering] (needs: skill-writer)
      ✓ jira (linked) [productivity, tasks, workflow] (global for ac, research)
      ↓ never-fetched (not downloaded) [engineering]

Two suffixes answer "why is this here", from the two places that can answer it:
`(global for X)` is a registry edge that pulled a skill into ~/.claude, `(installed for
X)` a recorded project dependency. Only one can ever apply to a row.

The emoji sits on the heading and nowhere else: rows carry a status glyph, which is
single-width and keeps the suffix columns aligned.

Read-only, so it never refuses for want of a project: in $HOME, the one directory that
is not one, it reports global state and says so.

`--json` prints `rows()` verbatim instead of rendering it, which is what makes this
command the one source the Television cables read. They used to re-derive the
catalogue, the dependency_only hiding, the effective global set and link status in jq
and fish, against a *different* rule for what a project is, so a directory that is not
a git repo showed every skill as available while this command showed them linked.
Nothing on stdout but the payload, then: the $HOME aside goes to stderr and neither
the heading nor the closing count is printed at all.
"""

import json
import sys
from pathlib import Path

from .. import catalog as cat
from .. import errors, paths, scope, state
from ..cli import fail
from dotkit import colors, ui

LINKED = "linked"
AVAILABLE = "available"
MISSING = "missing"

GROUPS_HEADER = "📚 Available groups:"

HEADER = {
    cat.SKILL: "🧩 Available skills:",
    cat.AGENT: "🤖 Available agents:",
    cat.PLUGIN: "🔌 Available plugins:",
}


def rows(catalog, kind, effective, home, project, provenance, group=None, claude=None):
    """One row per visible artifact of `kind`, as dicts.

    Pure: takes resolved inputs and returns data, so filtering and annotation are
    testable without a filesystem or a terminal.

    Ordering is everything present on disk first, then registry entries never
    downloaded: the walk reads the filesystem and backfills from the registry, which puts
    the two states in separate alphabetical runs.
    """
    present, absent = [], []
    # Derived here rather than passed in: it is a pure function of the catalog this
    # already holds, and a seventh resolved input would have to be threaded through
    # every caller to say something none of them decide.
    global_parents = scope.global_parents(catalog)
    # cat.visible drops the dependency-only skills: offering one here would be an
    # invitation to a refusal, since it cannot be added directly.
    for art in cat.visible(catalog, kind):
        if isinstance(group, str) and group not in art.groups:
            continue

        where = scope.installed_scope(art, home, project, claude)
        on_disk = art.source is not None and art.source.exists()
        reason = provenance.get((kind, art.name))
        # An untagged artifact sitting in ~/.claude can only have got there via
        # --global, so its presence is the evidence. No pin file needed.
        is_global = scope.belongs_global(art, effective) or where == scope.GLOBAL
        # Only what a row renders. `tagged_global` and `origin` used to sit here too:
        # nothing read either, both are one attribute lookup away on the artifact, and
        # every hand-written row fixture had to mirror them.
        #
        # `parent` and `global_for` are both "why is this here", from the two sources
        # that can answer it, and they are separate keys because they answer for
        # different scopes: `parent` is a recorded project install, `global_for` a
        # registry edge into ~/.claude. Collapsing them would leave a reader unable to
        # tell a stored decision from a derived one.
        row = {
            "name": art.name,
            "state": LINKED if where else (AVAILABLE if on_disk else MISSING),
            "installed": where,
            "global": is_global,
            "groups": tuple(sorted(set(art.groups))),
            "dependencies": tuple(sorted(set(art.dependencies))),
            "reason": reason,
            "parent": state.parent_of(reason) if reason else None,
            "global_for": global_parents.get(art.name, ()) if art.type == cat.SKILL else (),
        }
        (present if on_disk else absent).append(row)
    return present + absent


def _marker(row, indent):
    """The name and its state marker.

    The whole "↓ name (not downloaded)" run is dimmed rather than just the glyph,
    which is why this returns three shapes instead of one.
    """
    if row["state"] == LINKED:
        tick = colors.paint("✓", "green")
        return f"{indent}{tick} {row['name']} {colors.paint('(linked)', 'green')}"
    if row["state"] == AVAILABLE:
        return f"{indent}{colors.paint('·', 'dim')} {row['name']}"
    label = "↓ {} (not downloaded)".format(row["name"])
    return f"{indent}{colors.paint(label, 'dim')}"


def _scope_label(row):
    """The `(global…)` marker, naming what pulled the artifact into ~/.claude.

    A skill global only via a dependency (jira, documentation-and-adrs,
    planning-and-task-breakdown) carries no `global` tag, so without the parents the
    marker could only say `(global)` and leave the obvious next question unanswered:
    nothing the user typed mentions the skill, so nothing explains why `add` refuses it.
    Naming the parent is the whole point, and the registry knows it.

    A bare `(global)` remains the answer for a tagged artifact and for one hand-linked
    into ~/.claude with --global, where no edge exists to name.
    """
    if not row["global_for"]:
        return "(global)"
    return "(global for " + ", ".join(row["global_for"]) + ")"


def format_row(row, indent="  ", show_groups=True):
    """Render one row.

    show_groups=False is the grouped view, where the tag is already the heading, so the
    scope marker takes the place of the full group list.
    """
    parts = [_marker(row, indent)]

    if show_groups:
        if row["groups"]:
            parts.append(colors.paint("[" + ", ".join(row["groups"]) + "]", "cyan"))
        # Only when the groups suffix does not already carry `global`, which is the
        # tagged case. Printing both would be the same fact twice on one row.
        if row["global"] and "global" not in row["groups"]:
            parts.append(colors.paint(_scope_label(row), "dim"))
    elif row["global"]:
        parts.append(colors.paint(_scope_label(row), "dim"))

    if row["dependencies"]:
        parts.append(colors.paint("(needs: " + ", ".join(row["dependencies"]) + ")", "dim"))
    if row["parent"]:
        parts.append(colors.paint(f"(installed for {row['parent']})", "dim"))
    return " ".join(parts)


def grouped(listed):
    """Rows bucketed by tag, for `--group` with no tag given."""
    buckets = {}
    for row in listed:
        for tag in row["groups"]:
            buckets.setdefault(tag, []).append(row)
    return sorted(buckets.items())


def run(args):
    # A bare `--group` asks for the grouped *view*, and JSON has no view: each row
    # already carries its tags, so bucketing them is the caller's to do. Refused before
    # any I/O, since it is a decision about the flags alone.
    if args.json and args.group is True:
        return fail(
            errors.USAGE,
            "--json emits rows, and a bare --group asks for a rendering of them. Every "
            "row carries its `groups`, so bucket them downstream.\n"
            f"  Run: claude-kit list --type {args.type} --json",
        )

    claude = paths.claude_dir()
    home = paths.home()
    catalog = cat.build_catalog(claude)
    effective = scope.global_set(catalog)
    project = scope.project_root(Path.cwd(), home)
    provenance = state.read(project)

    listed = rows(catalog, args.type, effective, home, project, provenance, args.group, claude)

    if project is None:
        # stderr under --json: the aside is still worth reading, and stdout is a payload
        # a caller parses.
        ui.note(
            "Running in $HOME, which is never a project, so only global state is shown.",
            indent=0,
            stream=sys.stderr if args.json else None,
        )

    if args.json:
        print(json.dumps(listed))
        return errors.OK

    if args.group is True:
        # `--group` with no tag: the grouped view.
        ui.title(GROUPS_HEADER)
        for tag, members in grouped(listed):
            print(f"  {colors.paint(tag + ':', 'cyan')}")
            for row in members:
                print(format_row(row, indent="    ", show_groups=False))
        return errors.OK

    ui.title(HEADER[args.type])
    for row in listed:
        print(format_row(row))

    visible = cat.visible(catalog, args.type)
    installed = sum(1 for row in listed if row["installed"])
    ui.blank()
    if isinstance(args.group, str):
        ui.done(
            f"{len(listed)} of {len(visible)} {args.type}s tagged "
            f"'{args.group}', {installed} installed"
        )
    else:
        ui.done(f"{len(listed)} {args.type}s, {installed} installed")
    return errors.OK
