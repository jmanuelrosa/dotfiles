import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location("diagrams", SCRIPTS / "diagrams.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


diagrams = _load()


def git(root, *args):
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=True,
        env={
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
            "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
            "HOME": str(root),
        },
    ).stdout.strip()


def commit(root, message):
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)
    return git(root, "rev-parse", "--short", "HEAD")


def page(name, sha, paths, kind="explanation", closed=True):
    body = (
        f"# Doc\n\n<!-- diagram name={name} kind={kind} sha={sha} paths={paths} -->\n"
        "```mermaid\nflowchart LR\n  a --> b\n```\n"
    )
    return body + ("<!-- /diagram -->\n" if closed else "")


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "src" / "auth").mkdir(parents=True)
    (tmp_path / "src" / "auth" / "login.ts").write_text("v1\n")
    (tmp_path / "src" / "other.ts").write_text("v1\n")
    (tmp_path / "docs").mkdir()
    sha = commit(tmp_path, "init")
    (tmp_path / "docs" / "auth.md").write_text(page("auth-flow", sha, "src/auth/**"))
    commit(tmp_path, "docs")
    return tmp_path


def test_parse_markers_reads_attributes():
    found = diagrams.parse_markers(page("x", "abc1234", "a/**,b.ts", kind="how-to"), "d.md")
    assert len(found) == 1
    assert found[0].name == "x"
    assert found[0].kind == "how-to"
    assert found[0].sha == "abc1234"
    assert found[0].paths == ["a/**", "b.ts"]
    assert found[0].line == 3
    assert found[0].status == diagrams.STATUS_CURRENT


def test_parse_markers_flags_missing_attributes_and_unknown_kind():
    text = "<!-- diagram name=x kind=explanation -->\n<!-- /diagram -->\n"
    assert diagrams.parse_markers(text, "d.md")[0].problem == "missing sha, paths"
    text = page("x", "abc", "a", kind="poster")
    assert diagrams.parse_markers(text, "d.md")[0].problem == "unknown kind 'poster'"


def test_parse_markers_skips_examples_inside_a_fenced_block():
    text = "````markdown\n" + page("example", "abc", "a") + "````\n" + page("real", "abc", "a")
    assert [d.name for d in diagrams.parse_markers(text, "d.md")] == ["real"]


def test_parse_markers_flags_unclosed_block():
    found = diagrams.parse_markers(page("x", "abc", "a", closed=False), "d.md")
    assert found[0].status == diagrams.STATUS_INVALID
    assert "closing" in found[0].problem


def test_scan_is_current_when_anchored_paths_did_not_change(repo):
    found = diagrams.scan(repo, None)
    assert [d.status for d in found] == [diagrams.STATUS_CURRENT]


def test_scan_ignores_changes_outside_anchored_paths(repo):
    (repo / "src" / "other.ts").write_text("v2\n")
    commit(repo, "touch other")
    assert diagrams.scan(repo, None)[0].status == diagrams.STATUS_CURRENT


def test_scan_is_stale_after_a_commit_touching_anchored_paths(repo):
    (repo / "src" / "auth" / "login.ts").write_text("v2\n")
    commit(repo, "change login")
    found = diagrams.scan(repo, None)[0]
    assert found.status == diagrams.STATUS_STALE
    assert found.commits and found.commits[0].endswith("change login")


def test_scan_counts_working_tree_changes_as_stale(repo):
    (repo / "src" / "auth" / "login.ts").write_text("v2\n")
    found = diagrams.scan(repo, None)[0]
    assert found.status == diagrams.STATUS_STALE
    assert found.dirty == ["src/auth/login.ts"]


def test_scan_since_ref_uses_the_branch_diff(repo):
    git(repo, "switch", "-q", "-c", "feature/x")
    (repo / "src" / "auth" / "login.ts").write_text("v2\n")
    commit(repo, "change login")
    found = diagrams.scan(repo, "main")[0]
    assert found.status == diagrams.STATUS_STALE
    assert found.commits == ["src/auth/login.ts"]
    git(repo, "switch", "-q", "main")
    assert diagrams.scan(repo, "main")[0].status == diagrams.STATUS_CURRENT


