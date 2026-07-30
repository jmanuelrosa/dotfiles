"""The line vocabulary every script in this repo prints through.

The python half of roles/shell/files/fish/functions/_ui.fish, kind for kind and glyph
for glyph, so a fish function and a python command are indistinguishable on screen.
Two rules hold the whole style together:

    status is a coloured glyph   ✓ green, ⚠ yellow, ✗ magenta, · dim, → cyan
    topic is an emoji            and only ever on a `title` or a `done` line

Emoji are double-width in most terminals, so one used as a row marker knocks every
following column out of alignment. Keeping them on the two line kinds that start at
column zero is what lets a listing stay a listing.

    ui.title("🧩 Available skills:")        bold heading, emoji supplied by the caller
    ui.step("Fetching upstream")            → an action being taken
    ui.ok("Linked 'commit'")                ✓ it worked
    ui.warn("3 were git-tracked")           ⚠ worth reading, not fatal
    ui.err("Not a directory")               ✗ a refusal, printed to stderr
    ui.item("~/dev/api/.claude")            · one entry of a list
    ui.note("restore it with make run")     dim aside under the line above
    ui.done("Removed 3 of 3")               ✨ the closing summary

Indent defaults to 0, or 2 for `item` and `note`; pass indent= to override. Colour is
colors.py's decision, per stream, so piping to a file yields plain text.

Not claude-kit-only: weekly-recap imports it from beside the shim, and any python CLI
added to this directory should. The emoji vocabulary is listed in the repo CLAUDE.md.
"""

import os
import sys

from . import colors

# glyph, colour, whether the message itself is painted, and the default indent.
# One table rather than one function per kind, so the fish half can be diffed against
# it by eye and a new kind is a single line in each file.
#
# Only `title` and `note` paint their text. Everywhere else the glyph carries the
# colour and the message stays the terminal's own, which competes with nothing and
# reads on any theme.
KINDS = {
    "title": (None, "bold", True, 0),
    "note": (None, "dim", True, 2),
    "step": ("→", "cyan", False, 0),
    "ok": ("✓", "green", False, 0),
    "warn": ("⚠", "yellow", False, 0),
    "err": ("✗", "magenta", False, 0),
    "item": ("·", "dim", False, 2),
    # ✨ is never coloured: it is the one emoji this module supplies itself, because
    # every script closes the same way.
    "done": ("✨", None, False, 0),
}

# How many names an aside may list before it stops informing and starts scrolling.
NAME_LIMIT = 6


def render(kind, text, indent=None, stream=None):
    """One line as a string, ready to print or to hand to a caller's own emitter.

    Separated from printing because `doctor` collects its report through an `emit`
    callback, and a helper that could only print would force it to rebuild the palette
    by hand.
    """
    glyph, colour, paint_text, default_indent = KINDS[kind]
    pad = " " * (default_indent if indent is None else indent)
    if paint_text:
        return pad + colors.paint(text, colour, stream)
    return f"{pad}{colors.paint(glyph, colour, stream)} {text}"


def _emit(kind, text, indent, stream):
    stream = stream or sys.stdout
    print(render(kind, text, indent, stream), file=stream)


def title(text, indent=None, stream=None):
    """A bold section heading. The topic emoji, if any, belongs in `text`."""
    _emit("title", text, indent, stream)


def note(text, indent=None, stream=None):
    """A dimmed aside, normally sitting under the line it qualifies."""
    _emit("note", text, indent, stream)


def step(text, indent=None, stream=None):
    _emit("step", text, indent, stream)


def ok(text, indent=None, stream=None):
    _emit("ok", text, indent, stream)


def warn(text, indent=None, stream=None):
    _emit("warn", text, indent, stream)


def item(text, indent=None, stream=None):
    _emit("item", text, indent, stream)


def err(text, indent=None, stream=None):
    """A refusal. Goes to stderr, and decides its colour against stderr."""
    _emit("err", text, indent, stream or sys.stderr)


def done(text, indent=None, stream=None):
    """The closing summary."""
    _emit("done", text, indent, stream)


def blank(stream=None):
    print("", file=stream or sys.stdout)


def paint(text, colour, stream=None):
    """Colour a fragment for embedding in a line built by hand."""
    return colors.paint(text, colour, stream)


def names_or_count(names, noun, limit=NAME_LIMIT):
    """Names while they still read as a list, otherwise how many there are.

    A group holds as many as 37 artifacts, and an aside naming every one of them
    scrolls the lines that matter off the screen. No fish counterpart: only the
    group commands print these asides, and they exist here alone.
    """
    names = list(names)
    if len(names) <= limit:
        return ", ".join(names)
    return f"{len(names)} {noun}s"


def path(target, home=None):
    """A path with $HOME collapsed back to ~, as `_ui path` does in fish."""
    home = str(home or os.path.expanduser("~"))
    text = str(target)
    if text == home:
        return "~"
    if text.startswith(home + os.sep):
        return "~" + text[len(home) :]
    return text
