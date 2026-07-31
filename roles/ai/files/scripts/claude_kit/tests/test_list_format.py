"""`claude-kit list` renders exactly like `claude-skill list`.

The strongest form of this is a differential test: run both against the same project
and compare the bytes. That is what test_matches_claude_skill_byte_for_byte does, so a
drift in either implementation fails rather than being noticed by eye.

The rest pin individual pieces of the template so a failure says which part moved.
"""

import os
import subprocess
import sys

import pytest

from claude_kit import catalog as cat
from claude_kit import colors, scope
from claude_kit.commands import listing
from dotkit.testing import CLAUDE, FISH_FUNCTIONS, REPO
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

    claude-skill decides the same way now that its palette comes from `_ui color`; it
    used to emit codes unconditionally, because a bare set_color does. Which is why the
    differential tests below force colour on rather than assuming a terminal.
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
    """claude-skill dims "↓ name (not downloaded)" as one unit, not just the glyph."""
    got = listing.format_row(row("never-fetched", state=listing.MISSING))
    assert got == f"  {DIM}↓ never-fetched (not downloaded){RESET}"


# --- suffixes ---------------------------------------------------------------


def test_groups_are_cyan_bracketed_and_comma_joined(coloured):
    got = listing.format_row(row("x", groups=("engineering", "frontend")))
    assert f"{CYAN}[engineering, frontend]{RESET}" in got


def test_groups_are_sorted_and_deduped(catalog, effective):
    """jq's `unique` sorts and dedupes, so claude-skill prints them sorted.

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
    """claude-skill prints none, so neither do we.

    Its comment reads: the groups suffix already shows `global`, so no extra scope
    marker here.
    """
    got = listing.format_row(row("commit", groups=("ai", "global"), **{"global": True}))
    assert "[ai, global]" in got
    assert "(global)" not in got.replace("[ai, global]", "")


def test_the_flat_view_inherits_claude_skills_blind_spot(coloured):
    """A skill global only via a dependency has no `global` tag, so the flat view says
    nothing about its scope. Pinned deliberately: matching claude-skill's template means
    matching this gap too, and the grouped view is where scope does show.
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
    """Under a tag heading the group list would be noise, so claude-skill prints a bare
    `(global)` there instead."""
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
    """claude-skill walks the filesystem then backfills from the registry, which puts
    the two states in separate alphabetical runs rather than one merged list.
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
def test_headers_follow_claude_skills_wording(kind, expected):
    """Topic emoji on the heading, and only there.

    The byte-for-byte tests below hold claude-skill.fish and claude-agent.fish to the
    same strings, so a heading cannot be changed on one side alone.
    """
    assert listing.HEADER[kind] == expected


def test_only_the_headings_carry_an_emoji(coloured):
    """A row marker has to be single-width or the suffix columns stop lining up.

    Both emoji here are two columns wide, which is why the vocabulary keeps them off
    every line kind that is indented under something else.
    """
    for header in (*listing.HEADER.values(), listing.GROUPS_HEADER):
        assert header.split()[0] not in ("✓", "·", "↓")
    assert "\U0001f9e9" not in listing.format_row(row("x", state=listing.LINKED))


# --- the differential test --------------------------------------------------


def run_kit(argv, cwd, env):
    return subprocess.run(
        [sys.executable, str(SHIM), *argv], cwd=str(cwd), env=env, capture_output=True, text=True
    ).stdout


def run_fish(command, cwd, env):
    preamble = f"set -g fish_function_path {FISH_FUNCTIONS} $fish_function_path\n"
    return subprocess.run(
        ["fish", "--no-config", "-c", preamble + command],
        cwd=str(cwd), env=env, capture_output=True, text=True,
    ).stdout


@pytest.fixture
def both(tmp_path):
    """A project with one skill linked, plus an env both tools accept."""
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


def test_matches_claude_skill_byte_for_byte(both):
    """The real check: identical bytes, escape codes included.

    claude-kit adds `(installed for <parent>)` where it has provenance, which
    claude-skill cannot know, so rows carrying that suffix are compared with it
    stripped. Everything else must match exactly.
    """
    project, env = both
    mine = run_kit(["list", "--type", "skill"], project, env)
    theirs = run_fish("claude-skill list", project, env)

    def rows_only(text):
        """The header and row block, dropping our trailing count summary.

        Also strips `(installed for <parent>)`, which claude-kit knows from provenance
        and claude-skill cannot. Everything else must match byte for byte.
        """
        lines = []
        for line in text.splitlines():
            if not line.strip():
                break
            lines.append(line.split(f" {DIM}(installed for ")[0])
        return lines

    assert rows_only(mine) == rows_only(theirs)


def test_the_count_summary_is_a_claude_kit_addition(both):
    """It sits below the row block, so it adds information without altering the
    template. Asserted so the differential test above cannot quietly start ignoring a
    real divergence."""
    project, env = both
    mine = run_kit(["list", "--type", "skill"], project, env)
    assert "skills, 1 installed" in mine
    assert "installed" not in run_fish("claude-skill list", project, env).splitlines()[-1]


def test_the_grouped_view_matches_byte_for_byte(both):
    project, env = both
    mine = run_kit(["list", "--type", "skill", "--group"], project, env)
    theirs = run_fish("claude-skill list --group", project, env)
    assert mine.splitlines() == theirs.splitlines()


def test_a_tag_filter_is_a_claude_kit_addition(both):
    """claude-skill's --group takes no value, so `--group <tag>` is ours alone. It must
    not disturb the shared bare-flag behaviour."""
    project, env = both
    filtered = run_kit(["list", "--type", "skill", "--group", "global"], project, env)
    assert "Available skills:" in filtered
    assert "tagged 'global'" in filtered
    assert "Available groups:" not in filtered
