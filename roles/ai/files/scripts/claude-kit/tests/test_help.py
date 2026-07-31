"""The grouped help: every command sits in exactly one family.

`claude-kit -h` splits the commands by what they touch, because that is what
decides whether `--global` is even a question. argparse takes one subparsers
action, so the listing is an epilog built from COMMANDS and FAMILIES rather than
argparse's own. The risk that buys is a command reaching the CLI without reaching
the listing, which is what these assert against.

The colour tests guard the other risk: the help is painted in the commands' palette,
and every hook does it after argparse has measured and padded the text. A paint that
lands too early does not fail loudly, it quietly skews a column, so the tests compare
the painted help against the plain one rather than eyeballing the escapes.
"""

import io
import sys

import pytest

from claude_kit import errors
from dotkit import colors
from claude_kit.cli import COMMANDS, FAMILIES, SCOPE, build_parser
from dotkit.testing import force_colour
from kit_helpers import subparsers

GROUPED = [name for _, names in FAMILIES for name in names]


def test_every_command_is_grouped_exactly_once():
    """A new subcommand missing from FAMILIES vanishes from -h. Fail here instead."""
    assert sorted(GROUPED) == sorted(subparsers())
    assert len(GROUPED) == len(set(GROUPED)), "a command appears in two families"


def test_every_grouped_command_has_a_one_liner_and_a_scope():
    for name in GROUPED:
        assert COMMANDS.get(name), f"{name} has no COMMANDS entry"
        assert SCOPE.get(name), f"{name} has no SCOPE entry"


def test_every_subcommand_describes_itself():
    """Omitting `help` suppresses argparse's listing; description is what replaces it."""
    for name, parser in subparsers().items():
        assert parser.description, f"{name} --help would show no prose"
        assert COMMANDS[name] in parser.description
        assert SCOPE[name] in parser.description


def test_the_help_shows_the_families_and_no_flat_listing(kit):
    result = kit("--help")
    assert result.returncode == errors.OK
    for title, names in FAMILIES:
        assert title in result.stdout
        for name in names:
            assert name in result.stdout
    assert "{list,add" not in result.stdout, "argparse's flat listing is back, alongside the epilog"


def test_an_unknown_command_still_names_the_valid_ones(kit):
    """metavar hides the choices from the usage line, but not from the refusal."""
    result = kit("bogus")
    assert result.returncode == errors.USAGE
    for name in COMMANDS:
        assert name in result.stderr


# --- colour -----------------------------------------------------------------


def _both_renders(monkeypatch, render):
    force_colour(monkeypatch, True)
    painted = render()
    force_colour(monkeypatch, False)
    return painted, render()


def _assert_only_escapes_differ(monkeypatch, render):
    """Painted and plain must differ, and differ only in escapes.

    Both halves matter. Without the first, a render that lost its colour entirely
    passes: `formatter_class=Help` can be dropped from every subparser and the
    stripped-equals-plain half still holds, which is the one regression the
    per-command version of this test exists to catch.
    """
    painted, plain_text = _both_renders(monkeypatch, render)
    assert painted != plain_text, "FORCE_COLOR produced no colour at all"
    assert colors.strip(painted) == plain_text


def test_colour_changes_nothing_but_the_escapes(monkeypatch):
    """The layout assertion. Every hook paints text argparse has already measured, so
    stripping the escapes must give back the plain help byte for byte. Painting an
    invocation or a column before argparse pads it skews the block instead."""
    _assert_only_escapes_differ(monkeypatch, lambda: build_parser().format_help())


@pytest.mark.parametrize("command", sorted(COMMANDS))
def test_colour_changes_nothing_but_the_escapes_per_command(monkeypatch, command):
    _assert_only_escapes_differ(monkeypatch, lambda: subparsers()[command].format_help())


def test_the_palette_is_the_one_the_commands_use(coloured):
    """Bold for a heading, cyan for a name, dim for the aside: the same three roles
    they play in `list` and `outdated`."""
    text = build_parser().format_help()
    for title, _ in FAMILIES:
        assert colors.paint(f"{title}:", "bold") in text
    for name in COMMANDS:
        assert colors.paint(name, "cyan") in text
    assert colors.paint("options", "bold") in text
    assert text.rstrip().endswith(colors.RESET), "the closing hint should be dimmed"


def test_a_subcommand_prog_never_carries_escape_codes(coloured):
    """add_subparsers derives each prog from the parent's formatted usage, so painting
    that render would bake escapes into the prog and skew the width its usage wraps on.
    The prefix check in _format_usage is what prevents it; this is that check's test."""
    for name, parser in subparsers().items():
        assert "\x1b" not in parser.prog, f"{name}'s prog carries colour"


def test_a_refusal_to_a_redirected_stderr_carries_no_escapes(monkeypatch, capsys):
    """A refusal prints usage to stderr, but the formatter that painted it defaults to
    stdout: it is handed the text with no idea where the parser will send it. So with a
    terminal on stdout and a file on stderr, `claude-kit bogus 2>log` used to write
    escape codes into the log. colors.for_stream is what decides per destination.
    """
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)

    class Terminal(io.StringIO):
        def isatty(self):
            return True

    monkeypatch.setattr(sys, "stdout", Terminal())
    with pytest.raises(SystemExit):
        build_parser().parse_args(["bogus"])

    # capsys's stderr is not a tty, which is exactly the redirected case.
    assert "\x1b" not in capsys.readouterr().err


def test_the_refusal_marker_is_magenta(kit):
    result = kit("bogus", extra_env={"FORCE_COLOR": "1"})
    assert result.returncode == errors.USAGE
    assert colors.CODES["magenta"] + "✗" in result.stderr


def test_nothing_is_painted_when_the_output_is_piped(kit, plain):
    """The default for a pipe: colors.enabled is false, so a harness reading the help
    gets plain text without asking."""
    result = kit("--help")
    assert "\x1b" not in result.stdout
