"""Workspace trust: the key derivation, the inheritance walk, and the write.

Two of these are not claude-kit's rules to choose, and that is what most of this file
guards. The key Claude Code stores trust under, and the chain it walks to decide the
answer, are read out of the 2.1.220 binary; a derivation that is merely reasonable is a
derivation that reports on a directory Claude Code never looks at. So the cases below are
the shapes that binary distinguishes: a plain directory, a repo root, a subdirectory, a
linked worktree, and a worktree whose layout does not check out.

The write tests are all about *not* damaging a 76 KB file that belongs to somebody else:
the other fields of the entry, the other entries, the file's mode, and its exact byte
formatting.
"""

import json
import os
import stat

import pytest

from dotkit.testing import CLAUDE

from claude_kit import checks, errors, workspace as ws
from claude_kit.commands import trust

TRUSTED = ws.TRUSTED


def config_with(**entries):
    """A config holding one entry per path, each with just the flag."""
    return {"projects": {path: {TRUSTED: value} for path, value in entries.items()}}


# --- the key: what Claude Code would store this directory's trust under -------


def test_a_plain_directory_is_its_own_key(tmp_path):
    plain = tmp_path / "not-a-repo"
    plain.mkdir()
    assert ws.key_for(plain) == str(plain)
    assert ws.repo_dir(plain) is None


def test_a_repo_root_is_its_own_key(tmp_path):
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    assert ws.key_for(repo) == str(repo)


def test_a_subdirectory_resolves_up_to_the_repo_root(tmp_path):
    """The gate does not walk up from a subdirectory to find the *plugin*, but the key
    it stores trust under is the repo root regardless of how deep you are standing."""
    repo = tmp_path / "repo"
    deep = repo / "src" / "nested"
    (repo / ".git").mkdir(parents=True)
    deep.mkdir(parents=True)
    assert ws.key_for(deep) == str(repo)


def make_worktree(tmp_path, *, commondir=None, gitdir_shape=True):
    """A linked worktree the way git lays one out.

    `.git` is a file pointing at <main>/.git/worktrees/<name>, which holds a `commondir`
    pointing back at the main .git. Both knobs exist so the tests can break one link at a
    time and check the fallback.
    """
    main = tmp_path / "main"
    admin = main / ".git" / "worktrees" / "wt"
    admin.mkdir(parents=True)
    worktree = tmp_path / "wt"
    worktree.mkdir()
    (worktree / ".git").write_text(f"gitdir: {admin}\n")
    (admin / "commondir").write_text(("../.." if commondir is None else commondir) + "\n")
    if not gitdir_shape:
        stray = tmp_path / "stray"
        stray.mkdir()
        (worktree / ".git").write_text(f"gitdir: {stray}\n")
    return main, worktree


def test_a_linked_worktrees_key_is_the_main_checkout(tmp_path):
    """The finding this whole command exists for. A worktree gets no entry of its own, so
    a tool that reported on the worktree path would report on nothing at all."""
    main, worktree = make_worktree(tmp_path)
    assert ws.repo_dir(worktree) == str(worktree)
    assert ws.key_for(worktree) == str(main)


def test_a_subdirectory_of_a_worktree_also_keys_on_the_main_checkout(tmp_path):
    main, worktree = make_worktree(tmp_path)
    deep = worktree / "src"
    deep.mkdir()
    assert ws.key_for(deep) == str(main)


def test_a_worktree_whose_commondir_is_wrong_falls_back_to_itself(tmp_path):
    """Every consistency check the binary makes returns the worktree unchanged. Guessing
    past a broken layout would silently report on, and write to, some other directory."""
    _, worktree = make_worktree(tmp_path, commondir="../../../elsewhere")
    assert ws.key_for(worktree) == str(worktree)


def test_a_gitdir_pointing_outside_a_worktrees_directory_falls_back(tmp_path):
    _, worktree = make_worktree(tmp_path, gitdir_shape=False)
    assert ws.key_for(worktree) == str(worktree)


def test_a_git_file_that_is_not_a_pointer_falls_back(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").write_text("this is not a gitdir pointer\n")
    assert ws.key_for(repo) == str(repo)


def test_the_key_does_not_resolve_symlinks(tmp_path):
    """node's path.resolve does not realpath, so neither may this. A key derived through
    the real path names a directory whose entry Claude Code never reads."""
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)
    assert ws.key_for(link / ".") == str(link)


