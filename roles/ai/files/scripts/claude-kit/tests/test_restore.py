"""Group J: `restore`, installing what claude-kit.json already records.

The mirror of Group H. Adoption's hard question is what to record; restoration's is
what *not* to install, because a `dep-of:` row handed to `add` would come back
recorded `direct` and the cascade the manifest exists to preserve would be gone.

So J1 to J3 are pure selection and reporting over literal dicts, and J5 is the claim
none of them can make: wipe a project's links, restore, and the manifest has to come
back byte for byte.
"""

import json

import pytest

from claude_kit import catalog as cat
from claude_kit import errors, state
from claude_kit.commands import restore

SKILL = cat.SKILL
AGENT = cat.AGENT
PLUGIN = cat.PLUGIN


def step(name, kind=SKILL, required_by=None):
    from claude_kit.commands.add import Step
    from claude_kit import scope

    return Step(cat.Artifact(name=name, type=kind), scope.PROJECT, required_by)


def plan_with(*steps, refused=False):
    from claude_kit.commands.add import Plan

    plan_ = Plan(name=steps[0].artifact.name if steps else "x")
    plan_.steps.extend(steps)
    if refused:
        plan_.code = errors.NOT_FOUND
    return plan_


# --- J1: only the direct entries are installed ------------------------------


def test_j1_a_dependency_row_is_never_installed_directly():
    """The rule the whole command turns on. `add` re-resolves every closure and
    rewrites the dep-of records itself, so naming one here would record it direct."""
    provenance = {
        (SKILL, "parent"): state.DIRECT,
        (SKILL, "dep"): state.dep_of("parent"),
    }
    missing, present = restore.wanted(provenance, set())
    assert missing == [(SKILL, "parent")]
    assert present == []


def test_j1_an_already_linked_entry_is_set_aside_rather_than_refused():
    """A manifest is a set to converge on, as a group is, so the steady state is not
    a failure. add would refuse each of these with ALREADY."""
    provenance = {(SKILL, "a"): state.DIRECT, (SKILL, "b"): state.DIRECT}
    missing, present = restore.wanted(provenance, {(SKILL, "a")})
    assert missing == [(SKILL, "b")]
    assert present == [(SKILL, "a")]


def test_j1_type_narrows_the_selection():
    provenance = {
        (SKILL, "a"): state.DIRECT,
        (AGENT, "b"): state.DIRECT,
        (PLUGIN, "c"): state.DIRECT,
    }
    missing, _ = restore.wanted(provenance, set(), AGENT)
    assert missing == [(AGENT, "b")]


def test_j1_an_unrecognised_reason_counts_as_direct():
    """state.is_direct errs toward deliberate, and restore inherits that: a row we
    cannot read is one the user probably asked for."""
    missing, _ = restore.wanted({(SKILL, "a"): "hand-edited"}, set())
    assert missing == [(SKILL, "a")]


# --- J2: what is still unlinked afterwards ----------------------------------


def test_j2_a_stale_dependency_row_is_reported_not_forgotten():
    """Its parent stopped declaring it, so no closure will ever bring it back.
    Dropping the record is remove's business; restore only says so."""
    provenance = {
        (SKILL, "parent"): state.DIRECT,
        (SKILL, "orphan"): state.dep_of("parent"),
    }
    assert restore.unlinked(provenance, {(SKILL, "parent")}) == [(SKILL, "orphan")]


def test_j2_nothing_is_reported_once_every_row_is_linked():
    provenance = {(SKILL, "a"): state.DIRECT, (SKILL, "b"): state.dep_of("a")}
    assert restore.unlinked(provenance, {(SKILL, "a"), (SKILL, "b")}) == []


def test_j2_type_narrows_the_report():
    provenance = {(SKILL, "a"): state.DIRECT, (AGENT, "b"): state.DIRECT}
    assert restore.unlinked(provenance, set(), AGENT) == [(AGENT, "b")]


# --- J3: the reports and their exit codes -----------------------------------


def collect(fn, *args, **kwargs):
    lines = []
    code = fn(*args, **kwargs, emit=lines.append)
    return code, "\n".join(lines)


def test_j3_a_dry_run_shows_the_closure_rather_than_the_manifest(tmp_path):
    """One recorded entry routinely brings four skills with it. A preview reading
    `1 of 1` beside a real run printing four ✓ lines is one nobody would trust."""
    plans = [plan_with(step("dep", required_by="parent"), step("parent"))]
    code, text = collect(restore.preview, plans, [], SKILL, tmp_path)
    assert code == errors.OK
    assert "skill 'dep'  (required by parent)" in text
    assert "2 link(s) for 1 recorded skill(s)." in text
    assert "Nothing written (--dry-run)." in text


def test_j3_a_shared_dependency_is_listed_once():
    plans = [
        plan_with(step("dep", required_by="a"), step("a")),
        plan_with(step("dep", required_by="b"), step("b")),
    ]
    assert [key for key, _ in restore.planned_links(plans)] == [
        (SKILL, "dep"),
        (SKILL, "a"),
        (SKILL, "b"),
    ]


def test_j3_an_entry_planned_both_ways_keeps_the_bare_label():
    """`dep` is recorded direct *and* pulled in by `parent`. Annotating it
    `(required by parent)` would describe the wrong half of the truth."""
    plans = [plan_with(step("dep", required_by="parent"), step("parent")), plan_with(step("dep"))]
    assert dict(restore.planned_links(plans))[(SKILL, "dep")] is None


def test_j3_the_summary_counts_rows_and_links_separately():
    code, text = collect(restore.summarise, 4, 1, 1, [], [], SKILL, errors.OK)
    assert code == errors.OK
    assert "Restored 1 of 1 recorded skill(s), 4 link(s)" in text


