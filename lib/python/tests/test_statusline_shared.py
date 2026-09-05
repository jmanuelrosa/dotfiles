"""One status line vocabulary, five readers, and nothing pinning them but this file.

`roles/ai/files/statusline.json` holds the values Claude Code's status line and pi's footer both
render: the wrap-up threshold, the gauge cells, the lockfile table and the glyphs. Before it, each
value was typed into both harnesses and the threshold into three files, which is how a nudge that
fires at one percentage and a gauge that marks another get shipped together.

Nothing here checks that the two renderings look alike, because they should not: the colour models
differ on purpose (truecolor Solarized stops against a user-authored pi theme) and pi's token
format matches pi's own footer rather than Claude's. Those divergences have their own tests.

What this checks is that the sharing is real rather than decorative. Two ways it stops being real,
and both are silent:

- a reader goes back to a literal, which renders correctly the day it is written and drifts the
  first time the shared value changes;
- the file loses a key a reader asks for by name, which renders as a missing glyph or a missing
  marker rather than as an error, because every reader here degrades instead of failing.

The second is why the last group runs `statusline.sh` for real, with the vocabulary present and
with it hidden. The fallback is the whole reason reading the file is safe to do on a path that
runs every turn, and nothing exercised that script at all before this.
"""

import json
import os
import re
import subprocess
import sys

import pytest
from dotkit.testing import CLAUDE, PI_EXTENSIONS, REPO

VOCABULARY = REPO / "roles/ai/files/statusline.json"
STATUSLINE = CLAUDE / "statusline.sh"
NUDGE = CLAUDE / "hooks/context-nudge.sh"

# Every file that reads the vocabulary, and the relative hop each one makes to reach it. The hop
# is part of the contract: all five are reached through a symlink into this checkout, so each
# resolves its own realpath first and a wrong number of `..` is a file that silently is not there.
READERS = {
    STATUSLINE: 1,
    NUDGE: 2,
    PI_EXTENSIONS / "statusline.ts": 2,
    PI_EXTENSIONS / "velocity.ts": 2,
    PI_EXTENSIONS / "guardrails.ts": 2,
}

# What each reader asks the vocabulary for by name. A key dropped from the file is a glyph that
# stops rendering, which is exactly the kind of thing nobody notices in a footer.
REQUIRED = {
    "handoffPct": (STATUSLINE, NUDGE, PI_EXTENSIONS / "statusline.ts"),
    "bar": (STATUSLINE, PI_EXTENSIONS / "statusline.ts"),
    "packageManagers": (STATUSLINE, PI_EXTENSIONS / "statusline.ts"),
}


@pytest.fixture(scope="module")
def vocab():
    return json.loads(VOCABULARY.read_text())


def test_the_vocabulary_parses_and_carries_every_section(vocab):
    for key in ("handoffPct", "bar", "glyphs", "labels", "packageManagers"):
        assert key in vocab, f"statusline.json lost {key}"
    assert isinstance(vocab["handoffPct"], int) and 0 < vocab["handoffPct"] < 100
    assert set(vocab["bar"]) == {"width", "filled", "empty"}
    assert vocab["bar"]["width"] >= 2, "a gauge narrower than two cells cannot show a ramp"


def test_the_glyphs_and_labels_are_non_empty_strings(vocab):
    """An empty string renders as a missing glyph rather than as an error, so the file is the
    only place that can catch one."""
    for section in ("glyphs", "labels"):
        for name, value in vocab[section].items():
            assert isinstance(value, str) and value, f"{section}.{name} is empty"


def test_the_lockfile_table_keeps_its_order(vocab):
    """Order is the content: specific before npm is what makes a bun repo carrying a
    package-lock.json read as bun. An object keyed by lockfile would lose it, and so would a
    reader that sorted the list."""
    names = [entry["name"] for entry in vocab["packageManagers"]]
    lockfiles = [entry["lockfile"] for entry in vocab["packageManagers"]]
    assert len(set(lockfiles)) == len(lockfiles), "a lockfile appears twice"
    assert names.index("bun") < names.index("npm")
    assert names.index("pnpm") < names.index("npm")
    assert names.index("yarn") < names.index("npm")


@pytest.mark.parametrize("reader", READERS)
def test_every_reader_resolves_its_own_symlink(reader):
    """All five are reached through a symlink the ai role writes into ~/.claude or ~/.pi, so the
    vocabulary is a sibling of the link's target and not of the link. Resolving `__file__` or
    `import.meta.url` without realpath finds nothing, and finding nothing is silent here."""
    source = reader.read_text()
    assert "statusline.json" in source, f"{reader.name} no longer reads the vocabulary"
    assert "realpath" in source.lower(), (
        f"{reader.name} reaches the vocabulary without resolving its symlink first"
    )


