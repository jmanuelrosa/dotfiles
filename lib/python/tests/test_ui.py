"""The fish half of the line vocabulary, and the promise that both halves agree.

ui.py and _ui.fish are one style expressed twice, so the test that matters is the
differential one at the bottom: the same kind and the same text, rendered by each,
must come out as the same bytes. The python half on its own is tested in the dotkit
repository it is vendored from.
"""

import os
import subprocess
import sys

import pytest
from dotkit import ui
from dotkit.testing import FISH_FUNCTIONS

RESET = "\x1b[m"
GREEN = "\x1b[32m"
YELLOW = "\x1b[33m"
MAGENTA = "\x1b[35m"
CYAN = "\x1b[36m"
DIM = "\x1b[90m"
BOLD = "\x1b[1m"

# Every kind, with a sample message. Used for the differential test and for the
# indent table, so a kind added to ui.KINDS and not to _ui.fish fails here.
SAMPLES = [
    ("title", "🧹 Cleaning up"),
    ("note", "restore it with make run-role ROLE=ai"),
    ("step", "Fetching upstream"),
    ("ok", "Linked 'commit'"),
    ("warn", "3 were git-tracked"),
    ("err", "Not a directory"),
    ("item", "~/dev/api/.claude"),
    ("done", "Removed 3 of 3"),
]


# --- colour composed by hand ------------------------------------------------


def fish(command, **env_overrides):
    """A fish snippet, run with the repo's functions on the path and stdout captured.

    Captured rather than on a terminal, which is the whole point of the tests below:
    fish gives every command substitution a pipe of its own, so a helper called inside
    one sees a pipe for fd 1 however the outer command was run, and cannot tell which.
    """
    preamble = f'set -g fish_function_path "{FISH_FUNCTIONS}/ui" $fish_function_path\n'
    env = {**os.environ, "TERM": "xterm-256color"}
    env.pop("FORCE_COLOR", None)
    env.pop("NO_COLOR", None)
    env.update(env_overrides)
    return subprocess.run(
        ["fish", "--no-config", "-c", preamble + command],
        env=env,
        capture_output=True,
        text=True,
    )


def test_a_composed_fragment_carries_its_colour_out_of_the_substitution():
    """`_ui paint` states intent; it does not decide.

    Deciding there is what left every `lns` arrow and every `clean_claude` marker plain
    on a real terminal: the isatty it ran answered for fish's substitution pipe, which is
    never a tty, rather than for the stdout the line was headed to.
    """
    assert fish('printf "%s" (_ui paint yellow x)').stdout == f"{YELLOW}x{RESET}"


def test_a_printed_line_strips_the_colour_its_stream_refuses():
    """Where the line lands is where colour is resolved, so a composed fragment reaching
    a pipe is plain again. colors.for_stream is the python counterpart; ui.paint needs
    no equivalent, because in-process it can see the stream it is painting for."""
    out = fish('_ui item (_ui paint dim " → ")(_ui paint yellow ⚠)').stdout
    assert out == "  ·  → ⚠\n"


def test_no_color_silences_a_composed_fragment():
    """The one part of the decision a composing helper can make on its own: NO_COLOR is
    a statement about every stream, so it needs no knowledge of this one."""
    assert fish('printf "%s" (_ui paint yellow x)', NO_COLOR="1").stdout == "x"


@pytest.mark.parametrize(
    "env,expected",
    [({}, 1), ({"FORCE_COLOR": "1"}, 0), ({"NO_COLOR": "1", "FORCE_COLOR": "1"}, 1)],
)
def test_color_enabled_answers_through_its_exit_status(env, expected):
    """A script that prints rows with `echo` has no printing kind to resolve its colours,
    so it asks. Through the status rather than stdout, because a command substitution
    would replace the very fd the question is about."""
    assert fish("_ui color-enabled", **env).returncode == expected


# --- the differential test --------------------------------------------------


def fish_render(kind, text):
    """One line as _ui.fish renders it, escape codes included."""
    preamble = f'set -g fish_function_path "{FISH_FUNCTIONS}/ui" $fish_function_path\n'
    env = {**os.environ, "FORCE_COLOR": "1", "TERM": "xterm-256color"}
    env.pop("NO_COLOR", None)
    result = subprocess.run(
        ["fish", "--no-config", "-c", preamble + f"_ui {kind} {text!r}"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    # `err` is the one kind that writes to stderr, in both halves.
    return (result.stderr if kind == "err" else result.stdout).rstrip("\n")


@pytest.mark.parametrize("kind,text", SAMPLES)
def test_both_halves_render_identical_bytes(coloured, kind, text):
    """The real check. fish's `set_color normal` emits \\x1b[m rather than the more
    common \\x1b[0m, which is the reset colors.py reproduces; a divergence in either
    half shows up here as a byte difference rather than being noticed by eye."""
    mine = ui.render(kind, text, stream=sys.stdout)
    assert mine == fish_render(kind, text)


def test_the_fish_half_refuses_an_unknown_kind():
    """Both halves take their kinds from one table. fish cannot import ui.KINDS, so
    the guarantee it can offer is that a name outside its own switch is an error rather
    than a silently unstyled line."""
    preamble = f'set -g fish_function_path "{FISH_FUNCTIONS}/ui" $fish_function_path\n'
    result = subprocess.run(
        ["fish", "--no-config", "-c", preamble + "_ui shout hello"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "unknown line kind" in result.stderr
