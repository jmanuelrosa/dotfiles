"""Groups E and F: `update` and `outdated`.

The network is stubbed at exactly one seam, `upstream.fetch`. Everything below it
runs for real against real bytes: tarballs are built in tmp_path, so
strip-components semantics, the exclude set, the byte comparison and the atomic
swap are all exercised rather than mocked.
"""

import json
import tarfile

import pytest

from claude_kit import catalog as cat
from claude_kit import errors, registry, upstream
from claude_kit.commands import sync


# --- building fixture upstreams ---------------------------------------------


def write_tree(root, files):
    """Create {relative path: contents} under root."""
    for relative, contents in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents)
    return root


def make_tarball(tmp_path, name, files, wrapper="repo-main"):
    """A .tar.gz shaped like GitHub's: everything inside one wrapper directory.

    The wrapper is what strip=1 exists to discard, so building it faithfully is
    what makes the extraction test meaningful.
    """
    staging = tmp_path / f"staging-{name}"
    write_tree(staging / wrapper, files)
    archive_path = tmp_path / f"{name}.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(staging / wrapper, arcname=wrapper)
    return archive_path


# --- extraction: strip-components and traversal safety ----------------------


def test_e_extraction_strips_the_wrapper_directory(tmp_path):
    """GitHub wraps everything in <repo>-<ref>/, which strip=1 discards."""
    archive = make_tarball(tmp_path, "a", {"skills/x/SKILL.md": "body"}, wrapper="skills-main")
    out = upstream.extract(archive, tmp_path / "out")
    assert (out / "skills" / "x" / "SKILL.md").read_text() == "body"
    assert not (out / "skills-main").exists()


def test_e_extraction_refuses_path_traversal(tmp_path):
    """A tarball is remote input, so an escaping member must be dropped, not written."""
    staging = tmp_path / "evil"
    (staging / "wrapper").mkdir(parents=True)
    (staging / "wrapper" / "fine.txt").write_text("ok")
    escape = tmp_path / "escape.txt"
    escape.write_text("pwned")

    archive_path = tmp_path / "evil.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(staging / "wrapper", arcname="wrapper")
        archive.add(escape, arcname="wrapper/../../escaped.txt")

    out = upstream.extract(archive_path, tmp_path / "out")
    assert (out / "fine.txt").read_text() == "ok"
    assert not (tmp_path / "escaped.txt").exists()
    assert not (out.parent / "escaped.txt").exists()


def test_e_extraction_drops_members_shallower_than_the_strip(tmp_path):
    archive = make_tarball(tmp_path, "b", {"a.txt": "x"}, wrapper="w")
    out = upstream.extract(archive, tmp_path / "out")
    assert (out / "a.txt").read_text() == "x"


# --- E2: upstream_path "." means the repo root ------------------------------


@pytest.mark.parametrize("path", ["", ".", "/", None])
def test_e2_a_root_upstream_path_is_the_checkout_itself(tmp_path, path):
    root = tmp_path / "checkout"
    root.mkdir()
    assert upstream.subtree(root, path) == root


def test_e2_a_nested_upstream_path_descends(tmp_path):
    root = tmp_path / "checkout"
    assert upstream.subtree(root, "skills/commit") == root / "skills" / "commit"


def test_e2_a_trailing_slash_is_tolerated(tmp_path):
    root = tmp_path / "checkout"
    assert upstream.subtree(root, "skills/commit/") == root / "skills" / "commit"


# --- E3: the exclude set ----------------------------------------------------


def test_e3_excluded_directories_are_not_copied(tmp_path):
    source = write_tree(
        tmp_path / "src",
        {
            "SKILL.md": "body",
            ".git/config": "gitstuff",
            ".github/workflows/ci.yml": "ci",
            "node_modules/pkg/index.js": "js",
            "references/deep.md": "keep",
        },
    )
    destination = tmp_path / "dst"
    upstream.copy_tree(source, destination)

    assert (destination / "SKILL.md").read_text() == "body"
    assert (destination / "references" / "deep.md").read_text() == "keep"
    for excluded in (".git", ".github", "node_modules"):
        assert not (destination / excluded).exists(), f"{excluded} should be excluded"


