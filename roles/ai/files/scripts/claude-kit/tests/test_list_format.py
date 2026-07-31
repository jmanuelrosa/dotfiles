"""The exact bytes `claude-kit list` prints, row shape by row shape.

The template came from the `claude-skill` / `claude-agent` fish functions claude-kit
replaced, and while both shipped a differential test held them to the same bytes. Those
functions are gone, so this file is what pins the format now: every test asserts a
literal with the escape codes in it, and a failure says which piece moved.
"""

import os
import subprocess
import sys

import pytest

from claude_kit import catalog as cat
from claude_kit import scope
from dotkit import colors
from claude_kit.commands import listing
from dotkit.testing import CLAUDE, REPO
from kit_helpers import SHIM

RESET = "\x1b[m"
GREEN = "\x1b[32m"
CYAN = "\x1b[36m"
DIM = "\x1b[90m"
BOLD = "\x1b[1m"


def row(name="thing", **overrides):
    base = {
        "name": name,
        "state": listing.AVAILABLE,
        "installed": None,
        "global": False,
        "groups": (),
        "dependencies": (),
        "reason": None,
        "parent": None,
    }
    base.update(overrides)
    return base


# --- the palette ------------------------------------------------------------


def test_reset_matches_fishs_set_color(coloured):
    """fish emits \\x1b[m, not \\x1b[0m. Both reset, but only one is byte-identical."""
    assert colors.paint("x", "green") == f"{GREEN}x{RESET}"


def test_colour_is_off_when_not_a_terminal():
    """Piping to a file or a test harness should yield plain text.

    Which is why every test here forces colour on rather than assuming a terminal: under
    pytest stdout is a pipe, so the literals below would otherwise all be plain.
    """
    assert colors.paint("x", "green") == "x"


def test_no_color_beats_force_color(monkeypatch):
    """A user who asked for no colour anywhere means it."""
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.setenv("NO_COLOR", "1")
    assert colors.paint("x", "green") == "x"


# --- the three row shapes ---------------------------------------------------


def test_a_linked_row(coloured):
    got = listing.format_row(row("coderabbit", state=listing.LINKED, installed=scope.PROJECT))
    assert got == f"  {GREEN}✓{RESET} coderabbit {GREEN}(linked){RESET}"


def test_an_available_row(coloured):
    assert listing.format_row(row("astro")) == f"  {DIM}·{RESET} astro"


def test_a_not_downloaded_row_dims_the_whole_run(coloured):
    """"↓ name (not downloaded)" is dimmed as one unit, not just the glyph."""
    got = listing.format_row(row("never-fetched", state=listing.MISSING))
    assert got == f"  {DIM}↓ never-fetched (not downloaded){RESET}"


# --- suffixes ---------------------------------------------------------------


def test_groups_are_cyan_bracketed_and_comma_joined(coloured):
    got = listing.format_row(row("x", groups=("engineering", "frontend")))
    assert f"{CYAN}[engineering, frontend]{RESET}" in got


def test_groups_are_sorted_and_deduped(catalog, effective):
    """Sorted, as the jq `unique` this inherited its ordering from produced.

    Asserted on rows() rather than format_row: the ordering is a property of the data,
    and format_row joins whatever it is handed.
    """
    messy = cat.Artifact(name="messy", type=cat.SKILL, groups=("c", "a", "b", "a"), source=CLAUDE)
    listed = listing.rows({**catalog, (cat.SKILL, "messy"): messy}, cat.SKILL, effective, None, None, {})
    by_name = {r["name"]: r for r in listed}
    assert by_name["messy"]["groups"] == ("a", "b", "c")


def test_dependencies_are_dim_and_comma_joined(coloured):
    got = listing.format_row(row("x", dependencies=("alpha", "beta")))
    assert f"{DIM}(needs: alpha, beta){RESET}" in got


def test_suffix_order_is_groups_then_needs(coloured):
    got = listing.format_row(row("x", groups=("g",), dependencies=("d",)))
    assert got.index("[g]") < got.index("(needs: d)")


def test_the_flat_view_carries_no_scope_marker(coloured):
    """The groups suffix already shows `global`, so no extra scope marker here."""
    got = listing.format_row(row("commit", groups=("ai", "global"), **{"global": True}))
    assert "[ai, global]" in got
    assert "(global)" not in got.replace("[ai, global]", "")


def test_the_flat_view_has_a_blind_spot_and_keeps_it(coloured):
    """A skill global only via a dependency has no `global` tag, so the flat view says
    nothing about its scope. Pinned deliberately: the gap came with the template, and the
    grouped view is where scope does show.
    """
    got = listing.format_row(row("jira", groups=("workflow",), **{"global": True}))
    assert "(global)" not in got
    # The grouped view is the place it surfaces.
    grouped_row = listing.format_row(
        row("jira", groups=("workflow",), **{"global": True}), indent="    ", show_groups=False
    )
    assert f"{DIM}(global){RESET}" in grouped_row


def test_provenance_is_appended_last(coloured):
    got = listing.format_row(
        row("context-engineering", groups=("ai",), parent="spec-driven-development")
    )
    assert got.endswith(f"{DIM}(installed for spec-driven-development){RESET}")


# --- the grouped view -------------------------------------------------------


def test_grouped_rows_indent_four_and_drop_the_group_list(coloured):
    """Under a tag heading the group list would be noise, so a bare `(global)` takes its
    place."""
    got = listing.format_row(
        row("agent-audit", groups=("ai", "global"), **{"global": True}),
        indent="    ",
        show_groups=False,
    )
    assert got == f"    {DIM}·{RESET} agent-audit {DIM}(global){RESET}"