def test_j3_a_run_with_nothing_left_over_says_nothing_about_drift():
    _, text = collect(restore.summarise, 1, 1, 1, [], [], SKILL, errors.OK)
    assert "still not linked" not in text
    assert "4 link(s)" not in text, "the link count is only worth printing when it differs"


def test_j3_a_leftover_row_exits_drift_and_names_itself():
    code, text = collect(
        restore.summarise, 1, 1, 1, [], [(SKILL, "orphan")], SKILL, errors.OK
    )
    assert code == errors.DRIFT
    assert "skill 'orphan'" in text
    assert "Nothing was forgotten" in text


def test_j3_a_refusals_own_code_wins_over_drift():
    """The per-artifact message add already printed says more than DRIFT does."""
    code, _ = collect(
        restore.summarise, 0, 0, 1, [], [(SKILL, "gone")], SKILL, errors.NOT_FOUND
    )
    assert code == errors.NOT_FOUND


def test_j3_a_failure_is_counted_in_the_summary():
    _, text = collect(restore.summarise, 0, 0, 2, [], [], SKILL, errors.NOT_FOUND)
    assert "Restored 0 of 2 recorded skill(s) (2 failed)" in text


# --- J4: refusals -----------------------------------------------------------


def test_j4_no_manifest_points_at_adopt(kit, project):
    result = kit("restore", cwd=project)
    assert result.returncode == errors.NOT_FOUND
    assert "claude-kit adopt" in result.stderr


@pytest.mark.parametrize("body", ["{not json", "[]", "null"])
def test_j4_an_unparseable_manifest_is_drift_not_an_empty_restore(kit, project, body):
    """state.read would call this "nothing recorded" and exit 0 having done nothing."""
    (project / ".claude").mkdir()
    state.path_for(project).write_text(body)
    result = kit("restore", cwd=project)
    assert result.returncode == errors.DRIFT
    assert "does not parse" in result.stderr


def test_j4_restore_in_home_refuses(kit):
    result = kit("restore")
    assert result.returncode == errors.NO_PROJECT
    assert "claude-kit sync" in result.stderr


# --- J5: end to end ---------------------------------------------------------


def wipe(project):
    """A fresh clone: the manifest is committed, the symlinks never are."""
    for leaf in ("skills", "agents"):
        directory = project / ".claude" / leaf
        for entry in directory.iterdir() if directory.is_dir() else []:
            entry.unlink()


def test_j5_a_wiped_project_comes_back_with_its_manifest_byte_identical(kit, project):
    """The whole command in one assertion.

    Byte-identical is the strong form: it says every dep-of row came back a dep-of
    row rather than being promoted to direct, which is what installing the whole
    manifest instead of its direct half would have produced.
    """
    assert kit("add", "spec-driven-development", "--type", "skill", cwd=project).returncode == 0
    before = state.path_for(project).read_text()
    assert json.loads(before)["installed"]["skills"]["context-engineering"].startswith("dep-of:")

    wipe(project)
    result = kit("restore", cwd=project)
    assert result.returncode == errors.OK, result.stderr
    assert (project / ".claude" / "skills" / "context-engineering").is_symlink()
    assert state.path_for(project).read_text() == before


def test_j5_a_dry_run_touches_nothing(kit, project):
    assert kit("add", "coderabbit", "--type", "skill", cwd=project).returncode == 0
    wipe(project)

    result = kit("restore", "--dry-run", cwd=project)
    assert result.returncode == errors.OK
    assert "skill 'coderabbit'" in result.stdout
    assert not (project / ".claude" / "skills" / "coderabbit").exists()


def test_j5_restore_is_idempotent(kit, project):
    assert kit("add", "coderabbit", "--type", "skill", cwd=project).returncode == 0

    result = kit("restore", cwd=project)
    assert result.returncode == errors.OK
    assert "Nothing to restore" in result.stdout


def test_j5_one_dropped_row_does_not_strand_the_rest(kit, project):
    """A registry entry can disappear upstream while the manifest still names it."""
    assert kit("add", "coderabbit", "--type", "skill", cwd=project).returncode == 0
    wipe(project)
    records = state.read(project)
    records[(SKILL, "gone-upstream")] = state.DIRECT
    state.write(project, records)

    result = kit("restore", cwd=project)
    assert result.returncode == errors.NOT_FOUND
    assert "'gone-upstream' is not a known skill" in result.stderr
    assert (project / ".claude" / "skills" / "coderabbit").is_symlink(), result.stdout


def test_j5_restore_silences_the_stale_provenance_problems(kit, project):
    """Closes the loop with doctor, as adoption does for its own finding: G12 now
    names this command, so running it has to make the problems go away."""
    assert kit("add", "spec-driven-development", "--type", "skill", cwd=project).returncode == 0
    wipe(project)
    assert "stale-provenance" in kit("doctor", cwd=project).stdout

    assert kit("restore", cwd=project).returncode == errors.OK
    after = kit("doctor", cwd=project)
    assert "stale-provenance" not in after.stdout
    assert after.returncode == errors.OK


def test_j5_type_narrows_an_end_to_end_run(kit, project):
    """A plugin and a skill share the .claude/skills/ leaf, so this also checks that
    the narrowing reads the store a link resolves into rather than its filename."""
    assert kit("add", "coderabbit", "--type", "skill", cwd=project).returncode == 0
    assert kit("add", "backend", "--type", "plugin", cwd=project).returncode == 0
    wipe(project)

    result = kit("restore", "--type", "plugin", cwd=project)
    assert result.returncode == errors.OK, result.stderr
    assert (project / ".claude" / "skills" / "backend").is_symlink()
    assert not (project / ".claude" / "skills" / "coderabbit").exists()
