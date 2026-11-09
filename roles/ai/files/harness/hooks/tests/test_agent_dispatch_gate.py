"""`agent-dispatch-gate.sh` lets a parent-only worker be spawned by its parent and nobody else.

The gate reads the target agent's `dispatched-by` frontmatter from the catalog, so the
cases build a throwaway catalog and point `AGENT_CATALOG` at it. Cases assert on the tier
alone, never on the wording.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / "agent-dispatch-gate.sh"

ALLOW, BLOCK = "allow", "block"

WORKER = "code-review-worker"
PARENT = "code-reviewer"

AGENTS = {
    WORKER: f"---\nname: {WORKER}\ndescription: one sample\ndispatched-by: [{PARENT}]\n---\n\nbody\n",
    "block-worker": "---\nname: block-worker\ndescription: one sample\ndispatched-by:\n  - architect\n  - code-reviewer\n---\n",
    PARENT: f"---\nname: {PARENT}\ndescription: reviewer\ntools: Read, Agent\n---\n",
    "decision-judge": "---\nname: decision-judge\ndescription: judge\n---\n",
}


@pytest.fixture
def catalog(tmp_path):
    agents = tmp_path / "agents"
    agents.mkdir()
    for name, text in AGENTS.items():
        (agents / f"{name}.md").write_text(text, encoding="utf-8")
    return tmp_path


def tier(catalog, tool_input, caller=None, raw=None):
    payload = raw if raw is not None else json.dumps(
        {"tool_name": "Agent", "tool_input": tool_input, "cwd": str(catalog), **({"agent_type": caller} if caller else {})}
    )
    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        env={**os.environ, "AGENT_CATALOG": str(catalog), "HOME": str(catalog)},
    )
    if result.returncode == 2:
        assert result.stderr.strip(), "a refusal must say why"
        return BLOCK
    assert result.returncode == 0, result.stderr
    return ALLOW


def test_the_main_conversation_cannot_spawn_a_worker(catalog):
    assert tier(catalog, {"subagent_type": WORKER, "prompt": "review this"}) == BLOCK


def test_the_named_parent_can(catalog):
    assert tier(catalog, {"subagent_type": WORKER, "prompt": "S1 behaviour"}, caller=PARENT) == ALLOW


def test_another_agent_cannot(catalog):
    assert tier(catalog, {"subagent_type": WORKER}, caller="architect") == BLOCK


def test_a_block_list_names_every_parent(catalog):
    assert tier(catalog, {"subagent_type": "block-worker"}, caller="architect") == ALLOW
    assert tier(catalog, {"subagent_type": "block-worker"}, caller=PARENT) == ALLOW
    assert tier(catalog, {"subagent_type": "block-worker"}) == BLOCK


def test_an_agent_without_the_key_is_not_gated(catalog):
    assert tier(catalog, {"subagent_type": "decision-judge"}) == ALLOW
    assert tier(catalog, {"subagent_type": PARENT}) == ALLOW


def test_an_unknown_agent_is_not_gated(catalog):
    assert tier(catalog, {"subagent_type": "Explore"}) == ALLOW


def test_a_pi_workflow_naming_the_worker_is_gated(catalog):
    script = f'await runs.all([{{ key: "s1", agent: "{WORKER}", task: "behaviour" }}]);'
    assert tier(catalog, {"workflow": script}) == BLOCK
    assert tier(catalog, {"workflow": script}, caller=PARENT) == ALLOW


def test_a_pi_workflow_with_a_similar_name_is_not_gated(catalog):
    script = f'await runs.run({{ agent: "{WORKER}-v2", task: "x" }});'
    assert tier(catalog, {"workflow": script}) == ALLOW


def test_the_project_agent_dir_is_read_too(catalog, tmp_path):
    project = tmp_path / "project"
    (project / ".claude" / "agents").mkdir(parents=True)
    (project / ".claude" / "agents" / "local-worker.md").write_text(
        "---\nname: local-worker\ndispatched-by: [lead]\n---\n", encoding="utf-8"
    )
    payload = json.dumps({"tool_name": "Agent", "tool_input": {"subagent_type": "local-worker"}, "cwd": str(project)})
    assert tier(catalog, None, raw=payload) == BLOCK


@pytest.mark.parametrize("raw", ["", "not json", json.dumps({"tool_name": "Agent", "tool_input": "x"}), json.dumps({})])
def test_malformed_input_fails_open(catalog, raw):
    assert tier(catalog, None, raw=raw) == ALLOW
