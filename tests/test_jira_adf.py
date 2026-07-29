"""`adf.py` builds the squad's Jira description template as ADF.

The cases pin two things: the template shape the skill specifies (fixed section
order, lozenge colors, Gherkin rendering) and the ADF gotchas the script exists
to make unreachable. The gotcha cases walk the whole emitted document rather
than one node, so a refactor that reintroduces a rejected shape somewhere else
still fails.
"""

import json
import subprocess
import sys

import pytest

from conftest import REPO

ADF = REPO / "roles/ai/files/claude/skills/jira/scripts/adf.py"

EXIT_OK = 0
EXIT_USAGE = 1
EXIT_BAD_SECTION = 2
EXIT_MISSING_SECTION = 3
EXIT_BAD_GHERKIN = 4

EM_DASH = chr(0x2014)
EN_DASH = chr(0x2013)
CURLY_APOSTROPHE = chr(0x2019)
CURLY_OPEN_QUOTE = chr(0x201C)
CURLY_CLOSE_QUOTE = chr(0x201D)

GHERKIN = """Scenario: oversized payloads are rejected
GIVEN a payload larger than 1MB
WHEN the handler receives it
THEN it responds 413
"""

SOURCE_URL = "https://example.slack.com/archives/C123/p456"


@pytest.fixture
def adf():
    """Build ADF from a template body. adf(body, *argv) -> CompletedProcess."""

    def run(body, *argv):
        return subprocess.run(
            [sys.executable, str(ADF), "-", *argv],
            input=body,
            capture_output=True,
            text=True,
        )

    return run


def template(context="The handler crashes on payloads over 1MB.", criteria=GHERKIN, **extra):
    parts = [f"## Context\n{context}\n", f"## Acceptance criteria\n{criteria}"]
    for title, body in extra.items():
        heading = {"sources": "Resource / sources", "design": "Design"}[title]
        parts.append(f"## {heading}\n{body}\n")
    return "\n".join(parts)


def doc(result):
    assert result.returncode == EXIT_OK, result.stderr
    return json.loads(result.stdout)


def walk(node):
    yield node
    for child in node.get("content", []) or []:
        yield from walk(child)


def text_nodes(document):
    return [n for n in walk(document) if n.get("type") == "text"]


def mark_kinds(node):
    return {mark["type"] for mark in node.get("marks", [])}


def headings(document):
    """Every section header as (lozenge text, color), in document order."""
    out = []
    for node in document["content"]:
        if node.get("type") != "heading":
            continue
        status = node["content"][0]
        out.append((status["attrs"]["text"], status["attrs"]["color"]))
    return out


def section(document, title):
    """The nodes between a section's heading and the next heading."""
    body, collecting = [], False
    for node in document["content"]:
        if node.get("type") == "heading":
            collecting = node["content"][0]["attrs"]["text"] == title
            continue
        if collecting:
            body.append(node)
    return body


def flat_text(nodes):
    return "".join(n.get("text", "") for node in nodes for n in walk(node))


def test_a_complete_implementation_ticket_renders_the_whole_template(adf):
    """Given all four sections, When the ADF is built, Then it is a bare ADF doc
    whose headers are the template's lozenges in the template's order."""
    document = doc(adf(template(sources=SOURCE_URL, design="Mockups attached.")))
    assert document["type"] == "doc"
    assert document["version"] == 1
    assert headings(document) == [
        ("Context", "blue"),
        ("Acceptance criteria", "green"),
        ("Resource / sources", "yellow"),
        ("Design", "red"),
    ]


def test_sections_render_in_template_order_whatever_order_they_arrive_in(adf):
    """Given Design written before Resource / sources, When the ADF is built,
    Then the emitted order is still the template's.

    Section order is part of the agreed template, so the input cannot get it wrong.
    """
    body = "\n".join(
        [
            "## Design\nA mockup.\n",
            f"## Resource / sources\n{SOURCE_URL}\n",
            f"## Acceptance criteria\n{GHERKIN}",
            "## Context\nThe handler crashes.\n",
        ]
    )
    assert [title for title, _ in headings(doc(adf(body)))] == [
        "Context",
        "Acceptance criteria",
        "Resource / sources",
        "Design",
    ]


def test_an_omitted_design_section_leaves_no_empty_header(adf):
    """Given no Design section, When the ADF is built, Then no Design lozenge exists."""
    document = doc(adf(template(sources=SOURCE_URL)))
    assert [title for title, _ in headings(document)] == [
        "Context",
        "Acceptance criteria",
        "Resource / sources",
    ]