def test_grouped_buckets_are_sorted_and_span_tags(catalog, effective):
    listed = listing.rows(catalog, cat.SKILL, effective, None, None, {})
    buckets = listing.grouped(listed)
    tags = [tag for tag, _ in buckets]
    assert tags == sorted(tags)
    assert "ai" in tags and "engineering" in tags
    by_tag = dict(buckets)
    for member in by_tag["ai"]:
        assert "ai" in member["groups"]


# --- ordering ---------------------------------------------------------------


def test_present_artifacts_come_before_never_downloaded_ones(catalog, effective, tmp_path):
    """The walk reads the filesystem then backfills from the registry, which puts the two
    states in separate alphabetical runs rather than one merged list.
    """
    ghost = cat.Artifact(name="aaa-never-fetched", type=cat.SKILL, source=tmp_path / "nope")
    doctored = {**catalog, (cat.SKILL, ghost.name): ghost}
    listed = listing.rows(doctored, cat.SKILL, effective, None, None, {})

    states = [r["state"] for r in listed]
    assert states[-1] == listing.MISSING, "the missing one sorts first by name but last by state"
    assert listing.MISSING not in states[:-1]


# --- headers ----------------------------------------------------------------


@pytest.mark.parametrize(
    "kind,expected",
    [
        (cat.SKILL, "🧩 Available skills:"),
        (cat.AGENT, "🤖 Available agents:"),
        (cat.PLUGIN, "🔌 Available plugins:"),
    ],
)
def test_headers_carry_the_topic_emoji_and_the_rows_do_not(kind, expected):
    """One emoji per listing, on the heading, per the shared output vocabulary."""
    assert listing.HEADER[kind] == expected


def test_only_the_headings_carry_an_emoji(coloured):
    """A row marker has to be single-width or the suffix columns stop lining up.

    Both emoji here are two columns wide, which is why the vocabulary keeps them off
    every line kind that is indented under something else.
    """
    for header in (*listing.HEADER.values(), listing.GROUPS_HEADER):
        assert header.split()[0] not in ("✓", "·", "↓")
    assert "\U0001f9e9" not in listing.format_row(row("x", state=listing.LINKED))


# --- a real run through the shim --------------------------------------------
#
# Everything above renders one row in-process. These drive the installed command end to
# end, so the registry, the scope resolution and the printing all have to agree before a
# row comes out looking like the literals above.


def run_kit(argv, cwd, env):
    return subprocess.run(
        [sys.executable, str(SHIM), *argv], cwd=str(cwd), env=env, capture_output=True, text=True
    ).stdout


@pytest.fixture
def listing_run(tmp_path):
    """A project with one skill linked, and an env the shim accepts.

    Colour is forced on because the assertions are literals with escape codes in them,
    and a subprocess under pytest writes to a pipe.
    """
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    project = tmp_path / "project"
    project.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=project, check=True)

    skills = project / ".claude" / "skills"
    skills.mkdir(parents=True)
    (skills / "coderabbit").symlink_to(CLAUDE / "skills" / "coderabbit")

    env = {
        **os.environ,
        "HOME": str(home),
        "DOTFILES_DIR": str(REPO),
        "TERM": "xterm-256color",
        "FORCE_COLOR": "1",
    }
    env.pop("NO_COLOR", None)
    env.pop("XDG_CONFIG_HOME", None)
    return project, env


def test_a_real_run_prints_the_heading_then_the_rows(listing_run):
    project, env = listing_run
    out = run_kit(["list", "--type", "skill"], project, env).splitlines()
    assert out[0] == f"{BOLD}🧩 Available skills:{RESET}"
    linked = f"  {GREEN}✓{RESET} coderabbit {GREEN}(linked){RESET}"
    assert any(line.startswith(linked) for line in out)
    assert f"  {DIM}·{RESET} astro {CYAN}[astro, engineering, frontend]{RESET}" in out


def test_a_real_run_colours_nothing_when_stdout_is_a_pipe(listing_run):
    """Which is why the fixture forces colour on rather than assuming a terminal."""
    project, env = listing_run
    plain = {**env}
    plain.pop("FORCE_COLOR")
    out = run_kit(["list", "--type", "skill"], project, plain)
    assert "Available skills:" in out
    assert "\x1b" not in out


def test_the_count_summary_closes_the_listing(listing_run):
    """One `done` line per run, below the row block, so it adds a total without
    disturbing the template above."""
    project, env = listing_run
    out = run_kit(["list", "--type", "skill"], project, env).splitlines()
    assert out[-1].startswith("✨ ")
    assert "skills, 1 installed" in out[-1]


def test_the_grouped_view_indents_members_under_a_tag(listing_run):
    project, env = listing_run
    out = run_kit(["list", "--type", "skill", "--group"], project, env).splitlines()
    assert out[0] == f"{BOLD}{listing.GROUPS_HEADER}{RESET}"
    assert f"  {CYAN}ai:{RESET}" in out
    assert f"    {DIM}·{RESET} agent-audit {DIM}(global){RESET}" in out


def test_a_tag_filter_narrows_the_flat_view(listing_run):
    """`--group <tag>` filters; a bare `--group` buckets. One flag, two shapes, so the
    valued form must not turn the listing into the grouped view."""
    project, env = listing_run
    filtered = run_kit(["list", "--type", "skill", "--group", "global"], project, env)
    assert "Available skills:" in filtered
    assert "tagged 'global'" in filtered
    assert "Available groups:" not in filtered