# --- inheritance: trust is granted by an ancestor, not only by the key --------


def test_a_stored_flag_on_the_key_grants_trust():
    config = config_with(**{"/a/b": True})
    assert ws.granted_by(config, "/a/b", "/a/b") == "/a/b"


def test_an_ancestor_grants_trust_to_everything_beneath_it():
    """The fact that makes a false flag misleading: six of this machine's eight entries
    read false and every one of them is trusted, because $HOME's entry is true."""
    config = config_with(**{"/a": True, "/a/b/c": False})
    assert ws.granted_by(config, "/a/b/c", "/a/b/c") == "/a"


def test_the_key_wins_over_an_ancestor():
    """The gate probes the key first, so the reported grantor is the one it stops at."""
    config = config_with(**{"/a": True, "/a/b": True})
    assert ws.granted_by(config, "/a/b", "/a/b") == "/a/b"


def test_nothing_grants_trust_when_the_whole_chain_is_false():
    config = config_with(**{"/a": False, "/a/b": False})
    assert ws.granted_by(config, "/a/b", "/a/b") is None


def test_a_worktrees_key_and_its_cwd_are_two_different_lineages():
    """For a worktree the key sits under the main checkout while the cwd sits under its
    own parents, and the gate consults both. A walk from the key alone would miss a
    grantor above the worktree; a walk from the cwd alone would miss the key itself."""
    config = config_with(**{"/repos/main": True})
    assert ws.granted_by(config, "/repos/main", "/elsewhere/wt") == "/repos/main"

    config = config_with(**{"/elsewhere": True})
    assert ws.granted_by(config, "/repos/main", "/elsewhere/wt") == "/elsewhere"


def test_an_absent_entry_reads_as_none_not_as_false():
    """Three-valued because "never run here" and "declined the dialog" read differently
    to the person looking at the report."""
    config = config_with(**{"/a": False})
    assert ws.stored(config, "/a") is False
    assert ws.stored(config, "/b") is None


def test_a_surprising_shape_never_raises():
    """This file is not ours, so a projects map holding something unexpected has to read
    as "no trust" rather than as a traceback."""
    assert ws.stored({"projects": "nonsense"}, "/a") is None
    assert ws.stored({"projects": {"/a": "nonsense"}}, "/a") is None
    assert ws.granted_by({}, "/a", "/a") is None


def test_descendants_are_matched_at_a_segment_boundary():
    config = config_with(**{"/a/b": True, "/a/bc": True, "/a/b/c": True})
    assert ws.descendant_keys(config, "/a/b") == ["/a/b/c"]


# --- the write: one field of one key, and nothing else -----------------------


SEEDED = {
    "numStartups": 7,
    "oauthAccount": {"note": "kéep"},
    "projects": {
        "/other": {TRUSTED: False, "mcpServers": {"a": 1}, "lastCost": 0.5},
    },
}


@pytest.fixture
def seeded(tmp_path):
    path = tmp_path / ".claude.json"
    path.write_text(json.dumps(SEEDED, indent=2))
    os.chmod(path, 0o600)
    return path


def test_an_existing_entry_keeps_its_other_fields(seeded):
    config = ws.apply(ws.read(seeded), "/other", True)
    assert config["projects"]["/other"] == {
        TRUSTED: True,
        "mcpServers": {"a": 1},
        "lastCost": 0.5,
    }


def test_a_new_entry_is_shaped_like_the_one_claude_code_writes(seeded):
    config = ws.apply(ws.read(seeded), "/fresh", True)
    entry = config["projects"]["/fresh"]
    assert set(entry) == set(ws.DEFAULT_ENTRY)
    assert entry[TRUSTED] is True
    assert config["projects"]["/other"][TRUSTED] is False, "the other entry moved"


def test_the_rest_of_the_config_survives_a_write(seeded):
    ws.write(seeded, ws.apply(ws.read(seeded), "/fresh", True))
    after = json.loads(seeded.read_text())
    assert after["numStartups"] == 7
    assert after["oauthAccount"] == {"note": "kéep"}


