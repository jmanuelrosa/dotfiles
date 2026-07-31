"""Frontmatter validation without a YAML parser.

`doctor` wants two facts about a skill or agent: that its frontmatter block parses
at all, and that it declares a `name`. Both used to come from PyYAML, which is a
test dependency, so on a machine carrying only python3 the check reported that it
had not run. It was skipped exactly where it mattered.

`description` reads the same dialect for `scout`, which wants a gist to print
rather than a verdict. Reading and validating stay separate functions: one may
refuse, the other never does.

The frontmatter these artifacts write is a flat mapping of scalars, with folded
values, multi-line plain values and the occasional nested `metadata`. That dialect
is small enough to scan, and the failure the check exists for is lexical: an
unquoted `": "` inside a plain value, which YAML reads as a mapping in a position
that forbids one, so the block fails whole and the artifact silently does not load.

Scanning is not parsing and this does not pretend otherwise. It reports only what
is certainly malformed and stays silent on everything else, so a construction it
does not model reads as valid rather than broken. The bias is deliberate: this
check once reported 69 false problems, and a false problem costs more than a
missed one because it teaches the reader to skip the report. What it does not
model is written down in `tests/test_frontmatter.py`, which holds the boundary by
running every case past PyYAML: whatever is called malformed here has to be
malformed there too.
"""

OPEN = "---\n"
CLOSE = "\n---"

# A value opening with one of these is not a plain scalar, so the lines beneath it
# belong to a real parser: quoted and flow forms may span lines, block scalars hold
# arbitrary text, and an anchor or tag says nothing about what follows.
OPAQUE_OPENERS = "\"'[{|>&*!"
# YAML keeps these as indicators, so no plain scalar may begin with one. A backtick
# is the one a description plausibly reaches for, which is what earns the rule.
RESERVED_OPENERS = "@`%,]}"
COMMENT = " #"

PLAIN = "plain"
OPAQUE = "opaque"

DESCRIPTION = "description:"
# Both block-scalar indicators. A value opening with one of these carries no text
# on its own line, so everything worth reading is in the lines beneath it.
BLOCK_OPENERS = "|>"
QUOTES = "\"'"


class Malformed(Exception):
    """The block cannot be valid YAML. The message names the offending line."""


def block(text):
    """The lines between a file's opening `---` and the next `---`, or None."""
    if not text.startswith(OPEN):
        return None
    body, separator, _ = text[len(OPEN) :].partition(CLOSE)
    return body if separator else None


def keys(text):
    """The top-level mapping keys of a file's frontmatter, or None if it has none.

    Raises Malformed when the block certainly does not parse.
    """
    body = block(text)
    return None if body is None else _scan(body)


def description(text):
    """A file's frontmatter `description`, flattened to one line, or "".

    Reading, not validating, so it never raises: this is what a report prints, and
    a malformed block is doctor's business rather than an excuse to say nothing.

    The three forms these artifacts write all collapse to the same run of words —
    a plain one-liner, a plain value continued across indented lines, and a block
    scalar. `grep -m1 '^description:'` handles only the first, which is how every
    skill written in the `description: >-` form used to reach scout's report with
    nothing beside its name.
    """
    body = block(text)
    if body is None:
        return ""
    lines = body.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith(DESCRIPTION):
            continue
        inline = line[len(DESCRIPTION) :].strip()
        # Everything indented under the key continues it, whichever form it took. A
        # blank line is kept as a paragraph break and folds away with the rest; the
        # first flush-left line is the next key and ends the value.
        folded = []
        for continuation in lines[index + 1 :]:
            if continuation.strip() and not continuation.startswith((" ", "\t")):
                break
            folded.append(continuation.strip())
        # A block indicator's own line holds only the indicator and its chomping
        # flag, so it contributes no words.
        parts = folded if not inline or inline[0] in BLOCK_OPENERS else [inline, *folded]
        return " ".join(" ".join(parts).split()).strip(QUOTES)
    return ""


def _scan(body):
    found = []
    beneath = OPAQUE
    for number, line in enumerate(body.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = line[: len(line) - len(line.lstrip())]
        if "\t" in indent:
            raise Malformed(f"line {number}: indented with a tab, which YAML forbids")
        if indent:
            if beneath is PLAIN:
                _reject_mapping_value(stripped, number)
            continue
        # A top-level sequence is valid YAML that merely has no keys, so the caller's
        # own `name` check is what should speak, not a parse error.
        if stripped == "-" or stripped.startswith("- "):
            continue
        entry = _split(stripped)
        if entry is None:
            raise Malformed(f"line {number}: expected `key: value`, got {stripped!r}")
        key, value = entry
        if key is not None:
            found.append(key)
        beneath = _beneath(value.strip(), number)
    return found


def _split(line):
    """(key, value) for a mapping line, or None when it is not one at all.

    Only the bare form can trust its first colon, since a quoted key may contain
    one. A quoted form this cannot split yields a None *key* rather than None, so it
    passes through unnamed instead of being refused: nothing here writes a quoted
    key, and reporting legal YAML as broken is the one outcome worth ruling out.
    """
    if line[0] in "\"'":
        closing = line.find(line[0], 1)
        rest = line[closing + 1 :] if closing != -1 else ""
        if not rest.startswith(":"):
            return None, ""
        return line[1:closing], rest[1:]
    key, separator, value = line.partition(":")
    return (key, value) if separator else None


def _beneath(value, number):
    """What the indented lines under this key continue, validating the value itself."""
    if not value:
        return OPAQUE
    if value[0] in OPAQUE_OPENERS:
        return OPAQUE
    if value[0] in RESERVED_OPENERS:
        raise Malformed(f"line {number}: a plain value cannot start with {value[0]!r}, which YAML reserves")
    _reject_mapping_value(value, number)
    return PLAIN


def _reject_mapping_value(text, number):
    """Refuse the colon that ends a plain scalar's line, which is the failure G8 is for.

    YAML reads `description: pick one: this or that` as a mapping nested inside a
    value, which is not allowed there, so the whole block fails and the artifact
    does not load. Quoting the value is the fix.
    """
    content = text.split(COMMENT)[0].rstrip()
    if ": " in content or content.endswith(":"):
        raise Malformed(f"line {number}: unquoted ': ' in a plain value, which YAML reads as a mapping")
