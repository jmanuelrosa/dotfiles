"""A skill runs on its declared model for one agent run, after redirects translate it.

The extension is driven in node against a fake pi, because what is worth asserting is the
sequence it produces: which candidate a bare alias wins, which model a redirect lands on, and
that restore puts the thinking level back after the model rather than before, since pi resets
thinking inside every switch.

Most cases run against FIXTURE_ROUTING so the mechanism stays pinned while the live
model-routing.json changes; the live file is exercised separately through `live=True`.
"""

import json
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest
from dotkit.testing import PI, PI_EXTENSIONS

EXTENSION = PI_EXTENSIONS / "skill-model" / "index.ts"
PI_PACKAGE = "@earendil-works/pi-coding-agent"

CATALOGUE = [
    "openai-codex/gpt-6-astra",
    "openai-codex/gpt-6.1-sol",
    "openai-codex/gpt-6-sol",
    "openai-codex/gpt-6-luna",
    "openai-codex/gpt-5.6-terra",
    "openai-codex/gpt-5.6-sol",
    "openai-codex/gpt-5.6-luna",
    "anthropic/claude-fable-5-1",
    "anthropic/claude-opus-5-5",
    "anthropic/claude-opus-5",
    "anthropic/claude-sonnet-5",
    "anthropic/claude-haiku-4-5",
    "cursor/composer-2-5",
    "cursor/grok-4.7@256k",
    "cursor/grok-4.7@500k",
    "cursor/grok-4.6",
    "cursor/claude-fable-5-1@1m",
    "cursor/claude-fable-5-1@300k",
    "cursor/claude-opus-5@1m",
    "cursor/claude-sonnet-5@1m",
    "cursor/kimi-k3",
    "cursor/future-model@1m",
]
DEFAULT = "openai-codex/gpt-6-sol"
LIVE_ROUTING = json.loads((PI / "model-routing.json").read_text())
FIXTURE_ROUTING = {
    **LIVE_ROUTING,
    "redirects": {"openai-codex/gpt-5.6-terra": "openai-codex/gpt-5.6-luna"},
}

