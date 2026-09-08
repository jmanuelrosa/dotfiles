"""A skill that declares a model runs on it, for one agent run, or not at all.

The extension is driven in node against a fake pi, because what is worth asserting is the
sequence it produces: which candidate a bare alias wins, that a failed switch changes
nothing, and that the restore puts the thinking level back after the model rather than
before, since pi resets thinking inside every switch.
"""

import json
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest
from dotkit.testing import PI_EXTENSIONS

EXTENSION = PI_EXTENSIONS / "skill-model.ts"
PI_PACKAGE = "@earendil-works/pi-coding-agent"

# Mirrors the shape and order of `enabledModels` in pi/settings.json: anthropic is declared
# ahead of cursor, so a bare `opus` must land on anthropic.
CATALOGUE = [
    "openai-codex/gpt-5.6-terra",
    "anthropic/claude-opus-5",
    "anthropic/claude-sonnet-5",
    "cursor/claude-opus-5@1m",
]
DEFAULT = "openai-codex/gpt-5.6-terra"

DRIVER = """
const handlers = {};
const calls = { setModel: [], setThinkingLevel: [], entries: [], notify: [], status: [] };
const catalogue = scenario.catalogue.map((ref) => {
  const cut = ref.indexOf("/");
  return { provider: ref.slice(0, cut), id: ref.slice(cut + 1) };
});
const byRef = (ref) => catalogue.find((model) => model.provider + "/" + model.id === ref);
let current = scenario.current ? byRef(scenario.current) : null;
let thinking = scenario.thinking;

const pi = {
  on: (event, handler) => { (handlers[event] ??= []).push(handler); },
  setModel: async (model) => {
    const ref = model.provider + "/" + model.id;
    if ((scenario.unauthenticated ?? []).includes(ref)) return false;
    calls.setModel.push(ref);
    current = model;
    return true;
  },
  getThinkingLevel: () => thinking,
  setThinkingLevel: (level) => { thinking = level; calls.setThinkingLevel.push(level); },
  appendEntry: (customType, data) => { calls.entries.push({ customType, data }); },
  getCommands: () => scenario.commands ?? [],
};

const ctx = {
  get model() { return current; },
  scopedModels: catalogue.map((model) => ({ model })),
  modelRegistry: {
    getAvailable: () => catalogue,
    find: (provider, id) => catalogue.find((m) => m.provider === provider && m.id === id),
  },
  ui: {
    notify: (message, level) => { calls.notify.push([message, level]); },
    setStatus: (key, text) => { calls.status.push([key, text ?? null]); },
    theme: { fg: (_token, text) => text },
  },
  sessionManager: { getBranch: () => scenario.branch ?? [] },
};

register(pi);
for (const step of scenario.steps) {
  for (const handler of handlers[step.event] ?? []) await handler(step.payload, ctx);
}
process.stdout.write(JSON.stringify({
  ...calls,
  current: current ? current.provider + "/" + current.id : null,
  thinking,
}));
"""


def pi_package():
    binary = shutil.which("pi")
    if binary is None:
        return None
    root = Path(binary).resolve().parent.parent
    for candidate in (
        root / "lib/node_modules" / PI_PACKAGE,
        root / "libexec/lib/node_modules" / PI_PACKAGE,
    ):
        if candidate.is_dir():
            return candidate
    return None


@pytest.fixture(scope="module")
def harness(tmp_path_factory):
    package = pi_package()
    if package is None or shutil.which("node") is None:
        pytest.skip("pi and node are needed to execute the extension")
    assert EXTENSION.is_file(), f"{EXTENSION} is missing"

    root = tmp_path_factory.mktemp("skill-model")
    scope = root / "node_modules" / "@earendil-works"
    scope.mkdir(parents=True)
    (scope / "pi-coding-agent").symlink_to(package)
    extension = root / "skill-model.ts"
    extension.write_text(EXTENSION.read_text())

    skills = root / "skills"
    for name, frontmatter in {
        "commit": "name: commit\nmodel: opus",
        "pinned-exactly": "name: pinned-exactly\nmodel: anthropic/claude-sonnet-5",
        "quoted": 'name: quoted\nmodel: "sonnet"',
        "inheriting": "name: inheriting\nmodel: inherit",
        "unknown-model": "name: unknown-model\nmodel: gemini-9",
        "unpinned": "name: unpinned\ndescription: no model here",
    }.items():
        skill = skills / name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n\nBody.\n")
    return extension, skills