def test_e3_excluded_directories_do_not_count_as_a_difference(tmp_path):
    """Upstream carrying .github must not make an otherwise-identical skill look
    behind, or every check would report drift forever."""
    source = write_tree(tmp_path / "src", {"SKILL.md": "same", ".github/ci.yml": "ci"})
    destination = write_tree(tmp_path / "dst", {"SKILL.md": "same"})
    assert upstream.differs(source, destination) is False


# --- comparison -------------------------------------------------------------


def test_differs_is_false_for_identical_trees(tmp_path):
    files = {"SKILL.md": "body", "references/a.md": "a"}
    assert upstream.differs(write_tree(tmp_path / "s", files), write_tree(tmp_path / "d", files)) is False


def test_differs_detects_changed_contents(tmp_path):
    source = write_tree(tmp_path / "s", {"SKILL.md": "new"})
    destination = write_tree(tmp_path / "d", {"SKILL.md": "old"})
    assert upstream.differs(source, destination) is True


def test_differs_compares_bytes_not_mtimes(tmp_path):
    """filecmp.dircmp defaults to shallow, calling two files equal when size and
    mtime match. A same-length edit would then read as up to date and never sync."""
    source = write_tree(tmp_path / "s", {"SKILL.md": "aaaa"})
    destination = write_tree(tmp_path / "d", {"SKILL.md": "bbbb"})
    stat = (source / "SKILL.md").stat()
    import os

    os.utime(destination / "SKILL.md", (stat.st_atime, stat.st_mtime))
    assert (source / "SKILL.md").stat().st_size == (destination / "SKILL.md").stat().st_size
    assert upstream.differs(source, destination) is True


def test_differs_detects_an_added_file(tmp_path):
    source = write_tree(tmp_path / "s", {"SKILL.md": "x", "new.md": "y"})
    destination = write_tree(tmp_path / "d", {"SKILL.md": "x"})
    assert upstream.differs(source, destination) is True


def test_differs_detects_a_removed_file(tmp_path):
    source = write_tree(tmp_path / "s", {"SKILL.md": "x"})
    destination = write_tree(tmp_path / "d", {"SKILL.md": "x", "stale.md": "y"})
    assert upstream.differs(source, destination) is True


def test_differs_is_true_when_the_destination_is_absent(tmp_path):
    assert upstream.differs(write_tree(tmp_path / "s", {"a": "b"}), tmp_path / "nope") is True


# --- E9: atomicity ----------------------------------------------------------