def test_the_source_link_is_a_link_marked_text_node(adf):
    """Given a bare URL as the source, When the ADF is built, Then the section holds
    one paragraph whose text carries a link mark pointing at that URL."""
    body = section(doc(adf(template(sources=SOURCE_URL))), "Resource / sources")
    assert [node["type"] for node in body] == ["paragraph"]
    node = body[0]["content"][0]
    assert node["text"] == SOURCE_URL
    assert node["marks"] == [{"type": "link", "attrs": {"href": SOURCE_URL}}]


def test_sentence_punctuation_stays_outside_the_source_link(adf):
    """Given a URL followed by a period, When the ADF is built, Then the href stops
    at the URL.

    A trailing period swallowed into the href produces a dead link in Jira.
    """
    body = section(doc(adf(template(sources=f"See {SOURCE_URL}."))), "Resource / sources")
    hrefs = [
        mark["attrs"]["href"]
        for node in text_nodes(body[0])
        for mark in node.get("marks", [])
        if mark["type"] == "link"
    ]
    assert hrefs == [SOURCE_URL]
    assert flat_text(body).endswith(".")


def test_an_investigation_ticket_flags_itself_in_context(adf):
    """Given --investigation, When the ADF is built, Then Context ends with the
    investigation-only sentence and the shape is otherwise the template's."""
    document = doc(adf(template(), "--investigation"))
    context = flat_text(section(document, "Context"))
    assert context.endswith(
        "This ticket is for investigation only, implementation will be tracked in a "
        "separate follow-up once we agree on a direction."
    )
    assert [title for title, _ in headings(document)] == ["Context", "Acceptance criteria"]


def test_an_investigation_sentence_already_written_is_not_repeated(adf):
    """Given Context already carries the flagging sentence, When --investigation is
    passed, Then it appears once."""
    written = (
        "The image is 900MB. This ticket is for investigation only, implementation "
        "will be tracked in a separate follow-up once we agree on a direction."
    )
    context = flat_text(section(doc(adf(template(context=written), "--investigation")), "Context"))
    assert context.count("for investigation only") == 1


def test_an_implementation_ticket_is_not_flagged_as_investigation(adf):
    """Given no --investigation, When the ADF is built, Then no flagging sentence
    is added."""
    assert "for investigation only" not in flat_text(section(doc(adf(template())), "Context"))


def test_gherkin_renders_one_paragraph_per_scenario_with_a_bold_header(adf):
    """Given two scenarios, When the ADF is built, Then each is one paragraph whose
    first node is the bold Scenario line followed by its steps on separate lines."""
    criteria = GHERKIN + "\nScenario: small payloads still work\nGIVEN a payload under 1MB\nWHEN the handler receives it\nTHEN it responds 200\n"
    body = section(doc(adf(template(criteria=criteria))), "Acceptance criteria")
    assert [node["type"] for node in body] == ["paragraph", "paragraph"]
    for paragraph, name in zip(body, ("oversized payloads are rejected", "small payloads still work")):
        header = paragraph["content"][0]
        assert header["text"] == f"Scenario: {name}"
        assert mark_kinds(header) == {"strong"}
        steps = [n["text"] for n in paragraph["content"][1:] if n["type"] == "text"]
        assert steps[0].startswith("GIVEN ")
        assert any(step.startswith("THEN ") for step in steps)
        breaks = [n for n in paragraph["content"] if n["type"] == "hardBreak"]
        assert len(breaks) == len(steps)


def test_an_and_line_stays_inside_its_scenario(adf):
    """Given a scenario with an AND, When the ADF is built, Then the AND line is a
    step of that scenario's paragraph."""
    criteria = GHERKIN + "AND the event is recorded as rejected\n"
    body = section(doc(adf(template(criteria=criteria))), "Acceptance criteria")
    assert len(body) == 1
    assert flat_text(body).endswith("AND the event is recorded as rejected")


def test_the_scenario_header_markers_are_accepted_either_way(adf):
    """Given a bold-marked Scenario line, When the ADF is built, Then the asterisks
    do not survive into the text.

    The skill's own example writes the line as **Scenario: ...**.
    """
    criteria = "**Scenario: it works**\nGIVEN a\nWHEN b\nTHEN c\n"
    header = section(doc(adf(template(criteria=criteria))), "Acceptance criteria")[0]["content"][0]
    assert header["text"] == "Scenario: it works"
    assert mark_kinds(header) == {"strong"}