def test_scan_reports_an_unknown_sha(repo):
    (repo / "docs" / "auth.md").write_text(page("auth-flow", "deadbeef", "src/auth/**"))
    assert diagrams.scan(repo, None)[0].status == diagrams.STATUS_UNKNOWN_SHA


def test_scan_skips_vendored_trees(repo):
    (repo / "node_modules" / "x").mkdir(parents=True)
    (repo / "node_modules" / "x" / "README.md").write_text(page("vendored", "abc", "a"))
    assert [d.name for d in diagrams.scan(repo, None)] == ["auth-flow"]


def test_scan_survives_a_non_utf8_markdown_file(repo):
    (repo / "docs" / "binary.md").write_bytes(b"\xff\xfe\x00junk")
    assert [d.name for d in diagrams.scan(repo, None)] == ["auth-flow"]


def test_stamp_rewrites_only_the_named_diagram(repo):
    (repo / "docs" / "auth.md").write_text(
        page("auth-flow", "0000000", "src/auth/**") + page("other", "0000000", "src/other.ts")
    )
    head = commit(repo, "two diagrams")
    assert diagrams.stamp(repo, ["auth-flow"], False) == diagrams.EXIT_OK
    text = (repo / "docs" / "auth.md").read_text()
    assert f"name=auth-flow kind=explanation sha={head}" in text
    assert "name=other kind=explanation sha=0000000" in text


def test_stamp_refuses_an_unknown_name(repo, capsys):
    assert diagrams.stamp(repo, ["nope"], False) == diagrams.EXIT_USAGE
    assert "nope" in capsys.readouterr().err


def test_main_exit_code_and_json(repo, capsys):
    assert diagrams.main(["--root", str(repo), "scan", "--json"]) == diagrams.EXIT_OK
    data = json.loads(capsys.readouterr().out)
    assert data[0]["name"] == "auth-flow"
    (repo / "src" / "auth" / "login.ts").write_text("v2\n")
    assert diagrams.main(["--root", str(repo), "scan"]) == diagrams.EXIT_STALE
    out = capsys.readouterr().out
    assert "STALE=1" in out
    assert "STATUS=stale" in out


def test_main_outside_a_repo(tmp_path, capsys):
    assert diagrams.main(["--root", str(tmp_path), "scan"]) == diagrams.EXIT_NOT_A_REPO


STUB_LINTER = """
import sys
source = sys.stdin.read()
if "BAD" in source:
    print("line 2: unexpected token BAD")
    sys.exit(1)
if "CRASH" in source:
    print("could not fetch package")
    sys.exit(2)
"""

DRAWIO_SOURCE = (
    '<mxfile><diagram id="a" name="a"><mxGraphModel><root>'
    '<mxCell id="0"/></root></mxGraphModel></diagram></mxfile>'
)


def drawio_page(name, sha, paths, export):
    return (
        f"# Doc\n\n<!-- diagram name={name} kind=reference sha={sha} paths={paths} -->\n"
        f"![{name}]({export})\n<!-- /diagram -->\n"
    )


@pytest.fixture
def stub_linter(tmp_path, monkeypatch):
    stub = tmp_path / "stub_linter.py"
    stub.write_text(STUB_LINTER)
    monkeypatch.setattr(diagrams, "LINTER", (sys.executable, str(stub)))


def test_parse_markers_detects_each_format():
    mermaid = diagrams.parse_markers(page("m", "abc", "a"), "d.md")[0]
    drawio = diagrams.parse_markers(drawio_page("d", "abc", "a", "x.drawio.svg"), "d.md")[0]
    empty = diagrams.parse_markers("<!-- diagram name=e kind=reference sha=a paths=a -->\ntext\n<!-- /diagram -->\n", "d.md")[0]
    assert (mermaid.format, drawio.format, empty.format) == ("mermaid", "drawio", "unknown")