def test_the_bytes_are_the_ones_claude_code_writes(seeded):
    """JSON.stringify(o, null, 2): two-space indent, no trailing newline, non-ASCII left
    alone. Getting any of the three wrong reformats a 76 KB file the user did not ask us
    to touch, and buries the one line that changed."""
    ws.write(seeded, ws.apply(ws.read(seeded), "/fresh", True))
    raw = seeded.read_text()
    assert raw.startswith('{\n  "numStartups": 7,')
    assert not raw.endswith("\n")
    assert "kéep" in raw, "ensure_ascii escaped a string it should have left alone"


def test_key_order_is_preserved(seeded):
    ws.write(seeded, ws.apply(ws.read(seeded), "/fresh", True))
    after = json.loads(seeded.read_text())
    assert list(after) == list(SEEDED)
    assert list(after["projects"]) == ["/other", "/fresh"]


def test_the_mode_survives_a_write(seeded):
    """The file holds an oauth account. A temp file renamed into place would otherwise
    take whatever the umask says, which on most machines is world-readable."""
    ws.write(seeded, ws.apply(ws.read(seeded), "/fresh", True))
    assert stat.S_IMODE(seeded.stat().st_mode) == 0o600


def test_no_temp_file_is_left_behind(seeded):
    ws.write(seeded, ws.apply(ws.read(seeded), "/fresh", True))
    assert [p.name for p in seeded.parent.iterdir()] == [".claude.json"]


def test_a_missing_file_is_missing_not_merely_unreadable(tmp_path):
    """The two are separate because they answer differently: nothing is trusted on a
    machine with no config, which is a report; a corrupt one is a refusal to write."""
    with pytest.raises(ws.Missing):
        ws.read(tmp_path / "absent.json")


def test_malformed_json_refuses_rather_than_reading_as_empty(tmp_path):
    path = tmp_path / ".claude.json"
    path.write_text("{ not json")
    with pytest.raises(ws.Unreadable) as raised:
        ws.read(path)
    assert not isinstance(raised.value, ws.Missing), "a corrupt file read as an absent one"


def test_a_json_scalar_is_not_a_config(tmp_path):
    path = tmp_path / ".claude.json"
    path.write_text("[]")
    with pytest.raises(ws.Unreadable):
        ws.read(path)


# --- the report ---------------------------------------------------------------


def lines(state, **kwargs):
    out = []
    code = (
        trust.changed(state, kwargs["value"], emit=out.append)
        if "value" in kwargs
        else trust.show(state, kwargs.get("missing", False), emit=out.append)
    )
    return code, "\n".join(out)


def test_the_report_names_the_grantor_when_trust_is_inherited(tmp_path):
    project = tmp_path / "p"
    project.mkdir()
    config = config_with(**{str(tmp_path): True, str(project): False})
    code, text = lines(trust.resolve(config, project))
    assert code == errors.OK
    assert str(tmp_path) in text
    assert "inherited" in text


def test_an_untrusted_workspace_exits_drift(tmp_path):
    project = tmp_path / "p"
    project.mkdir()
    code, text = lines(trust.resolve({}, project))
    assert code == errors.DRIFT
    assert "Not trusted" in text
    assert "claude-kit trust --on" in text


def test_the_report_flags_a_worktree(tmp_path):
    main, worktree = make_worktree(tmp_path)
    _, text = lines(trust.resolve({}, worktree))
    assert str(main) in text
    assert "worktree" in text


def test_clearing_under_a_trusted_ancestor_says_so_and_still_exits_ok(tmp_path):
    """The case the chosen behaviour has to be honest about: the write happened, and the
    workspace is still trusted."""
    project = tmp_path / "p"
    project.mkdir()
    config = config_with(**{str(tmp_path): True, str(project): False})
    code, text = lines(trust.resolve(config, project), value=False)
    assert code == errors.OK
    assert "Still trusted" in text
    assert f"claude-kit trust --off {tmp_path}" in text


def test_trusting_a_directory_warns_about_the_projects_beneath_it(tmp_path):
    child = tmp_path / "child"
    child.mkdir()
    config = config_with(**{str(tmp_path): True, str(child): False})
    _, text = lines(trust.resolve(config, tmp_path), value=True)
    assert "beneath it" in text
    assert str(child) in text


# --- doctor's check ----------------------------------------------------------


