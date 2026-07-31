"""The provenance file: <project>/.claude/claude-kit.json.

Covers C22 to C25 and D16 to D17 at the read/write layer. The cascade rules that
consume it live in test_remove.py.
"""

import json

from claude_kit import catalog as cat
from claude_kit import state

SKILL = cat.SKILL
AGENT = cat.AGENT
PLUGIN = cat.PLUGIN


def read_raw(project):
    return json.loads(state.path_for(project).read_text())


# --- reason encoding --------------------------------------------------------


def test_direct_and_dependency_are_distinguishable():
    assert state.is_direct(state.DIRECT)
    assert not state.is_direct(state.dep_of("parent"))
    assert state.parent_of(state.dep_of("parent")) == "parent"
    assert state.parent_of(state.DIRECT) is None


def test_an_unrecognised_reason_counts_as_direct():
    """A wrong keep costs one stale link; a wrong delete loses a deliberate choice.

    So anything not explicitly recorded as a dependency must read as deliberate.
    """
    assert state.is_direct("something-we-never-wrote")
    assert state.is_direct("")


# --- C25: file creation and preservation ------------------------------------


def test_c25_no_file_reads_as_empty(tmp_path):
    project = tmp_path / "project"
    (project / ".claude").mkdir(parents=True)
    assert state.read(project) == {}


def test_c25_read_with_no_project_is_empty(tmp_path):
    assert state.read(None) == {}


def test_c25_the_file_is_created_on_first_record(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    state.record(project, {(SKILL, "coderabbit"): state.DIRECT})
    assert state.path_for(project).is_file()
    assert read_raw(project) == {"installed": {"skills": {"coderabbit": "direct"}}}


def test_c25_unrelated_entries_survive_a_write(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    state.record(project, {(SKILL, "first"): state.DIRECT})
    state.record(project, {(SKILL, "second"): state.dep_of("first")})
    assert state.read(project) == {
        (SKILL, "first"): state.DIRECT,
        (SKILL, "second"): state.dep_of("first"),
    }


def test_records_nest_by_collection(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    state.record(
        project,
        {
            (SKILL, "s"): state.DIRECT,
            (AGENT, "a"): state.DIRECT,
            (PLUGIN, "p"): state.DIRECT,
        },
    )
    assert read_raw(project)["installed"] == {
        "skills": {"s": "direct"},
        "agents": {"a": "direct"},
        "plugins": {"p": "direct"},
    }


def test_records_round_trip_keyed_by_type(tmp_path):
    """One name used by two types must not collapse into a single record."""
    project = tmp_path / "project"
    project.mkdir()
    state.record(project, {(SKILL, "review"): state.DIRECT, (AGENT, "review"): state.dep_of("x")})
    assert state.read(project) == {
        (SKILL, "review"): state.DIRECT,
        (AGENT, "review"): state.dep_of("x"),
    }


# --- C23: the dependency-to-direct upgrade ----------------------------------


def test_c23_a_dependency_is_upgraded_to_direct(tmp_path):
    """History A: naming something already present as a dependency is how you say
    you want it in its own right, even though no new symlink is made."""
    project = tmp_path / "project"
    project.mkdir()
    state.record(project, {(SKILL, "tdd"): state.dep_of("sdd")})
    state.record(project, {(SKILL, "tdd"): state.DIRECT})
    assert state.read(project)[(SKILL, "tdd")] == state.DIRECT


def test_c23_direct_is_never_downgraded_to_a_dependency(tmp_path):
    """History A again, in the other order: adding sdd after tdd must not demote
    tdd, or removing sdd would delete a skill the user chose."""
    project = tmp_path / "project"
    project.mkdir()
    state.record(project, {(SKILL, "tdd"): state.DIRECT})
    state.record(project, {(SKILL, "tdd"): state.dep_of("sdd")})
    assert state.read(project)[(SKILL, "tdd")] == state.DIRECT


# --- D16, D17: forgetting ---------------------------------------------------


def test_d16_forget_drops_only_the_named_keys(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    state.record(project, {(SKILL, "a"): state.DIRECT, (SKILL, "b"): state.DIRECT})
    state.forget(project, [(SKILL, "a")])
    assert state.read(project) == {(SKILL, "b"): state.DIRECT}


def test_d17_the_file_is_deleted_when_nothing_is_left(tmp_path):
    """An empty object on disk is indistinguishable from a stale one to a reader."""
    project = tmp_path / "project"
    project.mkdir()
    state.record(project, {(SKILL, "only"): state.DIRECT})
    assert state.path_for(project).is_file()
    state.forget(project, [(SKILL, "only")])
    assert not state.path_for(project).exists()


def test_forgetting_an_absent_key_is_harmless(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    state.record(project, {(SKILL, "a"): state.DIRECT})
    state.forget(project, [(SKILL, "never-there")])
    assert state.read(project) == {(SKILL, "a"): state.DIRECT}


# --- corruption tolerance ---------------------------------------------------


def test_malformed_json_reads_as_empty_rather_than_raising(tmp_path):
    """Provenance is an optimisation over conservative behaviour, and D14 already
    requires that a missing record never causes a deletion. Crashing on a corrupt
    file would make `remove` unusable instead of merely cautious."""
    project = tmp_path / "project"
    (project / ".claude").mkdir(parents=True)
    state.path_for(project).write_text("{not json")
    assert state.read(project) == {}


def test_an_unknown_collection_is_ignored(tmp_path):
    project = tmp_path / "project"
    (project / ".claude").mkdir(parents=True)
    state.path_for(project).write_text(
        json.dumps({"installed": {"widgets": {"x": "direct"}, "skills": {"y": "direct"}}})
    )
    assert state.read(project) == {(SKILL, "y"): state.DIRECT}


def test_a_non_dict_collection_is_ignored(tmp_path):
    project = tmp_path / "project"
    (project / ".claude").mkdir(parents=True)
    state.path_for(project).write_text(json.dumps({"installed": {"skills": ["a", "b"]}}))
    assert state.read(project) == {}


def test_a_non_dict_document_is_ignored(tmp_path):
    """The companion to the case above, one level further out.

    A file holding `[]` or `null` is valid JSON, so the except in read() never saw it
    and .get() raised instead. That took `list`, `doctor` and `remove` down with a
    traceback, and doctor is precisely the command reached for when something is wrong.
    """
    project = tmp_path / "project"
    (project / ".claude").mkdir(parents=True)
    for body in ("[]", "null", '"a string"', "42", "[{\"installed\": {}}]"):
        state.path_for(project).write_text(body)
        assert state.read(project) == {}, f"{body} should read as no provenance"


def test_the_file_ends_with_a_newline(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    state.record(project, {(SKILL, "a"): state.DIRECT})
    assert state.path_for(project).read_text().endswith("}\n")
