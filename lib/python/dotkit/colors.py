"""Terminal colours, matching what the fish half of the vocabulary emits.

`_ui` colours through `set_color`, whose reset is `\\x1b[m` rather than the more common
`\\x1b[0m`. Reproduced exactly so a python tool and a fish function are indistinguishable
when both are on screen.

Unlike `set_color`, these are suppressed when stdout is not a terminal, so piping to
a file or a test harness yields plain text. NO_COLOR and FORCE_COLOR override, per the
usual convention.
"""

import os
import re
import sys

RESET = "\x1b[m"
ESCAPE = re.compile(r"\x1b\[[0-9;]*m")
CODES = {
    "green": "\x1b[32m",
    "yellow": "\x1b[33m",
    "red": "\x1b[31m",
    "blue": "\x1b[34m",
    "magenta": "\x1b[35m",
    "cyan": "\x1b[36m",
    # brblack in fish: used for every de-emphasised suffix.
    "dim": "\x1b[90m",
    "bold": "\x1b[1m",
}


def enabled(stream=None):
    """Whether to emit escape codes.

    NO_COLOR wins over FORCE_COLOR: a user who has asked for no colour anywhere means
    it, and a tool overriding that is a bug rather than a feature.
    """
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    stream = stream or sys.stdout
    try:
        return stream.isatty()
    except (AttributeError, ValueError):
        return False


def paint(text, colour, stream=None):
    """Wrap text in a colour, or return it unchanged when colour is off."""
    if not text or colour is None or not enabled(stream):
        return text
    return f"{CODES[colour]}{text}{RESET}"


def cross(stream=None):
    """The refusal marker. Every refusal wears the same magenta, wherever it prints."""
    return paint("✗", "magenta", stream)


def strip(text):
    """Text with every colour escape removed."""
    return ESCAPE.sub("", text)


def for_stream(text, stream):
    """Already-painted text, made safe for a stream that may not want colour.

    Some text is painted before its destination is known: argparse formats usage
    through a HelpFormatter that has no idea whether the parser is about to print it to
    stdout for `--help` or to stderr for a refusal. Without this, `claude-kit bogus
    2>log` from a terminal writes escape codes into the log.
    """
    return text if enabled(stream) else strip(text)
