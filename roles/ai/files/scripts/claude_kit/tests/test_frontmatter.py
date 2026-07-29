"""The stdlib frontmatter scanner behind G8.

The scanner exists so `doctor` validates frontmatter on a machine with only
python3, where it used to report that it had not run. Scanning is not parsing, so
the contract is one-directional and this module is where it is held: **whatever
the scanner calls malformed, PyYAML must also reject.** The reverse is not
required, and CASES records exactly which real errors it lets through.

PyYAML is the oracle rather than the implementation, which is the whole point: it
is a test dependency, so it may be present here and absent in the tool.
"""

import pytest
import yaml

from claude_kit import frontmatter
from conftest import CLAUDE

# (label, block, caught) — `caught` is whether the scanner must report it. Every
# case is run past PyYAML too, so a False here means "PyYAML rejects this and we
# knowingly do not", and a True on valid YAML fails the agreement test.
CASES = [
    ("a flat mapping", "name: x\ndescription: fine\n", False),
    ("a colon with no space", "name: x\nurl: http://example.test/y\n", False),
    ("a multi-line plain value", "name: x\ndescription: one\n  two\n  three\n", False),
    ("a folded value holding a colon", "name: x\ndescription: >\n  fine: even here\n", False),
    ("a literal value holding a colon", "name: x\ndescription: |\n  fine: even here\n", False),
    ("a quoted value holding a colon", 'name: x\ndescription: "fine: here"\n', False),
    ("a nested mapping", 'name: x\nmetadata:\n  author: a\n  version: "1.0"\n', False),
    ("a flow sequence", "name: x\ntools: [a, b]\n", False),
    ("an empty value", "name: x\ndescription:\n", False),
    ("a comment line", "name: x\n# a note\ndescription: fine\n", False),
    ("a trailing comment holding a colon", "name: x\ndescription: fine # note: here\n", False),
    ("a continuation whose comment holds a colon", "name: x\ndescription: one\n  two # note: here\n", False),
    ("an anchored value", "name: x\ndescription: &a fine\n", False),
    ("a tagged value", "name: x\ndescription: !!str fine\n", False),
    ("a value opening with a dash", "name: x\ndescription: -fine\n", False),
    ("an em dash in a value", "name: x\ndescription: a design seat — not an implementer\n", False),
    ("a tool allowlist holding colons", "name: x\nallowed-tools: Bash(npm:*) Read Edit\n", False),
    # What the scanner must catch: every shape of the unquoted colon, which is the
    # failure that silently stops an artifact loading.
    ("an unquoted colon in a value", "name: x\ndescription: pick one: this or that\n", True),
    ("a value ending in a colon", "name: x\ndescription: pick one:\n", True),
    ("two unquoted colons", "name: x\ndescription: a: b: c\n", True),
    ("an unquoted colon under a hash", "name: x\ndescription: a#b: c\n", True),
    ("an unquoted colon in a continuation", "name: x\ndescription: one\n  two: three\n", True),
    ("a continuation ending in a colon", "name: x\ndescription: one\n  two:\n", True),
    ("a tab for indentation", "name: x\ndescription: one\n\ttwo\n", True),
    ("a line that is not a mapping entry", "name: x\nstray line\n", True),
    ("a value opening with an at sign", "name: x\ndescription: @fine\n", True),
    ("a value opening with a backtick", "name: x\ndescription: `fine`\n", True),
    ("a value opening with a percent", "name: x\ndescription: %fine\n", True),
    ("a value opening with a comma", "name: x\ndescription: ,fine\n", True),
    # Known gaps. Each is a real YAML error the scanner does not model, listed here
    # so the subset is a decision on the record rather than an accident.
    ("a value opening with a question mark", "name: x\ndescription: ? fine\n", False),
    ("an unterminated quote", 'name: x\ndescription: "one\n', False),
    ("an undefined alias", "name: x\ndescription: *nowhere\n", False),
    ("a colon nested under another key", "name: x\nmetadata:\n  note: a: b\n", False),
    ("a bare dash as a value", "name: x\ndescription: -\n", False),
]

IDS = [label for label, _, _ in CASES]


def rejects(text):
    try:
        yaml.safe_load(text)
    except Exception:
        return True
    return False


def scanned(block):
    """The scanner's verdict on a block: (keys, malformed)."""
    try:
        return frontmatter.keys(f"---\n{block}---\n body\n"), False
    except frontmatter.Malformed:
        return None, True


# --- the contract -----------------------------------------------------------


