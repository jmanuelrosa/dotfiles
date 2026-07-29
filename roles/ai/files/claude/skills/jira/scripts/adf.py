#!/usr/bin/env python3
"""adf.py - build a Jira description in ADF from the squad's ticket template.

Reads a markdown-ish file (or stdin on `-`) whose `##` headers name the
template's sections and writes the bare ADF `doc` that
`acli jira workitem create|edit --description-file` expects:

    ## Context
    The Stripe webhook handler crashes when the payload exceeds 1MB.

    ## Acceptance criteria
    Scenario: oversized payloads are rejected
    GIVEN a payload larger than 1MB
    WHEN the handler receives it
    THEN it responds 413
    AND the event is recorded as rejected

    ## Resource / sources
    https://example.slack.com/archives/C123/p456

Sections are emitted in the template's order whatever order they arrive in,
each under its fixed status lozenge. Inline `**bold**`, `` `code` ``,
`*italic*`, `[label](url)` and bare URLs are supported; bullets and numbered
lists are picked up from the usual markers.

Every ADF shape acli rejects is unreachable from this input: no text node ever
carries `code` alongside `strong` or `em`, list items are always
paragraph-wrapped, and a section's blocks are always siblings of its heading.
Em dashes, en dashes and curly quotes are normalized away, because the
generated text lands in a Jira ticket that bans them.
"""

import argparse
import json
import os
import re
import sys
import unicodedata

EXIT_OK = 0
EXIT_USAGE = 1
EXIT_BAD_SECTION = 2
EXIT_MISSING_SECTION = 3
EXIT_BAD_GHERKIN = 4

HEADING_LEVEL = 2

CONTEXT = "Context"
ACCEPTANCE_CRITERIA = "Acceptance criteria"
SOURCES = "Resource / sources"
DESIGN = "Design"

# Title strings and lozenge colors are the squad's agreed template. They are
# fixed: the section order below is the order the description renders in.
SECTIONS = (
    (CONTEXT, "blue"),
    (ACCEPTANCE_CRITERIA, "green"),
    (SOURCES, "yellow"),
    (DESIGN, "red"),
)
REQUIRED = (CONTEXT, ACCEPTANCE_CRITERIA)

ALIASES = {
    "context": CONTEXT,
    "acceptancecriteria": ACCEPTANCE_CRITERIA,
    "acceptance": ACCEPTANCE_CRITERIA,
    "criteria": ACCEPTANCE_CRITERIA,
    "ac": ACCEPTANCE_CRITERIA,
    "resourcesources": SOURCES,
    "resource": SOURCES,
    "resources": SOURCES,
    "source": SOURCES,
    "sources": SOURCES,
    "design": DESIGN,
}

INVESTIGATION_NOTE = (
    "This ticket is for investigation only, implementation will be tracked in a "
    "separate follow-up once we agree on a direction."
)
INVESTIGATION_MARKER = "for investigation only"

HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*#*$")
BULLET = re.compile(r"^\s*[-*+]\s+(.*)$")
ORDERED = re.compile(r"^\s*\d+[.)]\s+(.*)$")

SCENARIO = re.compile(r"^\s*(?:\*\*)?Scenario:\s*(.*?)(?:\*\*)?\s*$")
STEP_RANK = {"GIVEN": 1, "WHEN": 2, "THEN": 3}
CONJUNCTION = "AND"

INLINE = re.compile(
    r"`(?P<code>[^`]+)`"
    r"|\*\*(?P<strong>.+?)\*\*"
    r"|(?<!\*)\*(?P<em>[^*]+?)\*(?!\*)"
    r"|\[(?P<label>[^\]]*)\]\((?P<href>[^)\s]+)\)"
    r"|(?P<url>(?:https?://|mailto:)\S+)"
)

# Built from codepoints so this file never contains the characters the house
# style bans, and so the hook that blocks them cannot trip on the table itself.
PUNCTUATION = str.maketrans(
    {
        chr(0x2014): "-",
        chr(0x2013): "-",
        chr(0x2018): "'",
        chr(0x2019): "'",
        chr(0x201C): '"',
        chr(0x201D): '"',
    }
)

URL_TRAIL = ".,;:!?\"'"


class InputError(Exception):
    """Off-template input, carrying the exit code and the line to point at."""

    def __init__(self, code, message, lineno=None):
        super().__init__(message)
        self.code = code
        self.lineno = lineno


def fail(message, code):
    print(f"adf.py: {message}", file=sys.stderr)
    sys.exit(code)


def normalize(title):
    return "".join(ch for ch in title.lower() if ch.isalnum())


def clean(raw):
    """Strip the punctuation the ticket conventions ban, plus control characters.

    ADF has no escape for a control character, so a stray one in pasted prose
    would travel into the JSON body and come back as INVALID_INPUT.
    """
    text = raw.translate(PUNCTUATION)
    return "".join(ch for ch in text if ch == "\t" or unicodedata.category(ch) != "Cc")


