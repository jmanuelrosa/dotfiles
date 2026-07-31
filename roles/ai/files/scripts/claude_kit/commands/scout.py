"""`claude-kit scout`: what this project is missing, ranked.

Every other command starts from a name you already know. This one starts from the
directory: it fingerprints the project (fingerprint.py), matches that fingerprint
against the catalogue's group tags, and prints a shortlist. Answering "what should
I install here" therefore needs no prior knowledge of what exists, which is the
gap between `list` — the whole catalogue, alphabetically, telling you nothing
about relevance — and `add`, which already assumes the answer.

Read-only unless `--add`, which installs the strong tier and only the strong tier.
The weaker tier is a prompt to go and look, not a recommendation to act on, so no
flag installs it.

`--type` is optional here for the same reason as on `doctor` and `adopt`: a
project's stack implies artifacts of all three kinds — a React repo wants react
skills and the frontend seat plugin — and a required `--type` would make a partial
answer the only one available. Given, it narrows the whole report.

Nothing already available here is ever offered, and "available" is wider than
"linked in this project": it covers ~/.claude too, and anything that *belongs* in
~/.claude whether or not `sync` has run yet. Offering a global artifact would be
offering to install what every project already loads.
"""

import json
import textwrap
from dataclasses import dataclass
from pathlib import Path

from .. import catalog as cat
from .. import colors, errors, fingerprint, frontmatter, paths, scope, ui
from ..cli import fail
from . import add

# How many artifacts a report may name before it stops being a shortlist. Strong
# matches take from this first; the weaker tier gets whatever is left, so a
# well-covered project sees no guesses at all.
SHORTLIST_CAP = 12

# Descriptions are written for a model and run long — several are a paragraph. The
# report wants the gist, not the contract.
DESCRIPTION_CAP = 220
WRAP = 100

STRONG = "Strong match"
CONSIDER = "Worth considering"
ALREADY = "Already in this project"

HEADER = "🔎 Scouting {}"

TYPE_ORDER = (cat.SKILL, cat.AGENT, cat.PLUGIN)


@dataclass(frozen=True)
class Match:
    """One recommendation, carrying the reason it was made."""

    name: str
    kind: str
    groups: tuple
    description: str
    # The evidence string for the tag that put it here, printed verbatim.
    why: str
    # How many of the project's tags it carries. Ranks within a tier, never across.
    score: int


def describe(art):
    """A one-line gist of what an artifact does, or "".

    Three sources because the three types keep their prose in three places: a
    skill's SKILL.md frontmatter, an agent's own frontmatter, a plugin's manifest.
    """
    if art.source is None:
        return ""
    if art.type == cat.PLUGIN:
        manifest = art.source / cat.PLUGIN_MANIFEST
        try:
            data = json.loads(manifest.read_text(errors="replace"))
        except (OSError, ValueError):
            return ""
        if not isinstance(data, dict):
            return ""
        return " ".join(str(data.get("description") or "").split())
    path = art.source / "SKILL.md" if art.type == cat.SKILL else art.source
    try:
        return frontmatter.description(path.read_text(errors="replace"))
    except OSError:
        return ""


def available(catalog, effective, kinds, home, project, claude):
    """(candidates, already) for the selected types. Both name-ordered.

    A candidate is something scout may offer; `already` is what the project has, so
    the report can say "and you already have these" rather than silently omitting
    them and looking like it missed something.

    Three exclusions, and each drops the artifact from *both* lists:

      dependency-only  installs with whatever needs it and refuses to be named, so
                       offering it would be an invitation to a refusal.
      global           available in every project already, whether by tag or by a
                       link somebody made in ~/.claude by hand.
      missing on disk  registered but never downloaded. `update` fetches it; until
                       then `add` would refuse, so recommending it is a dead end.
    """
    candidates, already = [], []
    for kind in kinds:
        for art in cat.visible(catalog, kind):
            if scope.belongs_global(art, effective):
                continue
            where = scope.installed_scope(art, home, project, claude)
            if where == scope.GLOBAL:
                continue
            if where == scope.PROJECT:
                already.append(art)
                continue
            if art.source is None or not art.source.exists():
                continue
            candidates.append(art)
    return candidates, already


def reason(matched, evidence, focus):
    """Which of the matched tags explains the recommendation.

    The focus first, when it is one of them, because it is what the reader asked
    about. Then the most specific tag, which is the one naming a technology. Only
    then alphabetical, so the fallback is at least stable.

    Without this the reason is whichever tag happens to sort first, and the `qa`
    seat — matching a project with no tests on `testing` — justified itself with
    `observability` instead.
    """
    if focus and focus in matched:
        return evidence[focus]
    for tag in matched:
        if tag in fingerprint.TECH_TAGS:
            return evidence[tag]
    return evidence[matched[0]]


