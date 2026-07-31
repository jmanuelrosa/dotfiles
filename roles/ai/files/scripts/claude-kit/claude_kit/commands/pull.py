"""`claude-kit update` and `claude-kit outdated`.

One module because they are the same traversal with writes switched off. Sharing the
code is the point: a separate `outdated` implementation could disagree with `update`
about what "behind" means, and then the report would not predict the sync.

Named `pull` rather than `sync`, which it was: `claude-kit sync` is a different
command, in provision.py, and it converges ~/.claude rather than fetching anything.
Two unrelated meanings of one word in one CLI is the confusion the rename avoids.

Skills only. agent-registry.json has no repos and plugins are authored here, so
nothing else has an upstream to compare against.

Neither command touches a project. They update the dotfiles checkout itself, so they
work from any cwd.

The layout came from `claude-skill update` / `claude-skill outdated`, the fish functions
this replaced: cyan repo rules, glyphs, state colours, dim `(last synced …)` suffix and
`Done:` tally. Palette in colors.py.
"""

import tempfile
from pathlib import Path

from .. import catalog as cat
from .. import errors, paths, registry, upstream
from dotkit import colors, ui
from ..cli import fail

BEHIND = "behind"
CURRENT = "current"
ABSENT = "absent"
SYNCED = "synced"
INSTALLED = "installed"
FAILED = "failed"

# Glyph, colour and label per state. The glyph and the label share a colour, and the
# state is read off the colour as much as the text: green means untouched, blue means
# written, red means a sync is waiting.
STYLE = {
    BEHIND: ("⟳", "red", "behind"),
    CURRENT: ("✓", "green", "up to date"),
    ABSENT: ("↓", "yellow", "not downloaded"),
    SYNCED: ("⟳", "blue", "✓ synced."),
    INSTALLED: ("✓", "blue", "installed (new)"),
    # The reason is the whole message for a failure, so there is no label to colour.
    FAILED: ("✗", "magenta", None),
}

# Which counts a `Done:` line reports, in order, and the colour of each. `outdated`
# names the states it found; `update` names what it did, so a sync and a fresh install
# are one "updated" count.
TALLY = {
    "outdated": (
        ("behind", "red", (BEHIND,)),
        ("up-to-date", "green", (CURRENT,)),
        ("not downloaded", "yellow", (ABSENT,)),
        ("failed", "magenta", (FAILED,)),
    ),
    "update": (
        ("updated", "blue", (SYNCED, INSTALLED)),
        ("up-to-date", "green", (CURRENT,)),
        ("failed", "magenta", (FAILED,)),
    ),
}


def targets(catalog, names):
    """Skills to act on, grouped by upstream repo.

    Returns (by_repo, local, unknown). Local skills are reported rather than
    skipped: naming one is a reasonable mistake and deserves an explanation.
    """
    wanted = set(names) if names else None
    by_repo = {}
    local = []
    found = set()

    for skill in cat.of_type(catalog, cat.SKILL):
        if wanted is not None and skill.name not in wanted:
            continue
        found.add(skill.name)
        if skill.has_upstream:
            by_repo.setdefault(skill.upstream_repo, []).append(skill)
        else:
            local.append(skill)

    unknown = sorted(wanted - found) if wanted else []
    return by_repo, local, unknown


def last_synced(skill):
    """The `updated_at` stamp as a date, which is all the granularity a row needs.

    It truncates the ISO timestamp to ten characters rather than parsing it, so an
    unparseable or absent stamp still renders instead of raising.
    """
    return (skill.updated_at or "never")[:10]


def classify(skill, checkout, destination):
    """What state this skill is in relative to upstream. Pure, given two trees.

    The second element is the detail: a parenthetical note for a normal state, and the
    whole message for FAILED, which is why format_result paints the two differently.
    """
    source = upstream.subtree(checkout, skill.upstream_path)
    if not source.is_dir():
        return FAILED, f"upstream_path '{skill.upstream_path}' is not in the tarball"
    if not destination.is_dir():
        return ABSENT, None
    # One note for both outcomes: they are the two most common rows, and building the
    # string per branch is how they drift apart.
    note = f"last synced {last_synced(skill)}"
    return (BEHIND if upstream.differs(source, destination) else CURRENT), note


def format_result(state, name, detail=None):
    """One `  ✓ name: label (note)` row."""
    glyph, colour, label = STYLE[state]
    parts = [f"  {colors.paint(glyph, colour)} {name}:"]
    if label:
        parts.append(colors.paint(label, colour))
    if detail:
        # A failure reason reads as prose and stays undimmed; everything else is a
        # de-emphasised parenthetical.
        parts.append(detail if state == FAILED else colors.paint(f"({detail})", "dim"))
    return " ".join(parts)