def marks_for(marks):
    kinds = {kind for kind, _ in marks}
    if "code" in kinds:
        # acli rejects a text node carrying `code` together with `strong` or `em`
        # with INVALID_INPUT, so the formatting mark is dropped here and the code
        # span ends up as its own adjacent node.
        marks = tuple(m for m in marks if m[0] not in ("strong", "em"))
    out, seen = [], set()
    for kind, attr in marks:
        if kind in seen:
            continue
        seen.add(kind)
        out.append({"type": "link", "attrs": {"href": attr}} if kind == "link" else {"type": kind})
    return out


def text_nodes(raw, marks=()):
    """The one text node `raw` is worth, or none at all: ADF rejects empty text."""
    text = clean(raw)
    if not text:
        return []
    node = {"type": "text", "text": text}
    applied = marks_for(marks)
    if applied:
        node["marks"] = applied
    return [node]


def split_url(url):
    """Peel sentence punctuation off a bare URL so it stays outside the link."""
    trail = ""
    while url and url[-1] in URL_TRAIL:
        url, trail = url[:-1], url[-1] + trail
    while url.endswith(")") and url.count(")") > url.count("("):
        url, trail = url[:-1], ")" + trail
    return url, trail


def inline(raw, marks=()):
    nodes, pos = [], 0
    for match in INLINE.finditer(raw):
        nodes.extend(text_nodes(raw[pos : match.start()], marks))
        pos = match.end()
        if match.group("code") is not None:
            nodes.extend(text_nodes(match.group("code"), marks + (("code", None),)))
        elif match.group("strong") is not None:
            nodes.extend(inline(match.group("strong"), marks + (("strong", None),)))
        elif match.group("em") is not None:
            nodes.extend(inline(match.group("em"), marks + (("em", None),)))
        elif match.group("label") is not None:
            nodes.extend(inline(match.group("label"), marks + (("link", match.group("href")),)))
        else:
            url, trail = split_url(match.group("url"))
            nodes.extend(text_nodes(url, marks + (("link", url),)))
            nodes.extend(text_nodes(trail, marks))
    nodes.extend(text_nodes(raw[pos:], marks))
    return nodes


def paragraph(content):
    return {"type": "paragraph", "content": content}


def list_node(kind, items):
    # ADF rejects raw text in a listItem, so every item is a paragraph.
    return {
        "type": kind,
        "content": [
            {"type": "listItem", "content": [paragraph(inline(" ".join(item)))]} for item in items
        ],
    }


def render_prose(lines):
    """Turn a section body into paragraph and list nodes.

    A blank line closes whatever is open. A line with no marker that follows a
    list item continues that item, which is what markdown does with a wrapped
    bullet.
    """
    nodes, prose, items, kind = [], [], [], None

    def flush():
        nonlocal prose, items, kind
        if prose:
            nodes.append(paragraph(inline(" ".join(prose))))
            prose = []
        if items:
            nodes.append(list_node(kind, items))
            items, kind = [], None

    for line in lines:
        if not line.strip():
            flush()
            continue
        bullet, ordered = BULLET.match(line), ORDERED.match(line)
        if bullet or ordered:
            wanted = "bulletList" if bullet else "orderedList"
            if kind != wanted:
                flush()
                kind = wanted
            items.append([(bullet or ordered).group(1).strip()])
        elif items:
            items[-1].append(line.strip())
        else:
            prose.append(line.strip())
    flush()
    return nodes


def bad_gherkin(message, lineno):
    return InputError(EXIT_BAD_GHERKIN, message, lineno)


def parse_scenarios(numbered):
    """Split the acceptance criteria into scenarios, rejecting anything but Gherkin."""
    scenarios = []
    for lineno, line in numbered:
        if not line.strip():
            continue
        header = SCENARIO.match(line)
        if header:
            name = header.group(1).strip()
            if not name:
                raise bad_gherkin("a scenario needs a name after 'Scenario:'", lineno)
            scenarios.append({"name": name, "lineno": lineno, "steps": []})
            continue
        if BULLET.match(line) or ORDERED.match(line):
            raise bad_gherkin(
                "acceptance criteria are Gherkin scenarios, not bullets or a numbered list",
                lineno,
            )
        if not scenarios:
            raise bad_gherkin(
                "acceptance criteria must start with a 'Scenario: <name>' line", lineno
            )
        keyword, _, rest = line.strip().partition(" ")
        upper = keyword.upper()
        if upper not in STEP_RANK and upper != CONJUNCTION:
            raise bad_gherkin(
                f"expected a GIVEN, WHEN, THEN or AND line, got {line.strip()!r}", lineno
            )
        if keyword != upper:
            raise bad_gherkin(f"{keyword!r} must be capitalized as {upper!r}", lineno)
        if not rest.strip():
            raise bad_gherkin(f"the {upper} line has no text after the keyword", lineno)
        scenarios[-1]["steps"].append((lineno, upper, rest.strip()))
    if not scenarios:
        raise bad_gherkin("acceptance criteria are empty", numbered[0][0])
    for scenario in scenarios:
        validate_scenario(scenario)
    return scenarios