def test_e9_a_failed_copy_leaves_the_old_tree_intact(tmp_path, monkeypatch):
    """The fish version did `rm -rf` then rsync, destroying the skill if the copy
    failed halfway. Staging plus a swap means an interruption keeps the old tree.
    """
    source = write_tree(tmp_path / "src", {"SKILL.md": "new"})
    destination = write_tree(tmp_path / "dst", {"SKILL.md": "old"})

    import shutil

    def explode(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(shutil, "copytree", explode)
    with pytest.raises(OSError):
        upstream.copy_tree(source, destination)

    assert (destination / "SKILL.md").read_text() == "old", "the old tree must survive"


def test_e9_a_successful_copy_replaces_the_tree_completely(tmp_path):
    source = write_tree(tmp_path / "src", {"SKILL.md": "new"})
    destination = write_tree(tmp_path / "dst", {"SKILL.md": "old", "gone.md": "stale"})
    upstream.copy_tree(source, destination)
    assert (destination / "SKILL.md").read_text() == "new"
    assert not (destination / "gone.md").exists(), "a removed upstream file should go"


def test_e9_no_staging_directories_survive(tmp_path):
    source = write_tree(tmp_path / "src", {"SKILL.md": "x"})
    destination = tmp_path / "dst" / "skill"
    upstream.copy_tree(source, destination)
    leftovers = [p.name for p in destination.parent.iterdir() if p.name.startswith(".")]
    assert leftovers == []


def test_copy_tree_creates_a_missing_parent(tmp_path):
    source = write_tree(tmp_path / "src", {"SKILL.md": "x"})
    destination = tmp_path / "a" / "b" / "skill"
    upstream.copy_tree(source, destination)
    assert (destination / "SKILL.md").read_text() == "x"


# --- E4: registry stamping --------------------------------------------------


REGISTRY = {
    "version": 2,
    "repos": {
        "owner/one": {
            "branch": "main",
            "skills": [
                {"upstream_path": "skills/alpha", "groups": ["engineering"], "updated_at": "2020-01-01T00:00:00Z"},
                {"upstream_path": "skills/beta", "groups": ["quality"], "updated_at": "2020-01-01T00:00:00Z"},
            ],
        },
        "owner/two": {"branch": "trunk", "skills": [{"upstream_path": ".", "groups": []}]},
    },
    "local_skills": [{"name": "mine", "groups": ["ai"], "note": "Locally authored"}],
}


def test_e4_stamping_touches_only_the_named_entry(tmp_path):
    path = tmp_path / "skill-registry.json"
    path.write_text(json.dumps(REGISTRY, indent=2) + "\n")

    assert registry.stamp_entry(path, "owner/one", "skills/alpha", "2026-07-28T10:00:00Z")
    after = json.loads(path.read_text())

    entries = after["repos"]["owner/one"]["skills"]
    assert entries[0]["updated_at"] == "2026-07-28T10:00:00Z"
    assert entries[1]["updated_at"] == "2020-01-01T00:00:00Z", "sibling must not change"


def test_e4_everything_else_is_byte_identical(tmp_path):
    """A hand-maintained registry must survive a write with only the one field
    changed: no reordered keys, no dropped fields, no reformatting."""
    path = tmp_path / "skill-registry.json"
    original = json.dumps(REGISTRY, indent=2) + "\n"
    path.write_text(original)

    registry.stamp_entry(path, "owner/one", "skills/alpha", "2026-07-28T10:00:00Z")
    rewritten = path.read_text()

    expected = original.replace(
        '"updated_at": "2020-01-01T00:00:00Z"', '"updated_at": "2026-07-28T10:00:00Z"', 1
    )
    assert rewritten == expected


def test_e4_key_order_is_preserved(tmp_path):
    path = tmp_path / "skill-registry.json"
    path.write_text(json.dumps(REGISTRY, indent=2) + "\n")
    registry.stamp_entry(path, "owner/one", "skills/alpha", "2026-07-28T10:00:00Z")
    after = json.loads(path.read_text())
    assert list(after) == list(REGISTRY)
    assert list(after["repos"]) == list(REGISTRY["repos"])
    assert list(after["repos"]["owner/one"]["skills"][0]) == [
        "upstream_path", "groups", "updated_at",
    ]


def test_e4_an_entry_with_no_timestamp_gains_one(tmp_path):
    path = tmp_path / "skill-registry.json"
    path.write_text(json.dumps(REGISTRY, indent=2) + "\n")
    registry.stamp_entry(path, "owner/two", ".", "2026-07-28T10:00:00Z")
    after = json.loads(path.read_text())
    assert after["repos"]["owner/two"]["skills"][0]["updated_at"] == "2026-07-28T10:00:00Z"


def test_e4_an_unmatched_entry_writes_nothing(tmp_path):
    path = tmp_path / "skill-registry.json"
    original = json.dumps(REGISTRY, indent=2) + "\n"
    path.write_text(original)
    assert registry.stamp_entry(path, "owner/one", "skills/nope", "2026-07-28T10:00:00Z") is False
    assert path.read_text() == original


def test_e4_an_unknown_repo_writes_nothing(tmp_path):
    path = tmp_path / "skill-registry.json"
    original = json.dumps(REGISTRY, indent=2) + "\n"
    path.write_text(original)
    assert registry.stamp_entry(path, "owner/absent", "skills/alpha", "x") is False
    assert path.read_text() == original


def test_stamp_is_iso8601_zulu():
    stamped = upstream.stamp()
    from datetime import datetime

    assert datetime.strptime(stamped, "%Y-%m-%dT%H:%M:%SZ")


# --- a fixture repo, for the command-level cases ---------------------------


@pytest.fixture
def fixture_repo(tmp_path):
    """A claude store with two tracked skills from one repo, plus a local one."""
    claude = tmp_path / "claude"
    (claude / "skills").mkdir(parents=True)
    (claude / "agents").mkdir()
    (claude / "plugins").mkdir()

    (claude / "skill-registry.json").write_text(
        json.dumps(
            {
                "version": 2,
                "repos": {
                    "owner/one": {
                        "branch": "main",
                        "skills": [
                            {"upstream_path": "skills/alpha", "groups": [], "updated_at": "2020-01-01T00:00:00Z"},
                            {"upstream_path": "skills/beta", "groups": [], "updated_at": "2020-01-01T00:00:00Z"},
                        ],
                    }
                },
                "local_skills": [{"name": "mine", "groups": [], "note": "local"}],
            },
            indent=2,
        )
        + "\n"
    )
    (claude / "agent-registry.json").write_text(json.dumps({"version": 2, "repos": {}}, indent=2))
    write_tree(claude / "skills" / "alpha", {"SKILL.md": "old alpha"})
    write_tree(claude / "skills" / "beta", {"SKILL.md": "current beta"})
    write_tree(claude / "skills" / "mine", {"SKILL.md": "local"})
    return claude


@pytest.fixture
def upstream_files(tmp_path):
    """What the fake upstream serves: alpha changed, beta unchanged."""
    return {
        "skills/alpha/SKILL.md": "new alpha",
        "skills/beta/SKILL.md": "current beta",
        ".github/workflows/ci.yml": "ci",
    }


def fetcher_for(files, fail_repos=()):
    """A stand-in for upstream.fetch that unpacks a tree instead of downloading."""

    def fetcher(repo, branch, destination):
        if repo in fail_repos:
            raise upstream.FetchError(f"could not fetch {repo}: simulated network failure")
        write_tree(destination, files)
        return destination

    return fetcher


class _Args:
    def __init__(self, command, kind=cat.SKILL, names=None):
        self.command = command
        self.type = kind
        self.names = names or []


@pytest.fixture
def at(fixture_repo, monkeypatch):
    """Point paths.claude_dir at the fixture store."""
    from claude_kit import paths

    monkeypatch.setattr(paths, "claude_dir", lambda root=None: fixture_repo)
    return fixture_repo


# --- E1, E7: update ---------------------------------------------------------


def test_e1_a_behind_skill_is_synced(at, upstream_files, capsys):
    code = sync.run(_Args("update"), fetcher=fetcher_for(upstream_files))
    assert code == errors.OK
    assert (at / "skills" / "alpha" / "SKILL.md").read_text() == "new alpha"


def test_e7_a_current_skill_is_not_rewritten(at, upstream_files, capsys):
    before = (at / "skills" / "beta" / "SKILL.md").stat().st_mtime_ns
    sync.run(_Args("update"), fetcher=fetcher_for(upstream_files))
    after = (at / "skills" / "beta" / "SKILL.md").stat().st_mtime_ns
    assert before == after, "an up-to-date skill should not be touched"
    out = capsys.readouterr().out
    assert "beta: up to date" in out


def test_e4_update_stamps_only_what_it_synced(at, upstream_files, capsys):
    sync.run(_Args("update"), fetcher=fetcher_for(upstream_files))
    after = json.loads((at / "skill-registry.json").read_text())
    entries = {e["upstream_path"]: e for e in after["repos"]["owner/one"]["skills"]}
    assert entries["skills/alpha"]["updated_at"] != "2020-01-01T00:00:00Z"
    assert entries["skills/beta"]["updated_at"] == "2020-01-01T00:00:00Z"


def test_absent_skills_are_installed(at, upstream_files, capsys):
    import shutil

    shutil.rmtree(at / "skills" / "alpha")
    sync.run(_Args("update"), fetcher=fetcher_for(upstream_files))
    assert (at / "skills" / "alpha" / "SKILL.md").read_text() == "new alpha"
    assert "installed" in capsys.readouterr().out


# --- E5: local skills -------------------------------------------------------


def test_e5_a_local_skill_is_reported_not_failed(at, upstream_files, capsys):
    code = sync.run(_Args("update", names=["mine"]), fetcher=fetcher_for(upstream_files))
    assert code == errors.OK
    assert "no upstream to sync" in capsys.readouterr().out


def test_e5_a_local_skill_is_never_modified(at, upstream_files, capsys):
    sync.run(_Args("update"), fetcher=fetcher_for(upstream_files))
    assert (at / "skills" / "mine" / "SKILL.md").read_text() == "local"


def test_a_bare_run_says_nothing_about_local_skills(at, upstream_files, capsys):
    """Naming one deserves an explanation; listing every one on a bare run is a wall
    of warnings about nothing being wrong."""
    sync.run(_Args("outdated"), fetcher=fetcher_for(upstream_files))
    assert "mine" not in capsys.readouterr().out


# --- E6: partial failure ----------------------------------------------------


def test_e6_one_failing_repo_still_syncs_the_others(tmp_path, monkeypatch, capsys):
    claude = tmp_path / "claude"
    (claude / "skills").mkdir(parents=True)
    (claude / "plugins").mkdir()
    (claude / "skill-registry.json").write_text(
        json.dumps(
            {
                "version": 2,
                "repos": {
                    "owner/good": {"branch": "main", "skills": [{"upstream_path": "skills/alpha", "groups": []}]},
                    "owner/bad": {"branch": "main", "skills": [{"upstream_path": "skills/gamma", "groups": []}]},
                },
            },
            indent=2,
        )
        + "\n"
    )
    (claude / "agent-registry.json").write_text(json.dumps({"version": 2, "repos": {}}))
    write_tree(claude / "skills" / "alpha", {"SKILL.md": "old"})
    write_tree(claude / "skills" / "gamma", {"SKILL.md": "keep me"})

    from claude_kit import paths

    monkeypatch.setattr(paths, "claude_dir", lambda root=None: claude)

    files = {"skills/alpha/SKILL.md": "new", "skills/gamma/SKILL.md": "unused"}
    code = sync.run(_Args("update"), fetcher=fetcher_for(files, fail_repos={"owner/bad"}))

    assert code == errors.FETCH_FAILED
    assert (claude / "skills" / "alpha" / "SKILL.md").read_text() == "new", "the good repo should sync"
    assert (claude / "skills" / "gamma" / "SKILL.md").read_text() == "keep me", "the failed one is untouched"
    assert "simulated network failure" in capsys.readouterr().out


# --- E8: a missing upstream_path ------------------------------------------


def test_e8_a_missing_upstream_path_fails_without_deleting(at, capsys):
    """The tarball arrived but does not contain what the registry claims. The
    destination must survive: an upstream reorganisation should not delete a skill.
    """
    files = {"skills/beta/SKILL.md": "current beta"}
    code = sync.run(_Args("update"), fetcher=fetcher_for(files))
    assert code == errors.FETCH_FAILED
    assert (at / "skills" / "alpha" / "SKILL.md").read_text() == "old alpha"
    assert "not in the tarball" in capsys.readouterr().out


# --- E10: skills only -------------------------------------------------------


def _never_fetch(repo, branch, destination):
    raise AssertionError(f"the network must not be reached, but {repo} was requested")


@pytest.mark.parametrize("kind", [cat.AGENT, cat.PLUGIN])
@pytest.mark.parametrize("command", ["update", "outdated"])
def test_e10_agents_and_plugins_are_refused(kind, command, capsys):
    """The refusal must come before any fetch.

    targets() looks at skills regardless of --type, so this guard is the only thing
    stopping `update --type agent` from downloading every tracked repo. The
    exploding fetcher pins that ordering, and keeps a guard regression from turning
    the suite into a network client.
    """
    code = sync.run(_Args(command, kind=kind), fetcher=_never_fetch)
    assert code == errors.USAGE
    assert "only skills have upstreams" in capsys.readouterr().err


# E10 above already pins "before any fetch" for both commands over both wrong types,
# with the same exploding fetcher. test_type_contract.test_a1_touches_nothing is where
# the wider "a wrong --type writes nothing at all" claim is held.


# --- E11: no project needed -------------------------------------------------


def test_e11_update_needs_no_project(at, upstream_files, tmp_path, monkeypatch, capsys):
    """update writes into the dotfiles checkout, not a project, so any cwd works."""
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    assert sync.run(_Args("update"), fetcher=fetcher_for(upstream_files)) == errors.OK


# --- F1 to F5: outdated -----------------------------------------------------


def test_f1_outdated_reports_behind_and_writes_nothing(at, upstream_files, capsys):
    before = (at / "skills" / "alpha" / "SKILL.md").read_text()
    registry_before = (at / "skill-registry.json").read_text()

    code = sync.run(_Args("outdated"), fetcher=fetcher_for(upstream_files))

    assert code == errors.OK
    assert "alpha: behind" in capsys.readouterr().out
    assert (at / "skills" / "alpha" / "SKILL.md").read_text() == before, "no content change"
    assert (at / "skill-registry.json").read_text() == registry_before, "no stamp"


def test_f2_a_current_skill_is_reported_up_to_date(at, upstream_files, capsys):
    sync.run(_Args("outdated"), fetcher=fetcher_for(upstream_files))
    assert "beta: up to date" in capsys.readouterr().out


def test_f3_an_absent_skill_reads_differently_from_behind(at, upstream_files, capsys):
    import shutil

    shutil.rmtree(at / "skills" / "alpha")
    sync.run(_Args("outdated"), fetcher=fetcher_for(upstream_files))
    out = capsys.readouterr().out
    assert "alpha: not downloaded" in out
    assert "alpha: behind" not in out


def test_f4_being_behind_exits_ok(at, upstream_files, capsys):
    """Behind is information, not failure. Exiting non-zero would leave `outdated`
    usable only as a gate."""
    assert sync.run(_Args("outdated"), fetcher=fetcher_for(upstream_files)) == errors.OK


def test_f5_a_fetch_failure_exits_fetch_failed(at, upstream_files, capsys):
    code = sync.run(_Args("outdated"), fetcher=fetcher_for(upstream_files, fail_repos={"owner/one"}))
    assert code == errors.FETCH_FAILED


def test_outdated_and_update_agree_on_what_is_behind(at, upstream_files, capsys):
    """A separate implementation could disagree, and then the report would not
    predict the sync. Same traversal, writes switched off."""
    sync.run(_Args("outdated"), fetcher=fetcher_for(upstream_files))
    reported_behind = "alpha: behind" in capsys.readouterr().out

    sync.run(_Args("update"), fetcher=fetcher_for(upstream_files))
    actually_synced = "alpha: ✓ synced." in capsys.readouterr().out

    assert reported_behind == actually_synced is True


# --- name selection ---------------------------------------------------------


def test_naming_one_skill_leaves_the_others_alone(at, upstream_files, capsys):
    sync.run(_Args("update", names=["alpha"]), fetcher=fetcher_for(upstream_files))
    out = capsys.readouterr().out
    assert "alpha" in out
    assert "beta" not in out


def test_an_unknown_name_is_not_found(at, upstream_files, capsys):
    code = sync.run(_Args("update", names=["no-such-skill"]), fetcher=fetcher_for(upstream_files))
    assert code == errors.NOT_FOUND
    assert "not a known skill" in capsys.readouterr().err


def test_targets_groups_by_repo(at):
    catalog = cat.build_catalog(at)
    by_repo, local, unknown = sync.targets(catalog, [])
    assert set(by_repo) == {"owner/one"}
    assert {s.name for s in by_repo["owner/one"]} == {"alpha", "beta"}
    assert {s.name for s in local} == {"mine"}
    assert unknown == []


def test_targets_reports_unknown_names(at):
    catalog = cat.build_catalog(at)
    _, _, unknown = sync.targets(catalog, ["alpha", "ghost"])
    assert unknown == ["ghost"]


# --- the real fetch is only wired up, never called -------------------------


def test_the_real_fetcher_builds_a_github_tarball_url():
    assert upstream.tarball_url("owner/repo", "main") == (
        "https://github.com/owner/repo/archive/main.tar.gz"
    )


def test_fetch_raises_fetcherror_for_an_unreachable_host(monkeypatch, tmp_path):
    """The error type matters: process_repo catches FetchError to keep going after
    one bad repo, so a raw URLError escaping would abandon the whole run."""
    import urllib.error
    import urllib.request

    def explode(*args, **kwargs):
        raise urllib.error.URLError("no network")

    monkeypatch.setattr(urllib.request, "urlopen", explode)
    with pytest.raises(upstream.FetchError):
        upstream.fetch("owner/repo", "main", tmp_path / "out")


def test_fetch_raises_fetcherror_for_a_truncated_response(monkeypatch, tmp_path):
    """A chunked response cut short raises http.client.IncompleteRead, which is an
    HTTPException and not an OSError, so it once escaped as a traceback and abandoned
    every repo still to be checked."""
    import http.client
    import urllib.request

    class _Truncated:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self, *args):
            raise http.client.IncompleteRead(b"partial", 3607)

    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: _Truncated())
    with pytest.raises(upstream.FetchError):
        upstream.fetch("owner/repo", "main", tmp_path / "out")