def rank(candidates, direct, indirect, focus):
    """Split candidates into the two tiers. Pure.

    A tag with direct project evidence makes a strong match; a merely implied one
    makes it worth considering. Direct wins outright, so an artifact carrying both
    never lands in the weaker tier.

    `focus` only orders here — it sorts its own matches to the front of whichever
    tier they earned. The promotion happens one level up, in run(), which enters the
    focus tag into `direct` before calling this: asking for a tag is itself the
    evidence for it, so an artifact carrying it is a strong match and `--add` takes
    it. Keeping the two apart is what lets this function be tested for ordering
    alone.
    """
    # Naming a broad tag is the one way to mean it, so the focus is exempt from the
    # subtraction below. Otherwise `--focus observability` would quietly match
    # nothing at all, which reads as "no such tag" rather than "not by default".
    broad = fingerprint.BROAD_TAGS - {focus} if focus else fingerprint.BROAD_TAGS
    strong, consider = [], []
    for art in candidates:
        tags = set(art.groups) - broad
        # An artifact built for a framework the project does not use is noise,
        # however well its broader tags match.
        wanted_tech = tags & fingerprint.TECH_TAGS
        if wanted_tech and not wanted_tech & set(direct):
            continue
        hits = sorted(tags & set(direct))
        soft = sorted(tags & set(indirect))
        if hits:
            bucket, matched, evidence = strong, hits, direct
        elif soft:
            bucket, matched, evidence = consider, soft, indirect
        else:
            continue
        bucket.append(
            Match(
                name=art.name,
                kind=art.type,
                groups=tuple(art.groups),
                description=describe(art),
                why=reason(matched, evidence, focus),
                score=len(matched),
            )
        )

    def order(match):
        return (0 if focus and focus in match.groups else 1, -match.score, match.kind, match.name)

    return sorted(strong, key=order), sorted(consider, key=order)


def shortlist(strong, consider, cap=SHORTLIST_CAP):
    """Both tiers trimmed to a combined `cap`, strong matches served first."""
    strong = strong[:cap]
    return strong, consider[: max(cap - len(strong), 0)]


def install_commands(matches):
    """The commands that install `matches`, one per type.

    Not one command: `--type` applies to every name in a call, so a mixed
    shortlist cannot honestly be written as a single line.
    """
    by_kind = {}
    for match in matches:
        by_kind.setdefault(match.kind, []).append(match.name)
    return [
        f"claude-kit add {' '.join(by_kind[kind])} --type {kind}"
        for kind in TYPE_ORDER
        if kind in by_kind
    ]


def _add_differs(strong, offered):
    """How the install command above differs from what `--add` would do.

    An empty strong tier gets its own sentence rather than "the 0 strong matches",
    which is arithmetic where the reader wants an answer: the honest reading is
    that `--add` has nothing to install here.
    """
    if not strong:
        return "`--add` would install nothing: every match here is a guess."
    plural = "" if len(strong) == 1 else "es"
    return (
        f"That installs all {len(offered)}. `--add` takes only the "
        f"{len(strong)} strong match{plural}."
    )


def _row(match, show_kind):
    """One recommendation's headline: the name, its type when ambiguous, its tags.

    Composed by hand rather than through ui.item because only the glyph and the
    suffixes are painted, exactly as `list` composes its rows.
    """
    parts = [f"  {colors.paint('·', 'dim')} {match.name}"]
    if show_kind:
        parts.append(colors.paint(f"({match.kind})", "dim"))
    if match.groups:
        parts.append(colors.paint("[" + ", ".join(match.groups) + "]", "cyan"))
    return " ".join(parts)