def test_no_text_node_carries_code_alongside_a_formatting_mark(adf):
    """Given bold wrapping an inline code span, When the ADF is built, Then the code
    span is its own node and no node carries both marks.

    acli rejects a combined strong+code node with INVALID_INPUT.
    """
    document = doc(adf(template(context="**Simplify `.gitignore`** before the release.")))
    for node in text_nodes(document):
        assert not ({"code"} & mark_kinds(node) and {"strong", "em"} & mark_kinds(node))
    marked = {node["text"]: mark_kinds(node) for node in text_nodes(document)}
    assert marked["Simplify "] == {"strong"}
    assert marked[".gitignore"] == {"code"}


def test_a_code_span_inside_a_scenario_step_keeps_the_step_valid(adf):
    """Given a code span in a THEN line, When the ADF is built, Then the step splits
    into plain and code nodes rather than one node carrying both marks."""
    criteria = "Scenario: it writes the file\nGIVEN a run\nWHEN it finishes\nTHEN `out.json` exists\n"
    document = doc(adf(template(criteria=criteria)))
    coded = [node for node in text_nodes(document) if "code" in mark_kinds(node)]
    assert [node["text"] for node in coded] == ["out.json"]
    assert all(mark_kinds(node) == {"code"} for node in coded)


def test_every_list_item_wraps_its_text_in_a_paragraph(adf):
    """Given bullets and a numbered list, When the ADF is built, Then no listItem
    holds raw text.

    ADF rejects text directly inside a listItem.
    """
    document = doc(
        adf(template(context="Two symptoms:\n\n- it crashes\n- it retries\n\n1. first\n2. second"))
    )
    items = [node for node in walk(document) if node.get("type") == "listItem"]
    assert len(items) == 4
    for item in items:
        assert [child["type"] for child in item["content"]] == ["paragraph"]


def test_a_section_body_is_a_sibling_of_its_heading(adf):
    """Given any section, When the ADF is built, Then its heading holds only the
    lozenge and a space, and the prose sits at document level.

    Nesting the body inside the heading is the shape that renders as a giant title.
    """
    document = doc(adf(template(sources=SOURCE_URL)))
    for node in document["content"]:
        if node.get("type") != "heading":
            continue
        assert node["attrs"] == {"level": 2}
        assert [child["type"] for child in node["content"]] == ["status", "text"]
        assert node["content"][1]["text"] == " "
        assert node["content"][0]["attrs"]["style"] == ""
    assert any(node["type"] == "paragraph" for node in document["content"])


def test_an_em_dash_in_prose_becomes_a_hyphen(adf):
    """Given prose containing em and en dashes, When the ADF is built, Then neither
    character reaches the ticket.

    The ticket conventions ban them, and prose pasted from a thread carries them in.
    """
    context = f"The export fails {EM_DASH} silently {EN_DASH} on every retry."
    document = doc(adf(template(context=context)))
    assert EM_DASH not in document["content"][1]["content"][0]["text"]
    assert EN_DASH not in document["content"][1]["content"][0]["text"]
    assert "fails - silently - on every retry" in flat_text(section(document, "Context"))


def test_curly_quotes_become_straight_quotes(adf):
    """Given curly quotes in prose, When the ADF is built, Then they are straightened."""
    context = (
        f"The {CURLY_OPEN_QUOTE}export{CURLY_CLOSE_QUOTE} step "
        f"doesn{CURLY_APOSTROPHE}t finish."
    )
    rendered = flat_text(section(doc(adf(template(context=context))), "Context"))
    assert '"export"' in rendered
    assert "doesn't finish" in rendered
    assert not {CURLY_OPEN_QUOTE, CURLY_CLOSE_QUOTE, CURLY_APOSTROPHE} & set(rendered)


def test_no_emitted_text_node_is_empty(adf):
    """Given adjacent markers that leave nothing between them, When the ADF is built,
    Then no zero-length text node is emitted.

    ADF rejects a text node with an empty string.
    """
    document = doc(adf(template(context="`code`**bold**`more`*em* trailing")))
    assert all(node["text"] for node in text_nodes(document))


def test_an_unknown_section_is_refused(adf):
    """Given a heading that is not in the template, When the ADF is built, Then it
    exits on the section code."""
    result = adf(template() + "\n## Notes\nSomething else.\n")
    assert result.returncode == EXIT_BAD_SECTION