def format_tally(command, results):
    """The closing `✨ Done:` line, counting only the states this command reports."""
    parts = [
        f"{colors.paint(str(sum(1 for _, state, _ in results if state in states)), colour)} {label}"
        for label, colour, states in TALLY[command]
    ]
    return ui.render("done", f"{colors.paint('Done:', 'bold')} " + ", ".join(parts))


def process_repo(skills, claude, branch, repo, write, fetcher, workspace):
    """Fetch one repo once, then act on every skill tracked from it.

    One fetch per repo rather than per skill: a repo can supply many skills, and
    re-downloading it for each would be slower and could mix two upstream states
    into one run.

    Returns (fetch_error, results). A fetch error is one fact about the repo, so it is
    returned separately for the single `✗ FAILED to fetch` line, while every skill it
    stranded still gets a FAILED result so the tally counts them.
    """
    checkout = workspace / repo.replace("/", "_")
    try:
        fetcher(repo, branch, checkout)
    except upstream.FetchError as exc:
        # One unreachable repo must not abandon the others.
        return str(exc), [(skill, FAILED, str(exc)) for skill in skills]

    results = []
    for skill in skills:
        # catalog already resolved where this skill is stored, from the same STORE and
        # SUFFIX maps add, list and doctor read. Re-assembling the path here is how the
        # one command that writes artifact trees ends up writing where nothing looks.
        destination = skill.source
        state, detail = classify(skill, checkout, destination)
        if not write or state in (FAILED, CURRENT):
            results.append((skill, state, detail))
            continue
        source = upstream.subtree(checkout, skill.upstream_path)
        try:
            upstream.copy_tree(source, destination)
        except OSError as exc:
            # copy_tree swaps rather than deletes first, so a failed write leaves
            # the previous tree intact instead of destroying the skill.
            results.append((skill, FAILED, f"could not write {destination}: {exc}"))
            continue
        stamped = upstream.stamp()
        registry.stamp_entry(
            claude / cat.REGISTRY_FILE[cat.SKILL],
            repo,
            skill.upstream_path,
            stamped,
            collection=cat.COLLECTION[cat.SKILL],
        )
        # No note: the stamp is what was just written, so echoing it says only that the
        # clock works.
        results.append((skill, INSTALLED if state == ABSENT else SYNCED, None))
    return None, results


def run(args, fetcher=None):
    """fetcher is injectable so tests exercise everything but the network."""
    write = args.command == "update"
    fetcher = fetcher or upstream.fetch

    if args.type != cat.SKILL:
        return fail(
            errors.USAGE,
            f"only skills have upstreams, so `{args.command}` does not apply to "
            f"{args.type}s. Agents and plugins are authored in this repo.",
        )

    claude = paths.claude_dir()
    catalog = cat.build_catalog(claude)
    by_repo, local, unknown = targets(catalog, args.names)

    for name in unknown:
        fail(errors.NOT_FOUND, f"'{name}' is not a known skill.")

    count = len(by_repo)
    if write:
        ui.title(f"🔄 Syncing from {count} repo(s)...")
    else:
        ui.title(f"🔎 Checking {count} repo(s) for updates...")
    ui.blank()

    # Only when the user named one. On a bare run every locally authored skill is local,
    # and saying so thirteen times is what teaches a reader to skip the report.
    named_local = local if args.names else []
    for skill in named_local:
        ui.warn(f"'{skill.name}' is a local skill; no upstream to sync.", indent=2)
    if named_local:
        ui.blank()

    results = []
    with tempfile.TemporaryDirectory() as workspace:
        for repo in sorted(by_repo):
            skills = by_repo[repo]
            branch = skills[0].upstream_branch
            print(colors.paint(f"── {repo} ({branch}) ──", "cyan"))
            fetch_error, outcome = process_repo(
                skills, claude, branch, repo, write, fetcher, Path(workspace)
            )
            if fetch_error:
                # One line for the repo rather than the same error once per skill. Not
                # ui.err: this belongs in the run's report on stdout, next to the rows
                # for the skills it stranded, rather than on its own on stderr.
                print("  " + colors.paint(f"✗ FAILED to fetch: {fetch_error}", "magenta"))
            else:
                for skill, state, detail in outcome:
                    print(format_result(state, skill.name, detail))
            results.extend(outcome)
            print()

    print(format_tally(args.command, results))

    if unknown:
        return errors.NOT_FOUND
    # A fetch or write failure is the only thing either command calls failure.
    # Being behind is information: making `outdated` exit non-zero for it would
    # leave it usable only as a gate.
    if any(state == FAILED for _, state, _ in results):
        return errors.FETCH_FAILED
    return errors.OK
