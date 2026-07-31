"""`claude-kit sync`: converge ~/.claude on what the registries say belongs there.

This is the command the `ai` role calls, and it replaces the derivation, symlink and
prune block commit 0624d1c removed from roles/ai/tasks/main.yml. Nothing provisioned
~/.claude between that commit and this one.

Why it exists as a command rather than as Ansible: the set it converges on is
`scope.global_set`, which the tool already computes to answer "does this need
--global?". Expressed twice, in Jinja and in python, the two would drift, and the
Jinja copy was 130 lines nothing could unit-test.

**A convergence, not an install.** It links what belongs and unlinks what no longer
does, so it is the one command that deletes something nobody named. That is safe only
because the whole directory is role-owned, and three narrowings keep it that way:

  only symlinks             a real directory there is hand-authored content
  only into our own store   a link pointing anywhere else is somebody else's
  only when the set is not empty

The last is not paranoia. A registry that loses its `global` tags, or changes shape,
derives an empty set, and an empty set makes every existing link stale. Pruning to
zero is indistinguishable from working correctly right up until Claude Code loads no
skills at all, so it refuses instead.

Because it converges, a hand-made change here is transient by design: removing a
global link lasts until the next run, and `add --global` on an *untagged* artifact
lasts exactly as long. To keep either, change the `global` tag in the registry, which
is the only durable statement about what belongs.
"""

from dataclasses import dataclass, field

from .. import catalog as cat
from .. import errors, paths, scope
from dotkit import ui
from ..cli import fail

# What apply() reports doing. Only the three outcomes that touch the disk get a name:
# the rest are Plan fields and never appear in a result row.
LINKED = "linked"
RELINKED = "relinked"
PRUNED = "pruned"


@dataclass
class Plan:
    """What one run would do, as data. Pure: nothing here has touched the disk.

    Split from apply() for the same reason add.py is, plus one specific to this
    command: --dry-run has to print exactly what a real run would do, and the only
    way to guarantee that is for both to render the same plan.
    """

    link: list = field(default_factory=list)
    relink: list = field(default_factory=list)
    current: list = field(default_factory=list)
    prune: list = field(default_factory=list)
    blocked: list = field(default_factory=list)
    missing: list = field(default_factory=list)
    refusal: tuple = None

    @property
    def changes(self):
        return len(self.link) + len(self.relink) + len(self.prune)

    @property
    def belongs(self):
        """How many artifacts belong in ~/.claude, which is the only honest denominator.

        A pruned link is not one of them, so counting it here would report 21 of 21
        global artifacts on a run whose whole point was that one of the 21 was not.
        """
        return sum(
            len(bucket)
            for bucket in (self.link, self.relink, self.current, self.blocked, self.missing)
        )


def wanted(catalog, kind=None, effective=None):
    """Every artifact belonging in ~/.claude, ordered by type then name.

    `scope.belongs_global` is the authority, not a reimplementation of it: the tag for
    any type, plus the derived skills `scope.global_set` reaches through one level of
    declared dependencies (two for a global agent's skills). That derivation is why
    grilling, jira, domain-modeling, documentation-and-adrs and
    planning-and-task-breakdown belong here without carrying the tag.

    `kind` narrows to one type, and has to narrow both this and the prune scan: a
    `--type agent` run that pruned against the agent-only set would call every global
    skill stale. `effective` is passed in by plan() so one run derives it once.
    """
    if effective is None:
        effective = scope.global_set(catalog)
    return sorted(
        (
            art
            for art in catalog.values()
            if scope.belongs_global(art, effective) and (kind is None or art.type == kind)
        ),
        key=lambda art: (art.type, art.name),
    )


def stale(catalog, kind, home, claude, effective=None):
    """Global links of `kind` that no longer belong, as (type, name, path).

    `scope.installed_names` decides the type from which store a link resolves into
    rather than from its filename, which is the only thing that can: skills and
    plugins share the .claude/skills/ leaf, so a name alone counts every link as both
    and would offer each installed plugin up as a stale skill.

    That same check is what leaves a link pointing outside this repo alone, and
    `installed_names` yields symlinks only, so a real directory is never a candidate.
    """
    keep = {art.name for art in wanted(catalog, kind, effective)}
    return [
        (kind, name, path)
        for name, path in sorted(scope.installed_names(home, kind, claude).items())
        if name not in keep
    ]