def test_an_empty_section_is_refused(adf):
    """Given a Design heading with no body, When the ADF is built, Then it exits on
    the section code rather than emitting an orphan header."""
    assert adf(template() + "\n## Design\n").returncode == EXIT_BAD_SECTION


def test_a_duplicated_section_is_refused(adf):
    """Given two Context headings, When the ADF is built, Then it exits on the
    section code."""
    assert adf(template() + "\n## Context\nMore.\n").returncode == EXIT_BAD_SECTION


def test_content_before_the_first_heading_is_refused(adf):
    """Given prose above the first section, When the ADF is built, Then it exits on
    the section code."""
    assert adf("A stray intro line.\n\n" + template()).returncode == EXIT_BAD_SECTION


@pytest.mark.parametrize(
    "criteria",
    [
        "- the export completes\n- the totals are in GBP\n",
        "Scenario: it works\nGIVEN a\nTHEN c\n",
        "Scenario: it works\nGIVEN a\nWHEN b\n",
        "Scenario: it works\nGiven a\nWHEN b\nTHEN c\n",
        "Scenario: it works\nTHEN c\nGIVEN a\nWHEN b\n",
        "Scenario:\nGIVEN a\nWHEN b\nTHEN c\n",
        "Scenario: it works\nGIVEN\nWHEN b\nTHEN c\n",
        "AND something\nScenario: it works\nGIVEN a\nWHEN b\nTHEN c\n",
        "Scenario: it works\nAND something\nGIVEN a\nWHEN b\nTHEN c\n",
        "the export should complete\n",
    ],
    ids=[
        "bullets-instead-of-scenarios",
        "no-when",
        "no-then",
        "lowercase-keyword",
        "steps-out-of-order",
        "unnamed-scenario",
        "keyword-with-no-text",
        "and-before-any-scenario",
        "and-before-its-step",
        "prose-instead-of-a-scenario",
    ],
)
def test_acceptance_criteria_that_are_not_strict_gherkin_are_refused(adf, criteria):
    """Given acceptance criteria that break the Gherkin rule, When the ADF is built,
    Then it exits on the Gherkin code instead of emitting them."""
    result = adf(template(criteria=criteria))
    assert result.returncode == EXIT_BAD_GHERKIN
    assert not result.stdout


def test_a_missing_required_section_is_refused(adf):
    """Given no Acceptance criteria section, When the ADF is built, Then it exits on
    the missing-section code."""
    assert adf("## Context\nThe handler crashes.\n").returncode == EXIT_MISSING_SECTION


def test_an_unreadable_source_is_a_usage_error():
    """Given a path that does not exist, When the ADF is built, Then it exits on the
    usage code."""
    result = subprocess.run(
        [sys.executable, str(ADF), "no/such/template.md"], capture_output=True, text=True
    )
    assert result.returncode == EXIT_USAGE


def test_out_writes_the_document_and_prints_the_path(adf, tmp_path):
    """Given --out, When the ADF is built, Then the file holds the document and stdout
    holds only its path, ready for acli --description-file."""
    target = tmp_path / "ticket-adf.json"
    result = adf(template(), "--out", str(target))
    assert result.returncode == EXIT_OK
    assert result.stdout.strip() == str(target)
    assert json.loads(target.read_text())["type"] == "doc"


def test_out_creates_the_directory_it_is_pointed_at(adf, tmp_path):
    """Given --out under a directory that does not exist, When the ADF is built, Then the
    directory is created rather than the write failing, because the conventional target
    /tmp/claude/ is absent until a skill first writes there."""
    target = tmp_path / "claude" / "ticket-adf.json"
    result = adf(template(), "--out", str(target))
    assert result.returncode == EXIT_OK
    assert json.loads(target.read_text())["type"] == "doc"


def test_the_script_is_executable_and_stdlib_only():
    """Given the script on disk, When it is inspected, Then it is executable, carries
    the plain python3 shebang, and imports nothing third-party."""
    assert ADF.stat().st_mode & 0o111
    lines = ADF.read_text().splitlines()
    assert lines[0] == "#!/usr/bin/env python3"
    imported = {
        line.split()[1].split(".")[0]
        for line in lines
        if line.startswith(("import ", "from ")) and "conftest" not in line
    }
    assert imported <= set(sys.stdlib_module_names)
