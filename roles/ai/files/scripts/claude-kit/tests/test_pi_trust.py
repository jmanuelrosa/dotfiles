"""Group Q: pi's trust store, whose every derivation differs from Claude Code's.

The value of this module is entirely in the differences. A reader who assumes the two
stores answer the same question gets the wrong answer three separate ways, and none of
them is loud: the report simply describes a workspace pi never consults.

Read out of the installed pi 0.84.x `dist/core/trust-manager.js`, and asserted here
against a fabricated store rather than the real one, so the tests say what pi does
rather than what this machine happens to contain.
"""

import json

import pytest

from claude_kit import pi_trust


@pytest.fixture
def store_file(tmp_path):
    return tmp_path / "trust.json"


def write_store(path, mapping):
    path.write_text(json.dumps(mapping))
    return path


# --- Q1: the key ---------------------------------------------------------------


def test_the_key_is_the_directory_itself_not_a_repo_root(tmp_path):
    """Claude Code keys on the git root; pi keys on where it was started.

    So a subdirectory of a trusted repo is a workspace pi has never been asked about,
    and computing this the Claude way would report on an entry pi never reads.
    """
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    sub = repo / "packages" / "web"
    sub.mkdir(parents=True)
    assert pi_trust.key_for(sub) == str(sub.resolve())
    assert pi_trust.key_for(sub) != pi_trust.key_for(repo)


def test_the_key_follows_symlinks(tmp_path):
    """`canonicalizePath` is realpathSync, where Claude Code's normalise deliberately
    is not. A key computed without resolving names a directory pi never looks at."""
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)
    assert pi_trust.key_for(link) == str(real.resolve())


# --- Q2: reading ---------------------------------------------------------------


def test_a_missing_store_reads_as_nothing_recorded(tmp_path):
    """The normal state of a machine where pi has not asked yet."""
    assert pi_trust.read(tmp_path / "absent.json") == {}


def test_an_unparseable_store_reads_as_nothing_recorded(store_file):
    """pi's file to complain about. A report is the least useful place to refuse."""
    store_file.write_text("{not json")
    assert pi_trust.read(store_file) == {}


def test_non_boolean_entries_are_dropped(store_file):
    """pi only treats `true` and `false` as decisions, and `findNearestTrustEntry`
    walks past anything else, so a null must not read as a refusal."""
    write_store(store_file, {"/a": True, "/b": None, "/c": "yes", "/d": False})
    assert pi_trust.read(store_file) == {"/a": True, "/d": False}


# --- Q3: the nearest entry wins ------------------------------------------------


def test_trust_is_inherited_from_an_ancestor(tmp_path):
    project = tmp_path / "x" / "y"
    project.mkdir(parents=True)
    store = {str(tmp_path.resolve()): True}
    path, decision = pi_trust.decided_by(store, project)
    assert (path, decision) == (str(tmp_path.resolve()), True)


def test_the_nearest_entry_wins_even_when_it_is_a_refusal(tmp_path):
    """The difference that bites. Claude Code's gate keeps walking past a false looking
    for a true; pi stops at the first boolean, so a refusal shadows a grant above it."""
    parent = tmp_path / "p"
    child = parent / "c"
    child.mkdir(parents=True)
    store = {str(tmp_path.resolve()): True, str(parent.resolve()): False}
    path, decision = pi_trust.decided_by(store, child)
    assert (path, decision) == (str(parent.resolve()), False)


def test_nothing_recorded_anywhere_is_distinguishable_from_a_refusal(tmp_path):
    """Three states, not two: trusted, refused, never asked. A bool cannot carry that."""
    assert pi_trust.decided_by({}, tmp_path) == (None, None)


# --- Q4: the prompt this tool causes -------------------------------------------


def test_an_agents_skills_link_is_reported_as_the_trigger(tmp_path):
    """`add` creates this, so the prompt is a consequence of running claude-kit here.
    Naming the wrong cause sends the reader looking for a directory they never made."""
    (tmp_path / ".agents" / "skills").mkdir(parents=True)
    reason = pi_trust.prompt_reason({}, tmp_path, tmp_path)
    assert reason and ".agents/skills" in reason


