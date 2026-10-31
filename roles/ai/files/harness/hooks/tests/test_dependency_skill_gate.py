"""`dependency-skill-gate.sh` refuses a prompt that invokes a dependency-only skill directly.

The hook reads a UserPromptSubmit event on stdin and exits 2 to refuse. The registry is a
fixture reached through AGENT_CATALOG, the same variable harnessgen reads, so a test run
never depends on the catalog this machine happens to have linked.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from harnessgen import emit_claude

HOOK = Path(__file__).resolve().parents[1] / "dependency-skill-gate.sh"

REGISTRY = {
    "upstream": {
        "example/skills": {
            "skills": [
                {"upstream_path": "skills/grilling", "dependency_only": True},
                {"upstream_path": "skills/grill-me", "dependencies": ["grilling"]},
                {"upstream_path": "skills/upstream-name", "name": "renamed-dep", "dependency_only": True},
            ],
        },
    },
    "local": [
        {"name": "to-plan", "dependencies": ["grilling"]},
        {"name": "why", "dependency_only": True},
    ],
}

REFUSED = 2


@pytest.fixture
def catalog(tmp_path):
    (tmp_path / "skill-registry.json").write_text(json.dumps(REGISTRY))
    return tmp_path


def gate(prompt, catalog_dir, raw=None):
    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input=raw if raw is not None else json.dumps({"hook_event_name": "UserPromptSubmit", "prompt": prompt}),
        capture_output=True,
        text=True,
        env={"AGENT_CATALOG": str(catalog_dir), "PATH": "/usr/bin:/bin"},
    )
    return result.returncode, result.stderr


@pytest.mark.parametrize(
    "prompt",
    [
        "/grilling",
        "/grilling the auth plan",
        "  /grilling",
        "/skill:grilling the auth plan",
        "$grilling the auth plan",
        "please run $grilling on this",
        "/renamed-dep",
        "/why",
    ],
)
def test_a_direct_invocation_is_refused(catalog, prompt):
    code, _ = gate(prompt, catalog)
    assert code == REFUSED


@pytest.mark.parametrize(
    "prompt",
    [
        "/grill-me",
        "/grilling-notes",
        "/skill:grilling-notes",
        "why does grilling exist",
        "explain /grilling to me",
        "price$grilling",
        "/upstream-name",
        "",
    ],
)
def test_anything_else_is_allowed(catalog, prompt):
    code, stderr = gate(prompt, catalog)
    assert code == 0, stderr


def test_the_refusal_names_the_skills_to_run_instead(catalog):
    _, stderr = gate("/grilling", catalog)
    assert "grill-me" in stderr
    assert "to-plan" in stderr


def test_a_missing_registry_fails_open(tmp_path):
    code, _ = gate("/grilling", tmp_path)
    assert code == 0


def test_an_unreadable_registry_fails_open(tmp_path):
    (tmp_path / "skill-registry.json").write_text("not json")
    code, _ = gate("/grilling", tmp_path)
    assert code == 0


@pytest.mark.parametrize("raw", ["not json", "[]", json.dumps({"prompt": 3})])
def test_a_malformed_payload_fails_open(catalog, raw):
    code, _ = gate("", catalog, raw=raw)
    assert code == 0


def test_the_hook_refuses_exactly_what_claude_renders_name_only(catalog):
    """harnessgen derives the same set for skillOverrides; the two must not drift."""
    rendered = set(emit_claude.dependency_only_skills(REGISTRY))
    refused = {name for name in ("grilling", "renamed-dep", "why", "grill-me", "to-plan", "upstream-name")
               if gate(f"/{name}", catalog)[0] == REFUSED}
    assert refused == rendered