def plugin_project(tmp_path, claude):
    """A project with one plugin linked, which is what arms the trust check."""
    project = tmp_path / "proj"
    skills = project / ".claude" / "skills"
    skills.mkdir(parents=True)
    (skills / "backend").symlink_to(claude / "plugins" / "backend")
    return project


def test_g18_a_linked_plugin_in_an_untrusted_workspace_is_a_problem(tmp_path):
    project = plugin_project(tmp_path, CLAUDE)
    findings = checks.untrusted_workspace({}, project, CLAUDE)
    assert [f.check for f in findings] == ["untrusted-workspace"]
    assert findings[0].is_problem
    assert findings[0].kind == "plugin"


def test_g18_inherited_trust_satisfies_the_check(tmp_path):
    project = plugin_project(tmp_path, CLAUDE)
    config = config_with(**{str(tmp_path): True})
    assert checks.untrusted_workspace(config, project, CLAUDE) == []


def test_g18_a_project_with_no_plugins_is_never_asked_about_trust(tmp_path, project):
    """Trust is Claude Code's business until something claude-kit installed depends on
    it. Reporting it everywhere is how a report earns being skipped."""
    assert checks.untrusted_workspace({}, project, CLAUDE) == []


def test_g18_is_skipped_outside_a_project():
    assert checks.untrusted_workspace({}, None, CLAUDE) == []


# --- end to end through the shim ---------------------------------------------


def seed(home, **entries):
    (home / ".claude.json").write_text(json.dumps(config_with(**entries), indent=2))


def test_the_shim_reports_an_untrusted_directory(kit, tmp_path):
    where = tmp_path / "elsewhere"
    where.mkdir()
    seed(kit.home)
    result = kit("trust", str(where))
    assert result.returncode == errors.DRIFT
    assert "Not trusted" in result.stdout


def test_the_shim_trusts_then_reports_trusted(kit, tmp_path):
    where = tmp_path / "elsewhere"
    where.mkdir()
    seed(kit.home)
    assert kit("trust", "--on", str(where)).returncode == errors.OK
    assert json.loads((kit.home / ".claude.json").read_text())["projects"][str(where)][TRUSTED]
    assert kit("trust", str(where)).returncode == errors.OK


def test_the_shim_refuses_a_second_identical_change(kit, tmp_path):
    where = tmp_path / "elsewhere"
    where.mkdir()
    seed(kit.home, **{str(where): True})
    result = kit("trust", "--on", str(where))
    assert result.returncode == errors.ALREADY
    assert "already trusted" in result.stderr


def test_the_shim_refuses_off_when_there_is_nothing_to_clear(kit, tmp_path):
    where = tmp_path / "elsewhere"
    where.mkdir()
    seed(kit.home)
    assert kit("trust", "--off", str(where)).returncode == errors.ALREADY


def test_the_shim_will_not_create_claude_codes_config(kit, tmp_path):
    """The fixture makes ~/.claude but not ~/.claude.json, which is the fresh-machine
    case. A write has to refuse rather than invent that file."""
    where = tmp_path / "elsewhere"
    where.mkdir()
    result = kit("trust", "--on", str(where))
    assert result.returncode == errors.USAGE
    assert not (kit.home / ".claude.json").exists()


def test_the_shim_shows_an_answer_with_no_config_at_all(kit, tmp_path):
    where = tmp_path / "elsewhere"
    where.mkdir()
    result = kit("trust", str(where))
    assert result.returncode == errors.DRIFT
    assert "No ~/.claude.json yet" in result.stdout


def test_the_shim_refuses_both_switches_at_once(kit):
    result = kit("trust", "--on", "--off")
    assert result.returncode == errors.USAGE
    assert "not allowed with" in result.stderr


def test_the_shim_refuses_to_write_over_a_config_it_cannot_read(kit, tmp_path):
    where = tmp_path / "elsewhere"
    where.mkdir()
    (kit.home / ".claude.json").write_text("{ truncated")
    result = kit("trust", "--on", str(where))
    assert result.returncode == errors.USAGE
    assert (kit.home / ".claude.json").read_text() == "{ truncated"


def test_trust_takes_no_type(kit, tmp_path):
    """The one command with no --type: workspace trust is a property of a directory, not
    of an artifact, and a flag that narrowed nothing would be a lie."""
    result = kit("trust", "--type", "skill")
    assert result.returncode == errors.USAGE
    assert "--type" in result.stderr
