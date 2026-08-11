"""The product-team pipeline's invariants, mostly the ones that fail by not happening.

Removing a gate is only safe if the thing the gate was buying moved somewhere else, and
four such moves ride this change: ADR review to CODEOWNERS, the reviewer's reasoning to a
column in STATUS.md, the scenario text to the board issue body, and the retrospective to
ship time. Every one of them fails the same way, which is that nobody notices. A missing
CODEOWNERS line does not error, an `approved` with no reason looks like an approval, an
issue full of bare ids looks like an issue, and a retrospective nobody wrote leaves no
gap. So they are asserted here rather than trusted to review.

The rest guard couplings between files that a later edit would otherwise break quietly:
`pt.py` parses fields out of the templates, `product-lead` is the only map of the stage
set, and the removed vocabulary (Gate 2, Gate 3, local mode, the expedited path) must not
come back in one file while the others have moved on.
"""

import re

import pytest
from dotkit.testing import REPO

CLAUDE = REPO / "roles/ai/files/claude"
PLUGIN = CLAUDE / "plugins/product-team"
SKILLS = PLUGIN / "skills"
TEMPLATES = SKILLS / "product-lead/references/templates"
CONVENTIONS = SKILLS / "product-lead/references/conventions.md"
SCRIPT = SKILLS / "product-lead/scripts/pt.py"

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

# Words this change removed. A file still using one has not been migrated, and the two
# halves then describe different pipelines to whoever reads the one they open first.
RETIRED = ("Gate 2", "Gate 3", "6-gate-check", "expedited path", "local mode")


