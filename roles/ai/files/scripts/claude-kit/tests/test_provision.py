"""`claude-kit sync`: converging ~/.claude.

This is the only command that deletes something nobody named, so most of what is
asserted here is what it refuses to touch: a real directory, a link pointing outside
this repo, and everything at all when the derived set comes back empty.

Three altitudes, as elsewhere. `wanted`/`stale`/`plan` take literal catalogs and a
tmp_path store, the real registries get one section of their own, and the last section
pins the `ai` role's task against the summary wording it matches on.
"""

import yaml

from claude_kit import catalog as cat
from claude_kit import errors, scope
from claude_kit.commands import provision
from dotkit.testing import REPO

AI_TASKS = REPO / "roles/ai/tasks/main.yml"
SYNC_TASK = "Converge global claude skills, agents and plugins"


# --- fixtures built by hand -------------------------------------------------


def artifact(name, kind=cat.SKILL, groups=(), deps=(), store=None):
    """One artifact, with `source` pointed into `store` when given."""
    source = None
    if store is not None:
        source = store / cat.STORE[kind] / f"{name}{cat.SUFFIX[kind]}"
    return cat.Artifact(
        name=name,
        type=kind,
        groups=tuple(groups),
        dependencies=tuple(deps),
        source=source,
    )


def catalog_of(*artifacts):
    return {(art.type, art.name): art for art in artifacts}


def make_store(tmp_path):
    """A stand-in for roles/ai/files/claude, with the three stores present."""
    root = tmp_path / "claude"
    for leaf in ("skills", "agents", "plugins"):
        (root / leaf).mkdir(parents=True)
    return root


def create(art):
    """Put an artifact on disk: a file for an agent, a directory for the other two."""
    art.source.parent.mkdir(parents=True, exist_ok=True)
    if art.type == cat.AGENT:
        art.source.write_text("---\nname: x\n---\n")
    else:
        art.source.mkdir(exist_ok=True)
    return art


def link(home, art, target):
    """Link an artifact's global path at `target`, whatever that is."""
    path = scope.link_path(art, scope.GLOBAL, home, None)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.symlink_to(target)
    return path


class Args:
    def __init__(self, kind=None, dry_run=False):
        self.type = kind
        self.dry_run = dry_run


# --- what belongs there -----------------------------------------------------


def test_wanted_takes_the_tag_from_every_type():
    """A skill, an agent and a plugin are all global by carrying the tag."""
    c = catalog_of(
        artifact("s", cat.SKILL, groups=["global"]),
        artifact("a", cat.AGENT, groups=["global"]),
        artifact("p", cat.PLUGIN, groups=["global"]),
        artifact("nope", cat.SKILL, groups=["engineering"]),
    )
    assert [art.name for art in provision.wanted(c)] == ["a", "p", "s"]


def test_wanted_includes_the_dependencies_the_tag_reaches():
    """The derived half of the set. A global skill's dependency belongs in ~/.claude
    too, or the skill loads with something it calls at runtime missing."""
    c = catalog_of(
        artifact("dispatcher", cat.SKILL, groups=["global"], deps=["helper"]),
        artifact("helper", cat.SKILL),
    )
    assert [art.name for art in provision.wanted(c)] == ["dispatcher", "helper"]


def test_wanted_narrows_to_one_type():
    c = catalog_of(
        artifact("s", cat.SKILL, groups=["global"]),
        artifact("a", cat.AGENT, groups=["global"]),
    )
    assert [art.name for art in provision.wanted(c, cat.AGENT)] == ["a"]
    assert [art.name for art in provision.wanted(c, cat.SKILL)] == ["s"]


# --- what no longer does ----------------------------------------------------


def test_stale_finds_a_link_whose_tag_is_gone(tmp_path, home):
    store = make_store(tmp_path)
    dropped = create(artifact("was-global", cat.SKILL, store=store))
    link(home, dropped, dropped.source)

    c = catalog_of(artifact("was-global", cat.SKILL, store=store))
    assert provision.stale(c, cat.SKILL, home, store) == [
        (cat.SKILL, "was-global", home / ".claude/skills/was-global")
    ]


