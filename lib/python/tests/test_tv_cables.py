"""The Television claude cables read claude-kit, and derive nothing themselves.

There is no fish test suite, and that is how the bug this file guards against shipped.
`_tv_claude_list` used to rebuild claude-kit's whole answer in jq and fish: the
catalogue, the dependency_only hiding, the effective global set, and link status. Four
of those five had a python counterpart under test; the fifth, what counts as a project,
had none, and the two implementations disagreed. claude-kit takes the cwd, the cable
took `git rev-parse --show-toplevel`, so in a directory that is not a git repo the cable
found no project at all and rendered every non-global artifact `[available]` however
many links were on disk. Enter then refused, because claude-kit could see them.

So the invariant is not "the anchoring rule matches" - a matching second copy is still a
second copy. It is that **the cable holds no copy**: no project rule, no catalogue, no
scope predicate. Text assertions over the fish sources, because that is what a suite in
python can hold a fish function to.
"""

import re
from pathlib import Path

import pytest
from dotkit.testing import FISH_FUNCTIONS, REPO

# The two functions the cables call, and the whole of what fish still owns here.
CABLES = ("_tv_claude_list.fish", "_tv_claude_toggle.fish")

# Deleted when the cable stopped deriving: three scope helpers and the jq prelude that
# fed them. Every one had a python counterpart that was already the authority.
RETIRED = (
    "_claude_scope_target",
    "_claude_scope_is_global",
    "_claude_scope_global_skills",
    "_claude_skill_jqlib",
)

# What a second derivation would have to touch. The registries and the plugin manifests
# are the catalogue's own inputs; reaching for one here is rebuilding catalog.py.
DERIVATIONS = (
    "rev-parse",
    "skill-registry.json",
    "agent-registry.json",
    ".claude-plugin",
    "DOTFILES_DIR",
)


def source(name):
    return (FISH_FUNCTIONS / name).read_text()


@pytest.mark.parametrize("name", CABLES)
@pytest.mark.parametrize("forbidden", DERIVATIONS)
def test_a_cable_derives_nothing_of_its_own(name, forbidden):
    """Not even a *correct* copy of the project rule, which is the point.

    `rev-parse` is the one that actually broke. The rest are the inputs a catalogue
    would need, so they are how the next attempt would look.
    """
    assert forbidden not in source(name), (
        f"{name} reaches for {forbidden!r}. Every fact on a cable row comes from "
        f"`claude-kit list --json`; deriving one here is what made the picker and "
        f"claude-kit disagree about whether a skill was installed."
    )


def test_the_listing_cable_reads_claude_kit():
    assert re.search(r"claude-kit list --type \$type --json", source("_tv_claude_list.fish"))


def test_the_toggle_reads_its_direction_from_claude_kit():
    """Which way to toggle, and whether --global applies, are claude-kit's answers.

    Reconstructing either from a tag would put the scope rule back in fish, in the one
    place a wrong answer writes to disk instead of merely rendering oddly.
    """
    body = source("_tv_claude_toggle.fish")
    assert "claude-kit list --type $type --json" in body
    assert "claude-kit $action $name --type $type $want_global" in body


def sources():
    """Every file in the repo that could name a fish function, path-ordered."""
    for tree in (REPO / "roles", REPO / "lib", REPO / "docs" / "internals", REPO / "CLAUDE.md"):
        paths = [tree] if tree.is_file() else sorted(tree.rglob("*"))
        for path in paths:
            if not path.is_file() or path.suffix not in (".fish", ".py", ".md", ".yml", ".toml"):
                continue
            # This file names every retired helper, as the record of what went and why.
            if path.name == Path(__file__).name:
                continue
            yield path


@pytest.mark.parametrize("retired", RETIRED)
def test_a_retired_helper_is_gone_and_unreferenced(retired):
    """Including from prose: a doc naming one of these is an instruction to keep a
    duplicate in sync, and the duplicate no longer exists."""
    assert not (FISH_FUNCTIONS / f"{retired}.fish").exists()
    offenders = [str(p.relative_to(REPO)) for p in sources() if retired in p.read_text()]
    assert offenders == [], f"{retired} is gone but still named in: {', '.join(offenders)}"


def test_the_retired_family_is_unreferenced_by_its_prefix_too():
    """`_claude_scope_*` outlived the exact names in two CLAUDE.md sentences, which the
    per-name check above cannot see. The family is empty now, so the prefix is the
    assertion: any mention is a reader being sent to a function that is not there.
    """
    offenders = [str(p.relative_to(REPO)) for p in sources() if "_claude_scope" in p.read_text()]
    assert offenders == [], f"the _claude_scope_* family is gone but named in: {offenders}"
