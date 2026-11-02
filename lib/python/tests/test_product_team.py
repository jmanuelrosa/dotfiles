"""The product-team walkthrough this repository renders, held to the pipeline it describes.

The bundle itself, its stage skills, templates and `pt.py`, lives in agent-catalog and is
asserted there. What stays here is the half a catalog change cannot see: the overview
diagram and the walkthrough docs under the Claude adapter, which describe that pipeline
and rot silently when prose around them is edited and the drawing is left alone.
"""

import re

import pytest
from dotkit.testing import CLAUDE, REPO

STAGES = (
    "0-refine-idea",
    "1-research",
    "2-write-prd",
    "3-red-team",
    "4-tech-shape",
    "5-decompose",
    "6-verify",
    "7-push-to-board",
    "8-living-spec",
)

# Words the pipeline retired. A doc still using one describes a different pipeline from
# the bundle to whoever reads it first. `AC-{n.m}.{k}` itself is NOT retired: ac-writer
# still mints one for a genuinely story-local criterion; what is retired is the chain
# that made those ids the acceptance bar.
RETIRED = ("Gate 2", "Gate 3", "6-gate-check", "expedited path", "local mode", "five human PR gates", "AC-*")

WALKTHROUGH = (CLAUDE / "README.md", CLAUDE / "GETTING-STARTED.md")


def diagram():
    return (CLAUDE / "GETTING-STARTED.md").read_text(encoding="utf-8").split("```")[1]


@pytest.mark.parametrize("name", STAGES)
def test_the_walkthrough_diagram_draws_every_stage(name):
    """The overview diagram is the first thing read after six months away.

    It survived this change describing the four-gate pipeline (`DoR -> board`, no tasks
    layer, no living spec), because prose edited around a diagram leaves the drawing
    alone and nothing was reading it.
    """
    assert name in diagram(), f"{name} is in the pipeline but not in the diagram"


def test_no_diagram_label_line_can_be_clipped():
    """Mermaid measures wrapping near 200px; a renderer that will not wrap then clips.

    That is invisible locally, because mermaid-cli wraps the same label the reader's
    renderer truncates: `seats implement` vanished off the end of a node that rendered
    correctly here. So the breaks are explicit and every line stays short enough to fit.
    """
    too_long = []
    for line in diagram().splitlines():
        if line.lstrip().startswith("%%"):  # the init directive is config, not a label
            continue
        for label in re.findall(r'"([^"]*)"', line):
            too_long += [s for s in label.split("<br/>") if len(s.strip()) > 24]
    assert not too_long, f"these label lines will clip: {too_long}"


@pytest.mark.parametrize("word", RETIRED)
def test_the_retired_vocabulary_is_gone_from_the_walkthrough(word):
    """A scan scoped to the bundle missed `Local mode` in the walkthrough for a commit.

    Case-insensitively, because the one that survived was a bolded heading and the
    vocabulary here is written lowercase.
    """
    hits = [
        path.relative_to(REPO)
        for path in WALKTHROUGH
        if word.lower() in path.read_text(encoding="utf-8").lower()
    ]
    assert not hits, f"{word!r} still appears in {hits}"