def validate_scenario(scenario):
    rank, seen = 0, set()
    for lineno, keyword, _ in scenario["steps"]:
        if keyword == CONJUNCTION:
            if not seen:
                raise bad_gherkin("an AND line cannot come before its GIVEN, WHEN or THEN", lineno)
            continue
        if STEP_RANK[keyword] < rank:
            raise bad_gherkin(
                f"{keyword} comes after a later step; order them GIVEN, WHEN, THEN", lineno
            )
        rank = STEP_RANK[keyword]
        seen.add(keyword)
    missing = [keyword for keyword in STEP_RANK if keyword not in seen]
    if missing:
        raise bad_gherkin(
            f"scenario {scenario['name']!r} is missing {', '.join(missing)}", scenario["lineno"]
        )


def render_gherkin(numbered):
    """One paragraph per scenario: a bold Scenario line, then its steps on
    following lines.

    Separate paragraphs would space the steps apart as if each were its own
    criterion.
    """
    nodes = []
    for scenario in parse_scenarios(numbered):
        content = inline(f"Scenario: {scenario['name']}", (("strong", None),))
        for _, keyword, rest in scenario["steps"]:
            content.append({"type": "hardBreak"})
            content.extend(inline(f"{keyword} {rest}"))
        nodes.append(paragraph(content))
    return nodes


def lozenge_heading(title, color):
    return {
        "type": "heading",
        "attrs": {"level": HEADING_LEVEL},
        "content": [
            {"type": "status", "attrs": {"text": title, "color": color, "style": ""}},
            # The trailing single-space text node is load-bearing: a heading whose
            # only child is a status lozenge does not render as a section header.
            {"type": "text", "text": " "},
        ],
    }


def parse(source):
    """Map section title to its numbered lines, refusing anything off-template."""
    found, title = {}, None
    for lineno, line in enumerate(source.splitlines(), 1):
        heading = HEADING.match(line)
        if heading:
            name = ALIASES.get(normalize(heading.group(1)))
            if name is None:
                allowed = ", ".join(title for title, _ in SECTIONS)
                raise InputError(
                    EXIT_BAD_SECTION,
                    f"unknown section {heading.group(1)!r}; expected one of: {allowed}",
                    lineno,
                )
            if name in found:
                raise InputError(EXIT_BAD_SECTION, f"section {name!r} appears twice", lineno)
            found[name] = []
            title = name
            continue
        if title is None:
            if line.strip():
                raise InputError(
                    EXIT_BAD_SECTION,
                    "content before the first '## <section>' heading",
                    lineno,
                )
            continue
        found[title].append((lineno, line))

    for name, numbered in found.items():
        if not any(line.strip() for _, line in numbered):
            raise InputError(
                EXIT_BAD_SECTION,
                f"section {name!r} is empty; write it or leave the heading out",
                numbered[0][0] if numbered else None,
            )
    missing = [name for name in REQUIRED if name not in found]
    if missing:
        raise InputError(
            EXIT_MISSING_SECTION, f"missing required section(s): {', '.join(missing)}"
        )
    return found


def build(source, investigation=False):
    found = parse(source)
    content = []
    for title, color in SECTIONS:
        if title not in found:
            continue
        numbered = found[title]
        if title == ACCEPTANCE_CRITERIA:
            body = render_gherkin(numbered)
        else:
            body = render_prose([line for _, line in numbered])
        if title == CONTEXT and investigation and INVESTIGATION_MARKER not in source.lower():
            body.extend(render_prose([INVESTIGATION_NOTE]))
        content.append(lozenge_heading(title, color))
        content.extend(body)
    return {"type": "doc", "version": 1, "content": content}


class Parser(argparse.ArgumentParser):
    """argparse exits 2 on a usage error, which is a section-error code here."""

    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(EXIT_USAGE, f"adf.py: {message}\n")


def main():
    parser = Parser(prog="adf.py", description=__doc__.splitlines()[0])
    parser.add_argument(
        "source", nargs="?", default="-", help="template file, or - to read stdin (default)"
    )
    parser.add_argument(
        "--investigation",
        action="store_true",
        help="append the investigation-only sentence to Context unless it is already there",
    )
    parser.add_argument(
        "--out",
        metavar="PATH",
        help="write the ADF here and print the path instead of the document",
    )
    args = parser.parse_args()

    try:
        source = sys.stdin.read() if args.source == "-" else open(args.source).read()
    except OSError as error:
        fail(f"cannot read {args.source}: {error}", EXIT_USAGE)

    try:
        doc = build(source, investigation=args.investigation)
    except InputError as error:
        where = f"line {error.lineno}: " if error.lineno else ""
        fail(f"{where}{error}", error.code)

    payload = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    if not args.out:
        sys.stdout.write(payload)
        return EXIT_OK
    try:
        # The conventional target is /tmp/claude/, which does not exist on a
        # machine where no skill has written there yet.
        directory = os.path.dirname(os.path.abspath(args.out))
        os.makedirs(directory, exist_ok=True)
        with open(args.out, "w") as handle:
            handle.write(payload)
    except OSError as error:
        fail(f"cannot write {args.out}: {error}", EXIT_USAGE)
    print(args.out)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