@pytest.mark.parametrize(
    "entry",
    ["settings.json", "extensions", "skills", "prompts", "themes", "SYSTEM.md", "APPEND_SYSTEM.md"],
)
def test_each_named_pi_entry_is_reported_as_its_own_trigger(tmp_path, entry):
    """Not ours, so it must not be described as something claude-kit did.

    pi checks these seven names by `existsSync`, so a file answers as a directory would.
    """
    (tmp_path / ".pi").mkdir()
    (tmp_path / ".pi" / entry).touch()
    reason = pi_trust.prompt_reason({}, tmp_path, tmp_path, home=tmp_path)
    assert reason and entry in reason and "claude-kit" not in reason


def test_a_pi_directory_holding_nothing_pi_gates_is_not_a_trigger(tmp_path):
    """The existence of `.pi/` is not the trigger, its contents are.

    This repo's own `.pi/` holds a `.gitkeep` so pi-review can find the guidelines, and
    reporting that as a prompt tells the reader to expect one pi never raises.
    """
    (tmp_path / ".pi").mkdir()
    (tmp_path / ".pi" / ".gitkeep").touch()
    assert pi_trust.prompt_reason({}, tmp_path, tmp_path, home=tmp_path) is None


def test_an_agents_skills_directory_above_the_project_is_still_the_trigger(tmp_path):
    """pi walks from the cwd to the filesystem root, so the project root is not the
    boundary. Checking only the project root reports silence where pi will prompt."""
    project = tmp_path / "outer" / "project"
    project.mkdir(parents=True)
    (tmp_path / "outer" / ".agents" / "skills").mkdir(parents=True)
    reason = pi_trust.prompt_reason({}, project, project, home=tmp_path)
    assert reason and str(tmp_path / "outer" / ".agents" / "skills") in reason


def test_the_users_own_agents_skills_is_not_a_trigger(tmp_path):
    """pi skips `$HOME/.agents/skills` by name: it is the user's global store, not any
    project's. Without the exclusion, every directory under $HOME reports a prompt."""
    project = tmp_path / "home" / "project"
    project.mkdir(parents=True)
    (tmp_path / "home" / ".agents" / "skills").mkdir(parents=True)
    assert pi_trust.prompt_reason({}, project, project, home=tmp_path / "home") is None
    assert pi_trust.prompt_reason({}, project, project, home=tmp_path / "elsewhere")


def test_a_decided_project_is_not_reported_as_prompting(tmp_path):
    """Trust already recorded means pi asks nothing, whatever the project holds."""
    (tmp_path / ".agents" / "skills").mkdir(parents=True)
    store = {str(tmp_path.resolve()): True}
    assert pi_trust.prompt_reason(store, tmp_path, tmp_path) is None


def test_a_project_pi_has_no_reason_to_ask_about_is_silent(tmp_path):
    assert pi_trust.prompt_reason({}, tmp_path, tmp_path) is None
    assert pi_trust.prompt_reason({}, tmp_path, None) is None


# --- Q5: the lock --------------------------------------------------------------


def test_the_lock_is_visible_so_a_stale_read_can_be_named(store_file):
    """proper-lockfile takes `<file>.lock` beside the file. Nothing here writes, so this
    only changes what the reader is told, never what they may do."""
    assert not pi_trust.locked(store_file)
    (store_file.parent / "trust.json.lock").mkdir()
    assert pi_trust.locked(store_file)


def test_the_store_path_is_pis_and_not_claudes(tmp_path):
    """Two harnesses, two files. Writing one to answer for the other is the whole
    mistake this module exists to prevent."""
    path = pi_trust.store_path(tmp_path)
    assert path == tmp_path / ".pi" / "agent" / "trust.json"
    assert ".claude" not in str(path)