@pytest.mark.parametrize("reader,hops", READERS.items())
def test_every_reader_hops_the_right_number_of_directories(reader, hops):
    """The literal `..` count, checked against where the file actually sits. A reader one level
    off degrades to no glyphs and no threshold, which looks like a theme problem."""
    depth = len(reader.parent.relative_to(VOCABULARY.parent).parts)
    assert depth == hops, f"{reader.name} sits {depth} levels below the vocabulary, not {hops}"
    # The `..` hops written immediately before the filename, which is the whole path expression
    # in all five readers.
    written = reader.read_text().split('"statusline.json"')[0][-240:].count('".."')
    assert written == hops, (
        f"{reader.name} climbs {written} directories to reach a vocabulary {hops} above it"
    )


@pytest.mark.parametrize("key,readers", REQUIRED.items())
def test_the_file_carries_what_each_reader_asks_for(key, readers, vocab):
    assert key in vocab
    for reader in readers:
        assert key in reader.read_text(), f"{reader.name} no longer asks for {key}"


def test_no_reader_hardcodes_a_shared_value(vocab):
    """The assertion the whole change rests on. A literal here renders correctly the day it is
    written, and is the drift this file exists to prevent the moment the shared value changes.

    Prose is exempt: several of these files name the glyph they render in their header comment,
    and a comment cannot drift into a different rendering.

    One line of code is exempt too, and deliberately: statusline.sh's last-resort
    `\N{ROBOT FACE} Claude Code`, printed when every segment came back empty. That line renders
    when nothing else could, the vocabulary included, so taking its glyph from the file would make
    the fallback depend on the thing it is falling back from.
    """
    last_resort = 'or "\N{ROBOT FACE} Claude Code"'
    marks = set(vocab["glyphs"].values()) | {vocab["bar"]["filled"], vocab["bar"]["empty"]}
    for reader in READERS:
        code = strip_prose(reader).replace(last_resort, "")
        for mark in marks:
            assert mark not in code, f"{reader.name} hardcodes {mark!r}; it belongs to the file"
        assert not re.search(rf"=\s*{vocab['handoffPct']}\b", code), (
            f"{reader.name} hardcodes the handoff threshold again"
        )
        for entry in vocab["packageManagers"]:
            assert entry["lockfile"] not in code, (
                f"{reader.name} hardcodes {entry['lockfile']}; the table belongs to the file"
            )


def strip_prose(reader):
    """A reader's code with its docstrings and comments removed.

    Both languages, because the readers are split across them: python docstrings and `#` lines,
    JSDoc blocks and `//` lines. Crude on purpose, since a false negative here costs a missed
    literal and a false positive costs a test nobody can satisfy.
    """
    text = reader.read_text()
    text = re.sub(r'"""(?:.|\n)*?"""', "", text)
    text = re.sub(r"/\*(?:.|\n)*?\*/", "", text)
    text = re.sub(r"^\s*(#|//).*$", "", text, flags=re.M)
    return text


# --- the status line, executed --------------------------------------------------

PAYLOAD = {
    "session_id": "96371f64-022a-4060-83c1-441aa230c0dd",
    "version": "2.1.90",
    "model": {"display_name": "Opus 5"},
    "workspace": {"current_dir": str(REPO), "repo": {"name": "dotfiles"}},
    "context_window": {
        "used_percentage": 36.4,
        "context_window_size": 200_000,
        "total_input_tokens": 70_000,
        "total_output_tokens": 3_000,
    },
    "cost": {"total_lines_added": 120, "total_lines_removed": 30},
}


def run_statusline(tmp_path, vocabulary=True):
    """The status line, run the way Claude Code runs it, with TMPDIR pointed somewhere harmless.

    `vocabulary=False` copies the script out of the checkout so its realpath lands where no
    statusline.json sits, which is the only honest way to test the missing-file path: moving the
    real file aside would break every other session on this machine while the test ran.
    """
    script = STATUSLINE
    if not vocabulary:
        script = tmp_path / "statusline.sh"
        script.write_text(STATUSLINE.read_text())
    done = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(PAYLOAD),
        capture_output=True,
        text=True,
        env={**os.environ, "TMPDIR": str(tmp_path)},
        check=False,
    )
    assert done.returncode == 0, done.stderr
    return done.stdout


def test_the_status_line_renders_the_shared_vocabulary(tmp_path, vocab):
    out = run_statusline(tmp_path)
    assert vocab["glyphs"]["repo"] in out
    assert vocab["labels"]["context"] in out
    assert vocab["bar"]["filled"] in out
    # The payload is over the threshold on purpose, so the marker is part of what is asserted.
    assert PAYLOAD["context_window"]["used_percentage"] > vocab["handoffPct"]
    assert vocab["labels"]["handoff"] in out


def test_the_status_line_survives_a_missing_vocabulary(tmp_path, vocab):
    """It runs on every turn and its output is Claude's chrome, so it has to print something and
    exit 0 whatever it cannot read. The glyphs and the gauge go, the readings stay."""
    out = run_statusline(tmp_path, vocabulary=False)
    assert out.strip(), "a missing vocabulary emptied the status line"
    assert "(36%)" in out, "the reading itself should survive; only its decoration is shared"
    assert vocab["glyphs"]["repo"] not in out
    assert vocab["bar"]["filled"] not in out