def test_mermaid_source_is_the_text_between_the_fences():
    found = diagrams.parse_markers(page("m", "abc", "a"), "d.md")[0]
    assert diagrams.mermaid_source(found.body) == "flowchart LR\n  a --> b\n"


def test_lint_passes_a_clean_mermaid_block(repo, stub_linter):
    found = diagrams.scan(repo, None, run_lint=True)[0]
    assert (found.lint, found.lint_output) == ("ok", [])


def test_lint_reports_mermaid_diagnostics(repo, stub_linter):
    (repo / "docs" / "auth.md").write_text(page("auth-flow", "abc", "src/auth/**").replace("a --> b", "a --> BAD"))
    found = diagrams.scan(repo, "main", run_lint=True)[0]
    assert found.lint == "error"
    assert found.lint_output == ["line 2: unexpected token BAD"]


def test_lint_is_unavailable_when_the_linter_cannot_run(repo, monkeypatch):
    monkeypatch.setattr(diagrams, "LINTER", ("definitely-not-a-linter-on-path",))
    assert diagrams.scan(repo, None, run_lint=True)[0].lint == "unavailable"


def test_lint_is_unavailable_on_an_unexpected_exit(repo, stub_linter):
    (repo / "docs" / "auth.md").write_text(page("auth-flow", "abc", "src/auth/**").replace("a --> b", "a --> CRASH"))
    assert diagrams.scan(repo, "main", run_lint=True)[0].lint == "unavailable"


def test_lint_accepts_a_drawio_source_with_its_export(repo):
    (repo / "docs" / "diagrams").mkdir()
    (repo / "docs" / "diagrams" / "schema.drawio").write_text(DRAWIO_SOURCE)
    (repo / "docs" / "diagrams" / "schema.drawio.svg").write_text("<svg/>")
    (repo / "docs" / "schema.md").write_text(drawio_page("schema", "abc", "db/**", "diagrams/schema.drawio.svg"))
    found = diagrams.scan(repo, "main", run_lint=True, only={"schema"})
    assert [(d.name, d.lint) for d in found] == [("schema", "ok")]


def test_lint_names_a_missing_export_and_a_compressed_source(repo):
    (repo / "docs" / "diagrams").mkdir()
    (repo / "docs" / "diagrams" / "schema.drawio").write_text('<mxfile><diagram id="a">eJzt0zEOgCAQ</diagram></mxfile>')
    (repo / "docs" / "schema.md").write_text(drawio_page("schema", "abc", "db/**", "diagrams/schema.drawio.png"))
    found = diagrams.scan(repo, "main", run_lint=True, only={"schema"})[0]
    assert found.lint == "error"
    assert found.lint_output == [
        "docs/diagrams/schema.drawio: compressed; save it uncompressed so it diffs",
        "missing export diagrams/schema.drawio.png",
    ]


def test_lint_names_a_missing_drawio_source(repo):
    (repo / "docs" / "schema.md").write_text(drawio_page("schema", "abc", "db/**", "diagrams/schema.drawio.svg"))
    found = diagrams.scan(repo, "main", run_lint=True, only={"schema"})[0]
    assert found.lint_output[0] == "missing source docs/diagrams/schema.drawio"


def test_main_returns_the_lint_exit_code_before_the_stale_one(repo, stub_linter, capsys):
    (repo / "docs" / "auth.md").write_text(page("auth-flow", "abc", "src/auth/**").replace("a --> b", "a --> BAD"))
    (repo / "src" / "auth" / "login.ts").write_text("v2\n")
    assert diagrams.main(["--root", str(repo), "scan", "--since", "main", "--lint"]) == diagrams.EXIT_LINT
    out = capsys.readouterr().out
    assert "LINT_ERRORS=1" in out
    assert "lint: line 2: unexpected token BAD" in out


def test_main_only_limits_the_scan(repo, capsys):
    assert diagrams.main(["--root", str(repo), "scan", "--only", "nope"]) == diagrams.EXIT_OK
    assert capsys.readouterr().out.strip() == "DIAGRAMS=0"