DRIVER = """
const handlers = {};
const calls = {
  setModel: [], setThinkingLevel: [], entries: [], notify: [], status: [], replacements: [],
};
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
  for (const handler of handlers[step.event] ?? []) {
    const result = await handler(step.payload, ctx);
    if (step.event === "message_end" && result?.message) {
      step.payload.message = result.message;
      calls.replacements.push(result.message);
    }
  }
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
    extension = root / "extensions" / "skill-model" / "index.ts"
    extension.parent.mkdir(parents=True)
    extension.write_text(EXTENSION.read_text())
    (root / "model-routing.json").write_text(json.dumps(FIXTURE_ROUTING))
    live_extension = root / "live" / "extensions" / "skill-model" / "index.ts"
    live_extension.parent.mkdir(parents=True)
    live_extension.write_text(EXTENSION.read_text())
    shutil.copyfile(PI / "model-routing.json", root / "live" / "model-routing.json")

    skills = root / "skills"
    for name, frontmatter in {
        "commit": "name: commit\nmodel: opus",
        "cursor-opus": "name: cursor-opus\nmodel: cursor/claude-opus-5@1m",
        "cursor-sonnet": "name: cursor-sonnet\nmodel: cursor/claude-sonnet-5@1m",
        "cursor-fable": "name: cursor-fable\nmodel: cursor/claude-fable-5-1@1m",
        "cursor-composer": "name: cursor-composer\nmodel: cursor/composer-2-5",
        "cursor-grok": "name: cursor-grok\nmodel: cursor/grok-4.6",
        "cursor-grok-new": "name: cursor-grok-new\nmodel: cursor/grok-4.7@256k",
        "anthropic-fable": "name: anthropic-fable\nmodel: anthropic/claude-fable-5-1",
        "cursor-future": "name: cursor-future\nmodel: cursor/future-model@1m",
        "pinned-exactly": "name: pinned-exactly\nmodel: anthropic/claude-sonnet-5",
        "anthropic-opus": "name: anthropic-opus\nmodel: anthropic/claude-opus-5",
        "anthropic-haiku": "name: anthropic-haiku\nmodel: anthropic/claude-haiku-4-5",
        "quoted": 'name: quoted\nmodel: "sonnet"',
        "inheriting": "name: inheriting\nmodel: inherit",
        "unknown-model": "name: unknown-model\nmodel: gemini-9",
        "codex-terra": "name: codex-terra\nmodel: openai-codex/gpt-5.6-terra",
        "anthropic-opus-5-5": "name: anthropic-opus-5-5\nmodel: anthropic/claude-opus-5-5",
        "unpinned": "name: unpinned\ndescription: no model here",
    }.items():
        skill = skills / name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n\nBody.\n")
    return extension, skills, live_extension


def run(
    harness,
    steps,
    *,
    current=DEFAULT,
    thinking="high",
    branch=None,
    unauthenticated=None,
    catalogue=None,
    live=False,
):
    extension, skills, live_extension = harness
    if live:
        extension = live_extension
    scenario = {
        "catalogue": CATALOGUE if catalogue is None else catalogue,
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


STARTED = {"event": "before_agent_start", "payload": {"type": "before_agent_start"}}
SETTLED = {"event": "agent_settled", "payload": {"type": "agent_settled"}}


def assistant_error(error_message, model="claude-sonnet-5", provider="anthropic"):
    return {
        "event": "message_end",
        "payload": {
            "type": "message_end",
            "message": {
                "role": "assistant",
                "content": [],
                "stopReason": "error",
                "errorMessage": error_message,
                "provider": provider,
                "model": model,
            },
        },
    }


def test_enabled_models_limits_cursor_to_the_selected_cursor_models_pool():
    enabled = json.loads((PI / "settings.json").read_text())["enabledModels"]

    routing = json.loads((PI / "model-routing.json").read_text())
    assert {ref for ref in enabled if ref.startswith("cursor/")} == {
        f"cursor/{model}" for model in routing["cursorModels"]
    }
    for alias in ("opus", "sonnet", "haiku"):
        assert any(ref.startswith("anthropic/") and alias in ref for ref in enabled)


def test_default_model_uses_the_codex_subscription():
    settings = json.loads((PI / "settings.json").read_text())

    assert settings["defaultProvider"] == "openai-codex"
    assert settings["defaultModel"] == "gpt-6.1-sol"
    assert f'{settings["defaultProvider"]}/{settings["defaultModel"]}' in settings["enabledModels"]


def test_a_bare_alias_resolves_to_the_first_provider_the_catalogue_declares(harness):
    result = run(harness, [invoke("commit")])

    assert result["setModel"] == ["anthropic/claude-opus-5-5"]
    assert result["entries"] == [{
        "customType": "skill-model",
        "data": {
            "version": 1,
            "state": "pinned",
            "skill": "commit",
            "model": "anthropic/claude-opus-5-5",
            "previousModel": DEFAULT,
            "previousThinking": "high",
        },
    }]


@pytest.mark.parametrize(
    ("skill", "target"),
    [
        ("cursor-opus", "cursor/claude-opus-5@1m"),
        ("cursor-sonnet", "cursor/claude-sonnet-5@1m"),
        ("cursor-fable", "cursor/claude-fable-5-1@1m"),
        ("cursor-grok-new", "cursor/grok-4.7@256k"),
    ],
)
def test_cursor_pins_are_not_redirected(harness, skill, target):
    result = run(harness, [invoke(skill)], current=None)

    assert result["setModel"] == [target]
    assert result["current"] == target
    assert result["notify"] == []
    assert result["entries"][0]["data"]["model"] == target


def test_an_unpinned_agent_without_a_redirect_keeps_its_model(harness):
    source = "cursor/claude-sonnet-5@1m"
    result = run(harness, [STARTED, SETTLED], current=source)

    assert result["setModel"] == []
    assert result["replacements"] == []
    assert result["notify"] == []
    assert result["current"] == source


def test_the_run_ending_restores_the_model_before_the_thinking_level(harness):
    result = run(harness, [invoke("commit"), SETTLED], thinking="medium")

    assert result["setModel"] == ["anthropic/claude-opus-5-5", DEFAULT]
    assert result["setThinkingLevel"] == ["medium"]
    assert result["current"] == DEFAULT
    assert [entry["data"]["state"] for entry in result["entries"]] == ["pinned", "released"]
    assert result["status"] == [
        ["dotfiles-skill-model", "commit on claude-opus-5-5"],
        ["dotfiles-skill-model", None],
    ]


def test_an_explicit_reference_and_a_quoted_alias_both_resolve(harness):
    assert run(harness, [invoke("pinned-exactly")])["setModel"] == ["anthropic/claude-sonnet-5"]
    assert run(harness, [invoke("quoted")])["setModel"] == ["anthropic/claude-sonnet-5"]


def test_a_skill_the_model_reads_itself_is_pinned_too(harness):
    _extension, skills, _live = harness

    result = run(harness, [read(skills, "commit")])

    assert result["setModel"] == ["anthropic/claude-opus-5-5"]


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
        [invoke("cursor-future"), SETTLED],
        unauthenticated=["cursor/future-model@1m"],
    )

    assert result["setModel"] == []
    assert result["entries"] == []
    assert result["current"] == DEFAULT
    assert result["notify"] == [
        ["cursor-future wants cursor/future-model@1m, which has no configured auth", "warning"],
    ]


def test_inherit_and_an_absent_key_are_both_left_unpinned(harness):
    assert run(harness, [invoke("inheriting")])["setModel"] == []
    assert run(harness, [invoke("unpinned")])["setModel"] == []


def test_the_first_pin_of_a_run_owns_the_restore(harness):
    """A second skill inside the same run must not overwrite what the first snapshotted."""
    result = run(harness, [invoke("commit"), invoke("pinned-exactly"), SETTLED])

    assert result["setModel"] == ["anthropic/claude-opus-5-5", DEFAULT]


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


@pytest.mark.parametrize(
    ("skill", "spec"),
    [
        ("commit", "opus"),
        ("quoted", "sonnet"),
        ("anthropic-opus-5-5", "anthropic/claude-opus-5-5"),
        ("anthropic-opus", "anthropic/claude-opus-5"),
        ("pinned-exactly", "anthropic/claude-sonnet-5"),
        ("anthropic-haiku", "anthropic/claude-haiku-4-5"),
        ("anthropic-fable", "anthropic/claude-fable-5-1"),
    ],
)
def test_live_redirects_run_a_pin_on_its_mapped_model_before_any_lookup(harness, skill, spec):
    target = LIVE_ROUTING["redirects"][spec]
    result = run(harness, [invoke(skill), STARTED], current="openai-codex/gpt-5.6-sol", live=True)

    assert result["setModel"] == [target]
    assert result["current"] == target
    assert result["notify"] == []


def test_a_redirect_is_not_limited_to_one_provider(harness):
    result = run(harness, [invoke("codex-terra"), STARTED, SETTLED])

    assert result["setModel"] == ["openai-codex/gpt-5.6-luna", DEFAULT]
    assert result["entries"][0]["data"]["model"] == "openai-codex/gpt-5.6-luna"


def test_an_unpinned_run_on_a_redirected_model_runs_on_its_target_and_restores(harness):
    source = "openai-codex/gpt-5.6-terra"
    result = run(harness, [STARTED, SETTLED], current=source, thinking="medium")

    assert result["setModel"] == ["openai-codex/gpt-5.6-luna", source]
    assert result["setThinkingLevel"] == ["medium"]
    assert result["entries"] == []
    assert result["current"] == source


def test_an_account_error_is_left_to_pi_rather_than_switching_models(harness):
    result = run(
        harness,
        [
            invoke("cursor-composer"),
            STARTED,
            assistant_error("HTTP 429: rate limit exceeded", model="composer-2-5", provider="cursor"),
        ],
    )

    assert result["setModel"] == ["cursor/composer-2-5"]
    assert result["replacements"] == []