def stage_bodies():
    for name in STAGES + ("setup-strategy", "product-lead"):
        yield name, (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


# --- the four mitigations ----------------------------------------------------


def test_setup_strategy_scaffolds_the_adr_codeowners_line():
    """The only review an ADR gets, now that stage 4 has no gate."""
    body = (SKILLS / "setup-strategy/SKILL.md").read_text(encoding="utf-8")
    assert "/docs/adr/" in body, "removing the design gate left ADRs with no approver"
    adr = body.index("/docs/adr/")
    initiatives = body.index("/docs/initiatives/")
    assert initiatives < adr, "CODEOWNERS applies the last matching pattern, so order matters"


def test_a_session_gate_records_a_reason():
    """A PR gate leaves its reasoning in comments; a session gate leaves only this."""
    status = (TEMPLATES / "status.md").read_text(encoding="utf-8")
    header = next(line for line in status.splitlines() if line.startswith("| Gate |"))
    assert "Reason" in header, "a gate row with no reason column records nothing a reviewer thought"
    assert "Decided by" in header and "Date" in header
    assert "its reason" in CONVENTIONS.read_text(encoding="utf-8").lower()


def test_stage_seven_expands_scenarios_into_the_issue_body():
    """A story claims ids so the repo holds one copy; an issue needs the text."""
    body = (SKILLS / "7-push-to-board/SKILL.md").read_text(encoding="utf-8")
    assert "expands its claimed scenarios" in body or "expand" in body.lower()
    assert "02-prd.md" in body, "the scenario text has to be copied from somewhere"


def test_only_the_living_spec_stage_appends_learnings():
    """It moved off stage 7, which the solo profile never runs."""
    appenders = {
        name for name, body in stage_bodies() if "Append to `docs/LEARNINGS.md`" in body
    }
    assert appenders == {"8-living-spec"}, f"LEARNINGS.md is appended by {appenders}"


def test_the_scaffolded_learnings_file_names_the_stage_that_writes_it():
    """setup-strategy creates the file, so its own note is where a stale name survives."""
    body = (SKILLS / "setup-strategy/SKILL.md").read_text(encoding="utf-8")
    line = next(line for line in body.splitlines() if "Appended by" in line)
    assert "8-living-spec" in line
    assert "7-push-to-board" not in line


# --- the stage set ----------------------------------------------------------


@pytest.mark.parametrize("name", STAGES)
def test_every_stage_skill_exists_and_is_named_in_the_pipeline_map(name):
    assert (SKILLS / name / "SKILL.md").is_file()
    body = (SKILLS / "product-lead/SKILL.md").read_text(encoding="utf-8")
    assert f"/product-team:{name}" in body, "a stage the hub never names is a stage nobody runs"


@pytest.mark.parametrize("name", STAGES)
def test_the_walkthrough_diagram_draws_every_stage(name):
    """The overview diagram is the first thing read after six months away.

    It survived this change describing the four-gate pipeline (`DoR -> board`, no tasks
    layer, no living spec), because prose edited around a diagram leaves the drawing
    alone and nothing was reading it.
    """
    body = (CLAUDE / "GETTING-STARTED.md").read_text(encoding="utf-8")
    diagram = body.split("```")[1]
    assert name in diagram, f"{name} is in the pipeline but not in the diagram"


def test_no_diagram_label_line_can_be_clipped():
    """Mermaid measures wrapping near 200px; a renderer that will not wrap then clips.

    That is invisible locally, because mermaid-cli wraps the same label the reader's
    renderer truncates: `seats implement` vanished off the end of a node that rendered
    correctly here. So the breaks are explicit and every line stays short enough to fit.
    """
    body = (CLAUDE / "GETTING-STARTED.md").read_text(encoding="utf-8")
    diagram = body.split("```")[1]
    too_long = []
    for line in diagram.splitlines():
        if line.lstrip().startswith("%%"):  # the init directive is config, not a label
            continue
        for label in re.findall(r'"([^"]*)"', line):
            too_long += [s for s in label.split("<br/>") if len(s.strip()) > 24]
    assert not too_long, f"these label lines will clip: {too_long}"


def test_the_verifier_is_pinned_off_the_session_model():
    """It inherited Opus and cost more than research, the PRD and the red team combined."""
    body = (SKILLS / "6-verify/SKILL.md").read_text(encoding="utf-8")
    assert re.search(r"^model: sonnet$", body, re.MULTILINE)
    assert re.search(r"^effort: medium$", body, re.MULTILINE)


def test_no_skill_writes_a_stage_status_row():
    """Stage order is derived from disk, so a hand-written row can only be wrong."""
    offenders = []
    for name, body in stage_bodies():
        for pattern in (r"`gate-open`", r"stage \d+ -> ", r"mark stage \d+"):
            if re.search(pattern, body):
                offenders.append(f"{name}: {pattern}")
    assert not offenders, offenders


@pytest.mark.parametrize("word", RETIRED)
def test_the_retired_vocabulary_is_gone_from_the_plugin_and_its_docs(word):
    """Scoped to the plugin, this scan missed `Local mode` in the walkthrough for a commit.

    Case-insensitively, because the one that survived was a bolded heading and the
    vocabulary here is written lowercase.
    """
    docs = [CLAUDE / "README.md", CLAUDE / "GETTING-STARTED.md"]
    hits = [
        path.relative_to(REPO)
        for path in list(PLUGIN.rglob("*.md")) + docs
        if word.lower() in path.read_text(encoding="utf-8").lower()
    ]
    assert not hits, f"{word!r} still appears in {hits}"


def test_a_stage_running_the_script_is_allowed_to():
    """A Bash call a skill's allowed-tools does not cover is a prompt the user must clear."""
    for name, body in stage_bodies():
        if "pt.py" not in body:
            continue
        assert "Bash(python3 *product-lead/scripts/pt.py *)" in body, name


# --- what pt.py parses out of the templates ---------------------------------


@pytest.mark.parametrize("field", ("Scenarios", "Task groups", "Size hint", "Split rationale", "Depends on", "Needs design seat", "Board issue"))
def test_the_story_template_carries_every_field_the_checker_reads(field):
    """pt.py reads these by name, so a renamed row silently stops being checked."""
    body = (TEMPLATES / "story.md").read_text(encoding="utf-8")
    assert f"| {field} |" in body


def test_the_prd_template_shows_the_shapes_the_checker_matches():
    """A requirement block, a scenario id and a capability line, in the parsed dialect."""
    body = (TEMPLATES / "prd.md").read_text(encoding="utf-8")
    assert "### R{n}:" in body
    assert "SHALL" in body
    assert "#### R{n}.S1" in body
    assert "Capability:" in body
    assert "**WHEN**" in body and "**THEN**" in body


def test_the_task_template_uses_the_checkbox_the_merge_reads():
    body = (TEMPLATES / "tasks.md").read_text(encoding="utf-8")
    assert "- [ ]" in body
    assert "## Deferrals" not in body, "nothing runs after tasks, so every row would be a finding"


def test_every_deferrable_artifact_is_a_real_pipeline_artifact():
    """The ordering vocabulary in pt.py has to match the layout conventions.md documents."""
    source = SCRIPT.read_text(encoding="utf-8")
    layout = CONVENTIONS.read_text(encoding="utf-8")
    declared = re.search(r"^DEFERRABLE = \((.*?)\)$", source, re.MULTILINE | re.DOTALL).group(1)
    names = re.findall(r"[\w.-]+\.md", declared) + ["02-prd.md", "04-ux-spec.md", "05-tasks.md"]
    for name in set(names):
        assert name in layout, f"{name} is deferrable but not in the documented layout"


def test_the_config_template_holds_only_keys_the_pipeline_reads():
    """A key nothing reads is a promise the config cannot keep."""
    config = (TEMPLATES / "config.yml").read_text(encoding="utf-8")
    top_level = {
        line.split(":")[0]
        for line in config.splitlines()
        if line and not line[:1].isspace() and not line.startswith("#") and ":" in line
    }
    assert top_level == {
        "profile",
        "gate_medium",
        "github_repo",
        "project_number",
        "gate_owners",
        "roster",
        "extra_codebase_paths",
        "labels",
    }
    readers = "\n".join(body for _, body in stage_bodies()) + SCRIPT.read_text(encoding="utf-8")
    for key in top_level:
        assert key in readers, f"nothing reads {key}"
