"""A skill runs on its declared model for one agent run, with exact model fallback routes.

The extension is driven in node against a fake pi, because what is worth asserting is the
sequence it produces: which candidate a bare alias wins, when a source model account failure
switches to its mapped Codex model, and that restore puts the thinking level back after the
model rather than before, since pi resets thinking inside every switch.
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
    "openai-codex/gpt-5.6-terra",
    "openai-codex/gpt-5.6-sol",
    "openai-codex/gpt-5.6-luna",
    "anthropic/claude-opus-5",
    "anthropic/claude-sonnet-5",
    "anthropic/claude-haiku-4-5",
    "cursor/claude-opus-5@1m",
    "cursor/claude-sonnet-5@1m",
    "cursor/claude-fable-5@1m",
    "cursor/composer-2-5",
    "cursor/grok-4.6",
    "cursor/gpt-5.6-luna@1m",
    "cursor/gpt-5.6-terra@1m",
    "cursor/gpt-5.6-sol@1m",
    "cursor/future-model@1m",
]
DEFAULT = "openai-codex/gpt-5.6-terra"

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
let retryableReplacements = [];
if (scenario.piAi) {
  const { isRetryableAssistantError } = await import(scenario.piAi);
  retryableReplacements = calls.replacements.map(isRetryableAssistantError);
}
process.stdout.write(JSON.stringify({
  ...calls,
  retryableReplacements,
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
    pi_ai = package / "node_modules" / "@earendil-works" / "pi-ai"
    assert pi_ai.is_dir(), f"{pi_ai} is missing"
    extension = root / "extensions" / "skill-model" / "index.ts"
    extension.parent.mkdir(parents=True)
    extension.write_text(EXTENSION.read_text())
    shutil.copyfile(PI / "model-routing.json", root / "model-routing.json")

    skills = root / "skills"
    for name, frontmatter in {
        "commit": "name: commit\nmodel: opus",
        "cursor-opus": "name: cursor-opus\nmodel: cursor/claude-opus-5@1m",
        "cursor-sonnet": "name: cursor-sonnet\nmodel: cursor/claude-sonnet-5@1m",
        "cursor-fable": "name: cursor-fable\nmodel: cursor/claude-fable-5@1m",
        "cursor-composer": "name: cursor-composer\nmodel: cursor/composer-2-5",
        "cursor-grok": "name: cursor-grok\nmodel: cursor/grok-4.6",
        "cursor-luna": "name: cursor-luna\nmodel: cursor/gpt-5.6-luna@1m",
        "cursor-terra": "name: cursor-terra\nmodel: cursor/gpt-5.6-terra@1m",
        "cursor-sol": "name: cursor-sol\nmodel: cursor/gpt-5.6-sol@1m",
        "cursor-future": "name: cursor-future\nmodel: cursor/future-model@1m",
        "pinned-exactly": "name: pinned-exactly\nmodel: anthropic/claude-sonnet-5",
        "anthropic-opus": "name: anthropic-opus\nmodel: anthropic/claude-opus-5",
        "anthropic-haiku": "name: anthropic-haiku\nmodel: anthropic/claude-haiku-4-5",
        "quoted": 'name: quoted\nmodel: "sonnet"',
        "inheriting": "name: inheriting\nmodel: inherit",
        "unknown-model": "name: unknown-model\nmodel: gemini-9",
        "unpinned": "name: unpinned\ndescription: no model here",
    }.items():
        skill = skills / name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n\nBody.\n")
    return extension, skills, pi_ai / "dist" / "index.js"


def run(
    harness,
    steps,
    *,
    current=DEFAULT,
    thinking="high",
    branch=None,
    unauthenticated=None,
    check_retryable=False,
    catalogue=None,
):
    extension, skills, pi_ai = harness
    scenario = {
        "catalogue": CATALOGUE if catalogue is None else catalogue,
        "current": current,
        "thinking": thinking,
        "branch": branch or [],
        "unauthenticated": unauthenticated or [],
        "piAi": str(pi_ai) if check_retryable else None,
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

    assert {ref for ref in enabled if ref.startswith("cursor/")} == {
        "cursor/composer-2-5",
        "cursor/grok-4.6",
    }
    for alias in ("opus", "sonnet", "haiku"):
        selected = next(ref for ref in enabled if alias in ref)
        assert selected.startswith("anthropic/")


def test_default_model_uses_the_codex_subscription():
    settings = json.loads((PI / "settings.json").read_text())

    assert settings["defaultProvider"] == "openai-codex"
    assert settings["defaultModel"] == "gpt-5.6-terra"
    assert f'{settings["defaultProvider"]}/{settings["defaultModel"]}' in settings["enabledModels"]


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


@pytest.mark.parametrize("cursor_available", [True, False])
@pytest.mark.parametrize(
    ("skill", "target"),
    [
        ("cursor-opus", "anthropic/claude-opus-5"),
        ("cursor-sonnet", "anthropic/claude-sonnet-5"),
        ("cursor-fable", "anthropic/claude-opus-5"),
        ("cursor-luna", "openai-codex/gpt-5.6-luna"),
        ("cursor-terra", "openai-codex/gpt-5.6-terra"),
        ("cursor-sol", "openai-codex/gpt-5.6-sol"),
    ],
)
def test_legacy_cursor_pins_redirect_before_any_request(
    harness, skill, target, cursor_available,
):
    catalogue = [
        ref for ref in CATALOGUE if cursor_available or not ref.startswith("cursor/")
    ]
    result = run(harness, [invoke(skill)], current=None, catalogue=catalogue)

    assert result["setModel"] == [target]
    assert not any(ref.startswith("cursor/") for ref in result["setModel"])
    assert result["current"] == target
    assert result["notify"] == []
    assert result["replacements"] == []
    assert result["entries"][0]["data"]["model"] == target


@pytest.mark.parametrize("tier", ["luna", "terra", "sol"])
def test_redirected_cursor_gpt_has_no_account_error_fallback(harness, tier):
    model = f"gpt-5.6-{tier}"
    target = f"openai-codex/{model}"
    result = run(
        harness,
        [
            invoke(f"cursor-{tier}"),
            assistant_error("Quota exceeded", model=model, provider="openai-codex"),
        ],
        current=None,
    )

    assert result["setModel"] == [target]
    assert result["replacements"] == []


@pytest.mark.parametrize(
    ("skill", "primary", "fallback"),
    [
        ("cursor-opus", "anthropic/claude-opus-5", "openai-codex/gpt-5.6-sol"),
        ("cursor-sonnet", "anthropic/claude-sonnet-5", "openai-codex/gpt-5.6-terra"),
        ("cursor-fable", "anthropic/claude-opus-5", "openai-codex/gpt-5.6-sol"),
        ("anthropic-opus", "anthropic/claude-opus-5", "openai-codex/gpt-5.6-sol"),
        ("pinned-exactly", "anthropic/claude-sonnet-5", "openai-codex/gpt-5.6-terra"),
        ("anthropic-haiku", "anthropic/claude-haiku-4-5", "openai-codex/gpt-5.6-luna"),
    ],
)
def test_an_absent_exact_primary_starts_on_its_fallback(harness, skill, primary, fallback):
    result = run(
        harness,
        [invoke(skill)],
        current=None,
        catalogue=[ref for ref in CATALOGUE if ref != primary],
    )

    assert result["setModel"] == [fallback]
    assert result["current"] == fallback
    assert result["entries"][0]["data"]["model"] == fallback
    assert result["notify"] == [[
        f"{skill}: {primary} is unavailable; using {fallback}",
        "warning",
    ]]


def test_an_account_limit_retries_the_skill_turn_on_its_mapped_model(harness):
    result = run(
        harness,
        [
            invoke("cursor-sonnet"),
            STARTED,
            assistant_error("Monthly usage limit reached"),
            SETTLED,
        ],
        check_retryable=True,
    )

    assert result["setModel"] == [
        "anthropic/claude-sonnet-5",
        "openai-codex/gpt-5.6-terra",
        DEFAULT,
    ]
    assert result["replacements"] == [{
        "role": "assistant",
        "content": [],
        "stopReason": "error",
        "errorMessage": (
            "Provider returned error: retrying cursor-sonnet with "
            "openai-codex/gpt-5.6-terra"
        ),
        "provider": "anthropic",
        "model": "claude-sonnet-5",
    }]
    assert result["status"] == [
        ["dotfiles-skill-model", "cursor-sonnet on claude-sonnet-5"],
        ["dotfiles-skill-model", "cursor-sonnet on gpt-5.6-terra"],
        ["dotfiles-skill-model", None],
    ]
    assert result["retryableReplacements"] == [True]


def test_an_unpinned_agent_run_retries_on_its_mapped_model(harness):
    primary = "anthropic/claude-haiku-4-5"
    fallback = "openai-codex/gpt-5.6-luna"
    result = run(
        harness,
        [
            STARTED,
            assistant_error(
                "This request would exceed your account's monthly spend limit",
                model="claude-haiku-4-5",
                provider="anthropic",
            ),
            SETTLED,
        ],
        current=primary,
        thinking="medium",
        check_retryable=True,
    )

    assert result["setModel"] == [fallback, primary]
    assert result["setThinkingLevel"] == ["medium"]
    assert result["replacements"] == [{
        "role": "assistant",
        "content": [],
        "stopReason": "error",
        "errorMessage": f"Provider returned error: retrying agent run with {fallback}",
        "provider": "anthropic",
        "model": "claude-haiku-4-5",
    }]
    assert result["notify"] == [[
        f"agent run: anthropic account or capacity failure; retrying with {fallback}",
        "warning",
    ]]
    assert result["retryableReplacements"] == [True]
    assert result["entries"] == []
    assert result["status"] == []
    assert result["current"] == primary


def test_an_unpinned_agent_redirects_before_its_first_request(harness):
    source = "cursor/claude-sonnet-5@1m"
    target = "anthropic/claude-sonnet-5"
    result = run(harness, [STARTED, SETTLED], current=source)

    assert result["setModel"] == [target, source]
    assert result["replacements"] == []
    assert result["notify"] == []
    assert result["current"] == source


def test_an_unpinned_agent_without_a_route_keeps_normal_error_handling(harness):
    result = run(
        harness,
        [
            STARTED,
            assistant_error(
                "Quota exceeded",
                model="gpt-5.6-terra",
                provider="openai-codex",
            ),
            SETTLED,
        ],
    )

    assert result["setModel"] == []
    assert result["replacements"] == []
    assert result["notify"] == []


def test_an_unpinned_agent_keeps_network_errors_on_the_normal_retry_path(harness):
    primary = "anthropic/claude-haiku-4-5"
    result = run(
        harness,
        [
            STARTED,
            assistant_error(
                "Network error: connection reset",
                model="claude-haiku-4-5",
                provider="anthropic",
            ),
            SETTLED,
        ],
        current=primary,
    )

    assert result["setModel"] == []
    assert result["replacements"] == []
    assert result["current"] == primary


def test_an_unpinned_agent_skips_an_unavailable_fallback(harness):
    primary = "anthropic/claude-haiku-4-5"
    fallback = "openai-codex/gpt-5.6-luna"
    result = run(
        harness,
        [
            STARTED,
            assistant_error(
                "HTTP 429: rate limit exceeded",
                model="claude-haiku-4-5",
                provider="anthropic",
            ),
            SETTLED,
        ],
        current=primary,
        unauthenticated=[fallback],
    )

    assert result["setModel"] == []
    assert result["replacements"] == []
    assert result["current"] == primary


@pytest.mark.parametrize(
    ("skill", "provider", "model", "fallback"),
    [
        ("cursor-opus", "anthropic", "claude-opus-5", "openai-codex/gpt-5.6-sol"),
        ("cursor-sonnet", "anthropic", "claude-sonnet-5", "openai-codex/gpt-5.6-terra"),
        ("cursor-fable", "anthropic", "claude-opus-5", "openai-codex/gpt-5.6-sol"),
        ("anthropic-opus", "anthropic", "claude-opus-5", "openai-codex/gpt-5.6-sol"),
        ("pinned-exactly", "anthropic", "claude-sonnet-5", "openai-codex/gpt-5.6-terra"),
        ("cursor-composer", "cursor", "composer-2-5", "openai-codex/gpt-5.6-luna"),
        ("cursor-grok", "cursor", "grok-4.6", "openai-codex/gpt-5.6-terra"),
        ("anthropic-haiku", "anthropic", "claude-haiku-4-5", "openai-codex/gpt-5.6-luna"),
    ],
)
def test_each_source_model_retries_on_its_exact_fallback(
    harness, skill, provider, model, fallback,
):
    result = run(
        harness,
        [invoke(skill), assistant_error("HTTP 429: rate limit exceeded", model, provider)],
    )

    assert result["setModel"] == [f"{provider}/{model}", fallback]


def test_a_bare_alias_uses_the_route_for_the_model_it_resolves_to(harness):
    result = run(
        harness,
        [
            invoke("commit"),
            assistant_error("Quota exceeded", model="claude-opus-5", provider="anthropic"),
        ],
    )

    assert result["setModel"] == [
        "anthropic/claude-opus-5",
        "openai-codex/gpt-5.6-sol",
    ]


@pytest.mark.parametrize(
    "error_message",
    [
        "Cursor SDK API key is unauthorized",
        "HTTP 429: rate limit exceeded",
        "Quota exceeded for this subscription",
        "Spend limit reached",
    ],
)
def test_account_and_capacity_errors_use_the_exact_fallback(harness, error_message):
    result = run(
        harness,
        [invoke("cursor-sonnet"), assistant_error(error_message)],
    )

    assert result["setModel"] == [
        "anthropic/claude-sonnet-5",
        "openai-codex/gpt-5.6-terra",
    ]


def test_a_mapped_pin_without_auth_starts_directly_on_its_fallback(harness):
    previous = "openai-codex/gpt-5.6-sol"
    result = run(
        harness,
        [invoke("cursor-sonnet"), SETTLED],
        current=previous,
        unauthenticated=["anthropic/claude-sonnet-5"],
    )

    assert result["setModel"] == ["openai-codex/gpt-5.6-terra", previous]
    assert result["notify"] == [[
        (
            "cursor-sonnet: anthropic/claude-sonnet-5 is unavailable; "
            "using openai-codex/gpt-5.6-terra"
        ),
        "warning",
    ]]


def test_an_unmapped_model_has_no_fallback(harness):
    result = run(
        harness,
        [
            invoke("cursor-future"),
            assistant_error("Too many requests", model="future-model@1m", provider="cursor"),
        ],
    )

    assert result["setModel"] == ["cursor/future-model@1m"]
    assert result["replacements"] == []


@pytest.mark.parametrize(
    "error_message",
    [
        "Network error: connection reset",
        "HTTP 503: service unavailable",
        "Provider returned error: Cursor SDK run failed",
    ],
)
def test_other_cursor_errors_stay_on_the_normal_retry_path(harness, error_message):
    result = run(
        harness,
        [
            invoke("cursor-composer"),
            assistant_error(error_message, model="composer-2-5", provider="cursor"),
        ],
    )

    assert result["setModel"] == ["cursor/composer-2-5"]
    assert result["replacements"] == []


def test_fallback_works_when_the_skill_model_is_already_selected(harness):
    primary = "anthropic/claude-sonnet-5"
    result = run(
        harness,
        [invoke("cursor-sonnet"), assistant_error("Usage limit reached"), SETTLED],
        current=primary,
    )

    assert result["setModel"] == ["openai-codex/gpt-5.6-terra", primary]
    assert [entry["data"]["state"] for entry in result["entries"]] == [
        "pinned",
        "released",
    ]


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
    _extension, skills, _pi_ai = harness

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


def test_a_failed_unmapped_switch_records_no_pin_so_the_run_end_restores_nothing(harness):
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