def test_stale_ignores_a_link_pointing_outside_this_repo(tmp_path, home):
    """Only links into our own store are ours to remove. Someone else's link in
    ~/.claude/skills is someone else's business."""
    store = make_store(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    link(home, artifact("foreign", cat.SKILL, store=store), elsewhere)

    assert provision.stale(catalog_of(), cat.SKILL, home, store) == []


def test_stale_never_offers_a_real_directory(tmp_path, home):
    """state=absent on a directory is an rmtree. `installed_names` yields symlinks
    only, which is what keeps hand-authored content safe."""
    store = make_store(tmp_path)
    (home / ".claude/skills/handmade").mkdir(parents=True)

    assert provision.stale(catalog_of(), cat.SKILL, home, store) == []


def test_a_plugin_is_not_a_stale_skill(tmp_path, home):
    """Skills and plugins share .claude/skills/, so classifying by filename would
    report every installed plugin as a skill that lost its tag."""
    store = make_store(tmp_path)
    seat = create(artifact("backend", cat.PLUGIN, groups=["global"], store=store))
    link(home, seat, seat.source)

    c = catalog_of(seat)
    assert provision.stale(c, cat.SKILL, home, store) == []
    assert provision.stale(c, cat.PLUGIN, home, store) == []


# --- the plan ---------------------------------------------------------------


def test_plan_links_what_is_absent(tmp_path, home):
    store = make_store(tmp_path)
    art = create(artifact("commit", cat.SKILL, groups=["global"], store=store))

    result = provision.plan(catalog_of(art), None, home, store)
    assert [a.name for a, _ in result.link] == ["commit"]
    assert result.changes == 1
    assert result.belongs == 1


def test_plan_calls_a_correct_link_current(tmp_path, home):
    store = make_store(tmp_path)
    art = create(artifact("commit", cat.SKILL, groups=["global"], store=store))
    link(home, art, art.source)

    result = provision.plan(catalog_of(art), None, home, store)
    assert [a.name for a, _ in result.current] == ["commit"]
    assert result.changes == 0


def test_plan_relinks_a_link_pointing_at_the_wrong_source(tmp_path, home):
    """The right name over the wrong target loads the wrong artifact while looking
    correct, which is why the exact target is compared and not just the store."""
    store = make_store(tmp_path)
    art = create(artifact("commit", cat.SKILL, groups=["global"], store=store))
    other = create(artifact("research", cat.SKILL, store=store))
    link(home, art, other.source)

    result = provision.plan(catalog_of(art), None, home, store)
    assert [a.name for a, _ in result.relink] == ["commit"]
    assert result.current == []


def test_plan_is_blocked_by_a_real_directory(tmp_path, home):
    store = make_store(tmp_path)
    art = create(artifact("commit", cat.SKILL, groups=["global"], store=store))
    (home / ".claude/skills/commit").mkdir(parents=True)

    result = provision.plan(catalog_of(art), None, home, store)
    assert [a.name for a, _ in result.blocked] == ["commit"]
    assert result.link == []


def test_plan_reports_a_registered_artifact_missing_from_the_repo(tmp_path, home):
    """The old Ansible's force=true never validated its target, so a registry typo
    became a link resolving nowhere while the play reported success."""
    store = make_store(tmp_path)
    ghost = artifact("typo", cat.SKILL, groups=["global"], store=store)

    result = provision.plan(catalog_of(ghost), None, home, store)
    assert [a.name for a, _ in result.missing] == ["typo"]
    assert result.link == []
    assert not (home / ".claude/skills/typo").exists()


def test_plan_narrows_both_halves_to_one_type(tmp_path, home):
    """A --type agent run must not read every global skill as stale. The prune scan
    has to narrow with the wanted set, not against it."""
    store = make_store(tmp_path)
    skill = create(artifact("commit", cat.SKILL, groups=["global"], store=store))
    agent = create(artifact("architect", cat.AGENT, groups=["global"], store=store))
    link(home, skill, skill.source)

    result = provision.plan(catalog_of(skill, agent), cat.AGENT, home, store)
    assert [a.name for a, _ in result.link] == ["architect"]
    assert result.prune == []


# --- the one thing it refuses outright --------------------------------------


def test_plan_refuses_to_prune_everything_when_the_set_is_empty(tmp_path, home):
    """A registry that loses its `global` tags derives an empty set, and an empty set
    makes every existing link stale. Pruning to zero looks exactly like working."""
    store = make_store(tmp_path)
    orphan = create(artifact("commit", cat.SKILL, store=store))
    path = link(home, orphan, orphan.source)

    result = provision.plan(catalog_of(orphan), None, home, store)
    assert result.refusal is not None
    assert result.refusal[0] == errors.DRIFT
    assert path.is_symlink(), "plan() must not touch anything"


def test_an_empty_set_with_nothing_to_prune_is_not_a_refusal(tmp_path, home):
    """The guard is about deleting everything, not about the set being small. A fresh
    machine with no global artifacts yet has nothing to lose."""
    store = make_store(tmp_path)

    result = provision.plan(catalog_of(), None, home, store)
    assert result.refusal is None
    assert result.changes == 0


def test_run_touches_nothing_when_it_refuses(tmp_path, home, monkeypatch, capsys):
    """The refusal has to reach the exit code, not just the plan."""
    store = make_store(tmp_path)
    orphan = create(artifact("commit", cat.SKILL, store=store))
    path = link(home, orphan, orphan.source)
    monkeypatch.setattr(provision.paths, "claude_dir", lambda root=None: store)
    monkeypatch.setattr(provision.cat, "build_catalog", lambda claude: catalog_of(orphan))

    assert provision.run(Args()) == errors.DRIFT
    assert path.is_symlink()
    assert "global" in capsys.readouterr().err


# --- applying it ------------------------------------------------------------


def test_apply_then_replan_is_idempotent(tmp_path, home):
    """The property the `ai` role depends on: re-running reports no changes."""
    store = make_store(tmp_path)
    arts = [
        create(artifact("commit", cat.SKILL, groups=["global"], store=store)),
        create(artifact("architect", cat.AGENT, groups=["global"], store=store)),
        create(artifact("seat", cat.PLUGIN, groups=["global"], store=store)),
    ]
    c = catalog_of(*arts)

    provision.apply(provision.plan(c, None, home, store))
    again = provision.plan(c, None, home, store)
    assert again.changes == 0
    assert again.belongs == 3
    for art in arts:
        path = scope.link_path(art, scope.GLOBAL, home, None)
        assert path.is_symlink() and path.resolve() == art.source.resolve()


def test_apply_prunes_and_relinks_without_disturbing_the_rest(tmp_path, home):
    store = make_store(tmp_path)
    keep = create(artifact("commit", cat.SKILL, groups=["global"], store=store))
    dropped = create(artifact("prisma-expert", cat.SKILL, store=store))
    other = create(artifact("research", cat.SKILL, store=store))
    wrong = create(artifact("pr", cat.SKILL, groups=["global"], store=store))

    link(home, keep, keep.source)
    stale_link = link(home, dropped, dropped.source)
    link(home, wrong, other.source)
    foreign = link(home, artifact("theirs", cat.SKILL, store=store), tmp_path / "elsewhere")
    (home / ".claude/skills/handmade").mkdir(parents=True)

    c = catalog_of(keep, dropped, other, wrong)
    done = provision.apply(provision.plan(c, None, home, store))

    assert sorted((state, name) for state, name, _ in done) == [
        (provision.PRUNED, "prisma-expert"),
        (provision.RELINKED, "pr"),
    ]
    assert not stale_link.exists()
    assert scope.link_path(wrong, scope.GLOBAL, home, None).resolve() == wrong.source.resolve()
    assert foreign.is_symlink(), "a link outside our store is not ours to remove"
    assert (home / ".claude/skills/handmade").is_dir()


def test_a_dry_run_writes_nothing_but_reports_the_same_plan(tmp_path, home, monkeypatch, capsys):
    store = make_store(tmp_path)
    art = create(artifact("commit", cat.SKILL, groups=["global"], store=store))
    monkeypatch.setattr(provision.paths, "claude_dir", lambda root=None: store)
    monkeypatch.setattr(provision.cat, "build_catalog", lambda claude: catalog_of(art))

    assert provision.run(Args(dry_run=True)) == errors.OK
    out = capsys.readouterr().out
    assert "Would link 'commit'" in out
    assert "dry run" in out
    assert not scope.link_path(art, scope.GLOBAL, home, None).exists()


def test_a_missing_source_is_not_a_silent_success(tmp_path, home, monkeypatch):
    store = make_store(tmp_path)
    ghost = artifact("typo", cat.SKILL, groups=["global"], store=store)
    monkeypatch.setattr(provision.paths, "claude_dir", lambda root=None: store)
    monkeypatch.setattr(provision.cat, "build_catalog", lambda claude: catalog_of(ghost))

    assert provision.run(Args()) == errors.NOT_FOUND


def test_a_blocked_path_is_not_a_silent_success(tmp_path, home, monkeypatch):
    store = make_store(tmp_path)
    art = create(artifact("commit", cat.SKILL, groups=["global"], store=store))
    (home / ".claude/skills/commit").mkdir(parents=True)
    monkeypatch.setattr(provision.paths, "claude_dir", lambda root=None: store)
    monkeypatch.setattr(provision.cat, "build_catalog", lambda claude: catalog_of(art))

    assert provision.run(Args()) == errors.USAGE


# --- against the real registries --------------------------------------------


def test_every_global_artifact_exists_on_disk(catalog):
    """What the removed Ansible asserted, and the reason it asserted it: a name the
    registry gets wrong is a link that resolves nowhere."""
    missing = [
        f"{art.type} {art.name} -> {art.source}"
        for art in provision.wanted(catalog)
        if not art.source.exists()
    ]
    assert missing == []


def test_the_real_global_set_is_the_derived_one(catalog, effective):
    """`wanted` must not become a second derivation. Skills come from
    scope.global_set; the other two types are global exactly when tagged."""
    by_type = {}
    for art in provision.wanted(catalog):
        by_type.setdefault(art.type, set()).add(art.name)

    assert by_type[cat.SKILL] == effective
    for kind in (cat.AGENT, cat.PLUGIN):
        tagged = {a.name for a in catalog.values() if a.type == kind and a.tagged_global}
        assert by_type.get(kind, set()) == tagged


def test_a_real_run_converges_and_then_reports_no_changes(kit):
    """End to end through the shim, against the real registries and a throwaway HOME."""
    first = kit("sync")
    assert first.returncode == errors.OK, first.stderr
    assert ", 0 changes" not in first.stdout

    second = kit("sync")
    assert second.returncode == errors.OK, second.stderr
    assert ", 0 changes" in second.stdout

    skills = kit.home / ".claude/skills"
    agents = kit.home / ".claude/agents"
    assert (skills / "grill-me").is_symlink()
    # Derived rather than tagged: it arrives because grill-me declares it.
    assert (skills / "grilling").is_symlink()
    assert (agents / "architect.md").is_symlink()


# --- the ai role's end of the contract --------------------------------------


def sync_task():
    tasks = yaml.safe_load(AI_TASKS.read_text())
    matching = [t for t in tasks if t.get("name") == SYNC_TASK]
    assert len(matching) == 1, f"expected exactly one '{SYNC_TASK}' task"
    return matching[0]


def test_the_role_provisions_the_global_directories():
    """Nothing filled ~/.claude/skills between commit 0624d1c and this command, and
    only this task fills it now. Losing it again would be silent: the play succeeds
    and Claude Code simply loads no global skills."""
    task = sync_task()
    assert "claude-kit/claude-kit sync" in task["ansible.builtin.command"]["cmd"]


def test_the_role_reads_changed_off_the_summary_wording(capsys):
    """changed_when matches a string this module prints, so the two are one contract.

    Both directions are asserted, because each fails a different way: lose the marker
    from the quiet run and every play reports changed, and let it appear in a run that
    did something and a prune goes unreported.
    """
    marker = ", 0 changes"
    assert marker in sync_task()["changed_when"]

    provision._summary(provision.Plan(), dry_run=False)
    assert marker in capsys.readouterr().out

    busy = provision.Plan(prune=[(cat.SKILL, "gone", None)])
    provision._summary(busy, dry_run=False)
    assert marker not in capsys.readouterr().out


def test_the_role_dry_runs_under_check_mode():
    """A bare `command` task would sync for real during `make check`, and skipping it
    would make `make check` silent about the one task that deletes things."""
    task = sync_task()
    assert "--dry-run" in task["ansible.builtin.command"]["cmd"]
    assert "ansible_check_mode" in task["ansible.builtin.command"]["cmd"]
    assert task["check_mode"] is False


def test_the_role_pins_both_environmental_inputs():
    """HOME and DOTFILES_DIR are the tool's only environmental inputs. Inheriting
    DOTFILES_DIR from the caller would let the task provision from another checkout."""
    environment = sync_task()["environment"]
    assert "HOME" in environment
    assert "DOTFILES_DIR" in environment