@pytest.mark.parametrize("label,block,caught", CASES, ids=IDS)
def test_the_scanner_verdict_is_the_one_the_table_records(label, block, caught):
    """Both directions at once: what must be caught is, and what must not be is not.

    A false problem is the expensive failure here. Reporting a valid artifact as
    broken is how this check once produced 69 findings on a clean repo, which
    teaches the reader to skip the whole report.
    """
    _, malformed = scanned(block)
    assert malformed is caught


@pytest.mark.parametrize("label,block,caught", CASES, ids=IDS)
def test_the_table_agrees_with_pyyaml(label, block, caught):
    """Guards the table itself, which is the other half of the contract.

    Marking a case as caught asserts it is genuinely invalid YAML; with this the
    pair above becomes the one-directional claim the scanner actually makes.
    """
    if caught:
        assert rejects(block), f"{label}: expected to be caught, but it is valid YAML"


# --- the message ------------------------------------------------------------


def test_a_finding_names_the_line():
    """The detail reaches the user through doctor, so it has to be actionable."""
    with pytest.raises(frontmatter.Malformed) as excinfo:
        frontmatter.keys("---\nname: x\ndescription: fine\nsummary: pick one: this\n---\nbody\n")
    assert "line 3" in str(excinfo.value)
    assert "': '" in str(excinfo.value)


# --- what keys() returns ----------------------------------------------------


def test_no_opening_delimiter_means_no_block():
    assert frontmatter.keys("just prose\n") is None


def test_an_unclosed_block_means_no_block():
    """A file opening with --- and never closing has no frontmatter, not a broken one."""
    assert frontmatter.keys("---\nname: x\nbody with no closing delimiter\n") is None


def test_the_top_level_keys_are_returned_in_order():
    keys = frontmatter.keys("---\nname: x\ndescription: fine\nmodel: opus\n---\nbody\n")
    assert keys == ["name", "description", "model"]


def test_nested_keys_are_not_returned():
    """`name` has to mean the top-level one, or a nested `name` would satisfy G8."""
    keys = frontmatter.keys("---\nmetadata:\n  name: nested\n---\nbody\n")
    assert keys == ["metadata"]


def test_a_top_level_sequence_yields_no_keys():
    """Valid YAML, but not a mapping. G8's own `name` check is what should speak."""
    assert frontmatter.keys("---\n- a\n- b\n---\nbody\n") == []


def test_an_empty_block_yields_no_keys():
    assert frontmatter.keys("---\n\n---\nbody\n") == []


def test_back_to_back_delimiters_are_not_a_block():
    """`---\\n---` is a horizontal rule as readily as an empty block, and the old
    PyYAML path read it the same way. Pinned so the reading does not drift."""
    assert frontmatter.keys("---\n---\nbody\n") is None


def test_a_quoted_key_is_read_rather_than_refused():
    """Nothing here writes one, so the point is only that it is not a false problem."""
    assert frontmatter.keys('---\n"name": x\n---\nbody\n') == ["name"]


# --- the real artifacts -----------------------------------------------------


def artifact_files():
    """Every frontmatter-carrying file under files/claude, plugins included.

    Wider than G8's own catalog on purpose: plugin-bundled skills and agents are
    not registry entries, so nothing else would ever scan them.
    """
    agents = [p for p in CLAUDE.rglob("*.md") if p.parent.name == "agents"]
    return sorted({*CLAUDE.rglob("SKILL.md"), *agents})


def test_every_real_artifact_ships_a_block_the_scanner_accepts():
    """The corpus is the strongest evidence there is against a false problem.

    Over a hundred hand-written blocks, none of which the scanner may object to
    unless PyYAML objects first.
    """
    offenders = []
    for path in artifact_files():
        block = frontmatter.block(path.read_text())
        if block is None:
            offenders.append(f"{path.relative_to(CLAUDE)}: no frontmatter block")
            continue
        _, malformed = scanned(f"{block}\n")
        if malformed and not rejects(block):
            offenders.append(f"{path.relative_to(CLAUDE)}: called malformed, but PyYAML accepts it")
        elif not malformed and rejects(block):
            offenders.append(f"{path.relative_to(CLAUDE)}: PyYAML rejects this and the scanner missed it")
    assert offenders == [], "\n".join(offenders)


def test_every_real_artifact_declares_a_name():
    nameless = [
        str(path.relative_to(CLAUDE))
        for path in artifact_files()
        if "name" not in (frontmatter.keys(path.read_text()) or [])
    ]
    assert nameless == []