def run(harness, steps, *, current=DEFAULT, thinking="high", branch=None, unauthenticated=None):
    extension, skills = harness
    scenario = {
        "catalogue": CATALOGUE,
        "current": current,
        "thinking": thinking,
        "branch": branch or [],
        "unauthenticated": unauthenticated or [],
        "commands": [
            {
                "name": f"skill:{path.parent.name}",
                "source": "skill",
                "sourceInfo": {"path": str(path)},
            }
            for path in sorted(skills.glob("*/SKILL.md"))
        ],
        "steps": steps,
    }
    script = textwrap.dedent(f"""
      import register from {json.dumps(str(extension))};
      const scenario = {json.dumps(scenario)};
    """) + DRIVER
    result = subprocess.run(
        [shutil.which("node"), "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def invoke(name):
    return {
        "event": "input",
        "payload": {"type": "input", "text": f"/skill:{name}", "source": "interactive"},
    }


def read(skills, name):
    return {
        "event": "tool_result",
        "payload": {
            "type": "tool_result",
            "toolName": "read",
            "isError": False,
            "input": {"path": str(skills / name / "SKILL.md")},
        },
    }


SETTLED = {"event": "agent_settled", "payload": {"type": "agent_settled"}}


def test_a_bare_alias_resolves_to_the_first_provider_the_catalogue_declares(harness):
    result = run(harness, [invoke("commit")])

    assert result["setModel"] == ["anthropic/claude-opus-5"]
    assert result["entries"] == [{
        "customType": "skill-model",
        "data": {
            "version": 1,
            "state": "pinned",
            "skill": "commit",
            "model": "anthropic/claude-opus-5",
            "previousModel": DEFAULT,
            "previousThinking": "high",
        },
    }]


def test_the_run_ending_restores_the_model_before_the_thinking_level(harness):
    result = run(harness, [invoke("commit"), SETTLED], thinking="medium")

    assert result["setModel"] == ["anthropic/claude-opus-5", DEFAULT]
    assert result["setThinkingLevel"] == ["medium"]
    assert result["current"] == DEFAULT
    assert [entry["data"]["state"] for entry in result["entries"]] == ["pinned", "released"]
    assert result["status"] == [
        ["dotfiles-skill-model", "commit on claude-opus-5"],
        ["dotfiles-skill-model", None],
    ]


def test_an_explicit_reference_and_a_quoted_alias_both_resolve(harness):
    assert run(harness, [invoke("pinned-exactly")])["setModel"] == ["anthropic/claude-sonnet-5"]
    assert run(harness, [invoke("quoted")])["setModel"] == ["anthropic/claude-sonnet-5"]


def test_a_skill_the_model_reads_itself_is_pinned_too(harness):
    _extension, skills = harness

    result = run(harness, [read(skills, "commit")])

    assert result["setModel"] == ["anthropic/claude-opus-5"]


def test_a_model_no_enabled_entry_matches_leaves_the_session_alone(harness):
    result = run(harness, [invoke("unknown-model"), SETTLED])

    assert result["setModel"] == []
    assert result["entries"] == []
    assert result["status"] == []
    assert result["notify"] == [
        ['unknown-model wants "gemini-9", which no enabled model matches', "warning"],
    ]


def test_a_failed_switch_records_no_pin_so_the_run_end_restores_nothing(harness):
    result = run(
        harness,
        [invoke("commit"), SETTLED],
        unauthenticated=["anthropic/claude-opus-5"],
    )

    assert result["setModel"] == []
    assert result["entries"] == []
    assert result["current"] == DEFAULT
    assert result["notify"] == [
        ["commit wants anthropic/claude-opus-5, which has no configured auth", "warning"],
    ]


def test_inherit_and_an_absent_key_are_both_left_unpinned(harness):
    assert run(harness, [invoke("inheriting")])["setModel"] == []
    assert run(harness, [invoke("unpinned")])["setModel"] == []


def test_the_first_pin_of_a_run_owns_the_restore(harness):
    """A second skill inside the same run must not overwrite what the first snapshotted."""
    result = run(harness, [invoke("commit"), invoke("pinned-exactly"), SETTLED])

    assert result["setModel"] == ["anthropic/claude-opus-5", DEFAULT]


def test_resuming_a_session_pinned_mid_run_is_not_stranded_on_the_pinned_model(harness):
    pin = {
        "version": 1,
        "state": "pinned",
        "skill": "commit",
        "model": "anthropic/claude-opus-5",
        "previousModel": DEFAULT,
        "previousThinking": "low",
    }
    result = run(
        harness,
        [{"event": "session_start", "payload": {"type": "session_start", "reason": "resume"}}],
        current="anthropic/claude-opus-5",
        branch=[{"type": "custom", "customType": "skill-model", "data": pin}],
    )

    assert result["setModel"] == [DEFAULT]
    assert result["setThinkingLevel"] == ["low"]
    assert [entry["data"]["state"] for entry in result["entries"]] == ["released"]