def render(strong, consider, already, focus, project, emit=print):
    """Print the report and return the artifacts it offered, in display order.

    `emit` is the seam the tests capture on, as in doctor.report: a helper that
    could only print would put the palette out of their reach.
    """
    offered = [*strong, *consider]
    # More than one type in play, so a bare name no longer says which command
    # installs it. With one type the suffix would be on every row and inform nobody.
    show_kind = len({match.kind for match in offered}) > 1

    emit(ui.render("title", HEADER.format(ui.path(project))))
    emit("")

    # Without this a focus that matched nothing installable reads as an ordinary
    # report, and the unrelated fallback picks look like the answer to it.
    if focus and offered and not any(focus in match.groups for match in offered):
        emit(ui.render("warn", f"Nothing available carries the '{focus}' tag. Showing the rest."))
        emit("")

    for title, matches in ((STRONG, strong), (CONSIDER, consider)):
        if not matches:
            continue
        emit(ui.render("title", title))
        for match in matches:
            emit(_row(match, show_kind))
            emit(ui.render("note", f"Why:  {match.why}", indent=4))
            if match.description:
                gist = textwrap.shorten(match.description, DESCRIPTION_CAP, placeholder=" …")
                emit(
                    ui.render(
                        "note",
                        textwrap.fill(
                            gist,
                            width=WRAP,
                            initial_indent="What: ",
                            subsequent_indent="      ",
                        ).replace("\n", "\n    "),
                        indent=4,
                    )
                )
        emit("")

    if already:
        emit(ui.render("title", ALREADY))
        for art in already:
            tick = colors.paint("✓", "green")
            suffix = f" {colors.paint('(' + art.type + ')', 'dim')}" if show_kind else ""
            emit(f"  {tick} {art.name}{suffix}")
        emit("")

    if offered:
        for command in install_commands(offered):
            emit(ui.render("step", command))
        # The command above takes everything shown; --add takes the strong tier
        # alone. Reading one as shorthand for the other is the obvious mistake to
        # make, and it is only visible from the counts, so say it outright. Silent
        # when the tiers agree, since then there is no difference to warn about.
        if consider:
            emit(ui.render("note", _add_differs(strong, offered)))
    else:
        reason = (
            f"No artifact matches the focus '{focus}'."
            if focus
            else "Nothing left to add: everything relevant is already installed."
        )
        emit(ui.render("ok", reason))

    emit(
        ui.render(
            "done",
            f"{len(strong)} strong, {len(consider)} worth considering, "
            f"{len(already)} already here",
        )
    )
    return offered


def install(catalog, effective, matches, home, project):
    """Install the strong tier. Returns the first failure's code, or OK.

    Goes through add.install_one rather than linking directly, so a recommendation
    accepted here resolves dependencies and records provenance exactly as one typed
    by hand does. Nothing scout offers is global, so want_global is always False.
    """
    first_failure = errors.OK
    for match in matches:
        plan_ = add.install_one(catalog, effective, match.kind, match.name, False, home, project)
        if not plan_.refused:
            continue
        fail(plan_.code, plan_.message)
        if first_failure == errors.OK:
            first_failure = plan_.code
    return first_failure


def run(args):
    claude = paths.claude_dir()
    home = paths.home()
    project = scope.project_root(Path.cwd(), home)

    if project is None:
        return fail(
            errors.NO_PROJECT,
            "scout reads a project to decide what it needs, and $HOME is the one "
            "directory that cannot be a project: its .claude is ~/.claude, which "
            "already holds everything tagged global.\n"
            "  cd into the project you want recommendations for.",
        )

    catalog = cat.build_catalog(claude)
    effective = scope.global_set(catalog)
    kinds = (args.type,) if args.type else TYPE_ORDER
    candidates, already = available(catalog, effective, kinds, home, project, claude)

    direct = fingerprint.read(project)
    indirect = fingerprint.implied(direct)
    if not fingerprint.covered(direct):
        # The stack is one the catalogue has no artifacts for. These are guesses, so
        # they join the implied map rather than inflating the strong tier.
        for tag, evidence in fingerprint.fallback(direct).items():
            indirect.setdefault(tag, evidence)
    if args.focus:
        # A tag is opaque here, so a typo is indistinguishable from a real tag that
        # simply matched nothing: both print the unfocused report and exit 0. Say so,
        # rather than letting a misspelt focus look like it worked. Checked against the
        # whole catalogue, not the candidates, so this means "no such tag" and not
        # "nothing left to offer under it".
        if not any(cat.in_group(catalog, kind, args.focus) for kind in TYPE_ORDER):
            ui.warn(f"nothing in the catalogue carries '{args.focus}', so --focus did nothing")
            ui.note("`claude-kit list` prints each artifact with its tags.")

        # Asking for a tag is itself the evidence for it, so the focus enters as
        # *direct* and its artifacts become strong matches — which `--add` then
        # takes. That promotion is the point of the flag rather than a side effect:
        # a focus `--add` ignored would be a filter that filters nothing. It also
        # outranks an implied hit on the same tag, whose weaker reason would
        # otherwise be what prints.
        direct.setdefault(args.focus, f"requested focus '{args.focus}'")
        indirect.pop(args.focus, None)

    strong, consider = shortlist(*rank(candidates, direct, indirect, args.focus))
    render(strong, consider, already, args.focus, project)

    if not args.add or not strong:
        return errors.OK
    ui.blank()
    return install(catalog, effective, strong, home, project)