def plan(catalog, kind, home, claude):
    """Decide what one run means. Pure apart from lstat and readlink.

    The refusal is returned rather than raised so --dry-run reports it too: learning
    that a real run would refuse is most of what a dry run is for.
    """
    result = Plan()
    effective = scope.global_set(catalog)
    belongs = wanted(catalog, kind, effective)

    for art in belongs:
        link = scope.link_path(art, scope.GLOBAL, home, None)
        if not art.source.exists():
            # force=true in the old Ansible never validated its target, so a registry
            # typo became a dangling link that resolved nowhere and still reported
            # success. An assert per artifact is what that block needed instead.
            result.missing.append((art, link))
            continue
        if link.is_symlink():
            # The exact target, not merely the right store: a link with the right name
            # pointing at the wrong source loads the wrong artifact under a name that
            # looks correct, and only re-pointing it fixes that.
            bucket = result.current if scope.links_to(link, art.source) else result.relink
            bucket.append((art, link))
            continue
        if link.exists():
            # Hand-authored content wearing the right name. remove.py refuses the same
            # case for the same reason: this tool owns its own symlinks and nothing else.
            result.blocked.append((art, link))
            continue
        result.link.append((art, link))

    for one in (kind,) if kind else (cat.SKILL, cat.AGENT, cat.PLUGIN):
        result.prune.extend(stale(catalog, one, home, claude, effective))

    # Every link in the selected scope is stale and nothing is left to replace them,
    # which is what a registry with its `global` tags lost looks like. Indistinguishable
    # from success until Claude Code loads no skills at all, so it refuses.
    if result.prune and not belongs:
        subject = f"no {kind}" if kind else "nothing"
        result.refusal = (
            errors.DRIFT,
            f"{subject} belongs in ~/.claude, so pruning would delete every link "
            f"there ({len(result.prune)} of them).\n"
            f"  The registries have lost their 'global' tags or changed shape. Fix "
            f"that first; nothing was touched.",
        )
    return result


def apply(plan_):
    """Make the plan true. Returns [(outcome, artifact-or-name, path)] in report order."""
    done = []
    for art, link in plan_.relink:
        link.unlink()
        link.symlink_to(art.source)
        done.append((RELINKED, art.name, link))
    for art, link in plan_.link:
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(art.source)
        done.append((LINKED, art.name, link))
    for _, name, path in plan_.prune:
        path.unlink()
        done.append((PRUNED, name, path))
    return done


def _report(plan_, dry_run):
    """One line per change, then the asides, then one summary.

    Silent about what is already correct, which on a steady-state run is everything.
    Eighteen lines saying nothing happened is what teaches a reader to skip the
    report, and this runs on every `make run-role ROLE=ai`.
    """
    linked = "Would link" if dry_run else "Linked"
    unlinked = "Would unlink" if dry_run else "Unlinked"
    for art, link in plan_.link:
        ui.ok(f"{linked} '{art.name}' ({art.type}) into {ui.path(link.parent)}")
    for art, link in plan_.relink:
        ui.ok(f"{linked} '{art.name}' ({art.type}) again; it pointed somewhere else")
    for _, name, path in plan_.prune:
        ui.ok(f"{unlinked} '{name}' from {ui.path(path.parent)}; it no longer belongs here")

    for art, link in plan_.blocked:
        kind_of_thing = "file" if art.type == cat.AGENT else "directory"
        ui.warn(
            f"{ui.path(link)} is a real {kind_of_thing}, not a link claude-kit made. "
            f"Leaving it alone."
        )
    for art, _ in plan_.missing:
        ui.warn(
            f"'{art.name}' ({art.type}) belongs in ~/.claude but is missing from the "
            f"repo at {ui.path(art.source)}."
        )
    if plan_.missing:
        ui.note("Fix the registry name, or run: claude-kit update --type skill")


def _summary(plan_, dry_run):
    """The closing line, and the one the `ai` role reads to decide `changed`.

    Both branches keep the same shape, so `, 0 changes` is a stable thing for the role
    to match on. Its `changed_when` is pinned to this wording by test_provision.py.
    """
    if plan_.changes == 0:
        return ui.done(f"{plan_.belongs} global artifacts, 0 changes")
    tail = ", dry run" if dry_run else ""
    return ui.done(
        f"{plan_.belongs} global artifacts, {plan_.changes} changes "
        f"({len(plan_.link)} linked, {len(plan_.relink)} relinked, "
        f"{len(plan_.prune)} pruned{tail})"
    )


def run(args):
    claude = paths.claude_dir()
    home = paths.home()
    catalog = cat.build_catalog(claude)
    dry_run = args.dry_run

    scoped = f" {args.type}s" if args.type else " artifacts"
    verb = "Checking" if dry_run else "Syncing"
    ui.title(f"🔄 {verb} global{scoped} in {ui.path(home / '.claude')}")

    plan_ = plan(catalog, args.type, home, claude)
    if plan_.refusal is not None:
        return fail(*plan_.refusal)

    if not dry_run:
        apply(plan_)
    _report(plan_, dry_run)
    _summary(plan_, dry_run)

    # A blocked path is a genuine conflict someone has to resolve; a missing source is
    # a registry that names something this repo does not have. Both leave ~/.claude
    # short of what it should hold, so neither is allowed to exit 0. Ordered so the
    # more actionable of the two wins when both happen.
    if plan_.missing:
        return errors.NOT_FOUND
    if plan_.blocked:
        return errors.USAGE
    return errors.OK
