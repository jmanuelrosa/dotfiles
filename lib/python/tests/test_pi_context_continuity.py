"""The continuity extension records a model switch without rewriting the conversation.

Pi already keeps one session branch across `/model`. What it does not keep is a record that
the next request is a projection of that branch, not the same effective context. This suite
drives the extension the way pi loads it: one default export, event handlers, `appendEntry`
for state that must survive resume, and `notify` for a loss the user can act on. The payload
is metadata. A prompt, an image, or a thinking block in that payload would be the feature
logging the conversation it exists only to describe.
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from dotkit.testing import PI_EXTENSIONS, REPO

EXTENSION = PI_EXTENSIONS / "context-continuity.ts"
TASKS = REPO / "roles/ai/tasks/main.yml"
PACKAGE = "@earendil-works/pi-coding-agent"

SOL = {
    "id": "gpt-5.6-sol",
    "provider": "cursor",
    "api": "openai-completions",
    "contextWindow": 200_000,
    "input": ["text", "image"],
}
GROK = {
    "id": "grok-4.6",
    "provider": "xai",
    "api": "openai-completions",
    "contextWindow": 500_000,
    "input": ["text"],
}
COMPOSER = {
    "id": "composer-2-5",
    "provider": "cursor",
    "api": "openai-completions",
    "contextWindow": 200_000,
    "input": ["text"],
}


@pytest.fixture(scope="module")
def source():
    return EXTENSION.read_text()


@pytest.fixture(scope="module")
def dist():
    binary = shutil.which("pi")
    if binary is None:
        pytest.skip("pi is needed to check the extension against its own API")
    root = Path_or_skip(binary)
    if root is None:
        pytest.skip(f"no {PACKAGE} dist beside {binary}")
    return root


def Path_or_skip(binary):
    resolved = Path(binary).resolve().parent.parent
    for prefix in ("lib/node_modules", "libexec/lib/node_modules"):
        found = resolved / prefix / PACKAGE / "dist"
        if found.is_dir():
            return found
    return None


def imported(source):
    block = re.search(rf'import (?:type )?\{{([^}}]*)\}} from "{re.escape(PACKAGE)}"', source, re.S)
    assert block, "the extension must import from pi by package name"
    return {
        name.replace("type ", "").strip() for name in block.group(1).split(",") if name.strip()
    }


def test_every_imported_name_is_exported_by_pi(source, dist):
    exports = (dist / "index.d.ts").read_text()
    for name in imported(source):
        assert name in exports, f"{name} is not exported by {PACKAGE}"


def test_the_extension_uses_public_hooks_not_private_dist_modules(source):
    assert 'from "@earendil-works/pi-coding-agent"' in source
    assert "/dist/" not in source
    assert "transform-messages" not in source
    assert "compaction.js" not in source


def test_the_role_installs_the_extension():
    assert "files/pi/extensions/*.ts" in TASKS.read_text()


@pytest.fixture(scope="module")
def runner(dist, tmp_path_factory):
    if shutil.which("node") is None:
        pytest.skip("node is needed to execute the extension")
    home = tmp_path_factory.mktemp("continuity")
    (home / "node_modules").symlink_to(dist.parents[2])
    (home / "context-continuity.ts").write_text(EXTENSION.read_text())
    return home


def run_events(runner, script):
    done = subprocess.run(
        [shutil.which("node"), "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        cwd=runner,
        env={**os.environ},
        check=False,
    )
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def drive(branch, model, previous=None, source="set", prompt="SYSTEM", tools=None, extra=""):
    return f"""
import continuity from "./context-continuity.ts";

const entries = [];
const notifications = [];
const handlers = {{}};
const pi = {{
  on(event, handler) {{ handlers[event] = handler; }},
  appendEntry(customType, data) {{ entries.push({{ customType, data }}); }},
  getActiveTools() {{ return {json.dumps(tools or ["read", "bash"])}; }},
}};
continuity(pi);

const branch = {json.dumps(branch)};
const ctx = {{
  model: {json.dumps(model)},
  getSystemPrompt: () => {json.dumps(prompt)},
  sessionManager: {{
    getSessionId: () => "session-1",
    getLeafId: () => branch.at(-1)?.id ?? null,
    getBranch: () => branch,
    getEntries: () => branch,
  }},
  ui: {{ notify: (message, type) => notifications.push({{ message, type }}) }},
}};
await handlers.session_start?.({{}}, ctx);
await handlers.model_select?.( {{
  source: {json.dumps(source)},
  model: {json.dumps(model)},
  previousModel: {json.dumps(previous)},
}}, ctx);
{extra}
process.stdout.write(JSON.stringify({{ entries, notifications }}));
"""


def entry(entry_id, entry_type, **fields):
    return {"id": entry_id, "type": entry_type, **fields}


def message(entry_id, role, **message_fields):
    return entry(entry_id, "message", message={"role": role, **message_fields})


def test_an_explicit_switch_appends_one_versioned_projection(runner):
    result = run_events(
        runner,
        drive(
            [message("m1", "user", content="hello"), message("m2", "assistant", content="hi")],
            GROK,
            previous=SOL,
            source="set",
        ),
    )
    assert len(result["entries"]) == 1
    payload = result["entries"][0]
    assert payload["customType"] == "context-continuity"
    data = payload["data"]
    assert data["version"] == 1
    assert data["event"] == "model-switch"
    assert data["source"] == "set"
    assert data["usageQuality"] == "unknown"
    assert data["activeModel"]["id"] == "grok-4.6"
    assert data["previousModel"]["id"] == "gpt-5.6-sol"
    assert data["logicalContext"]["sessionId"] == "session-1"
    assert data["logicalContext"]["contextEntryId"] == "m2"


def test_restore_does_not_append_a_duplicate_entry(runner):
    existing = entry(
        "c1",
        "custom",
        customType="context-continuity",
        data={"version": 1, "event": "model-switch", "degradations": []},
    )
    result = run_events(
        runner,
        drive(
            [message("m1", "user", content="hello"), existing],
            GROK,
            previous=SOL,
            source="restore",
        ),
    )
    assert result["entries"] == []


def test_repeated_context_events_do_not_repeat_the_notification(runner):
    image = {"type": "image", "source": {"type": "base64", "mediaType": "image/png", "data": "abc"}}
    branch = [message("m1", "user", content=[image, {"type": "text", "text": "look"}])]
    extra = """
    const messages = [{ role: "user", content: [{ type: "image" }, { type: "text", text: "look" }] }];
    await handlers.context?.({ messages }, ctx);
    await handlers.context?.({ messages }, ctx);
    """
    result = run_events(runner, drive(branch, COMPOSER, previous=SOL, extra=extra))
    assert len(result["notifications"]) == 1
    assert "image" in result["notifications"][0]["message"].lower()
    assert "composer-2-5" in result["notifications"][0]["message"]


def test_a_text_only_model_reports_images_in_user_and_tool_content(runner):
    image = {"type": "image", "source": {"type": "base64", "mediaType": "image/png", "data": "abc"}}
    branch = [
        message("m1", "user", content=[image]),
        message("m2", "assistant", content=[{"type": "toolCall", "id": "c1", "name": "read"}]),
        message("m3", "toolResult", toolCallId="c1", toolName="read", content=[image]),
    ]
    result = run_events(runner, drive(branch, COMPOSER, previous=SOL))
    assert "images-unsupported" in result["entries"][0]["data"]["degradations"]


def test_same_model_replay_does_not_report_opaque_reasoning_loss(runner):
    thinking = {"type": "thinking", "thinking": "private", "redacted": True, "thinkingSignature": "sig"}
    branch = [
        message(
            "m1",
            "assistant",
            provider=SOL["provider"],
            api=SOL["api"],
            model=SOL["id"],
            content=[thinking],
        )
    ]
    result = run_events(runner, drive(branch, SOL, previous=None, source="set"))
    assert "opaque-reasoning-unavailable" not in result["entries"][0]["data"]["degradations"]
    assert result["notifications"] == []


def test_cross_model_replay_reports_opaque_reasoning_without_its_content(runner):
    thinking = {"type": "thinking", "thinking": "secret plan", "redacted": True, "thinkingSignature": "sig"}
    branch = [
        message(
            "m1",
            "assistant",
            provider=SOL["provider"],
            api=SOL["api"],
            model=SOL["id"],
            content=[thinking],
        )
    ]
    result = run_events(runner, drive(branch, GROK, previous=SOL))
    data = result["entries"][0]["data"]
    assert "opaque-reasoning-unavailable" in data["degradations"]
    dumped = json.dumps(data)
    assert "secret plan" not in dumped
    assert "sig" not in dumped
    assert "secret plan" not in result["notifications"][0]["message"]


def test_orphaned_tool_calls_are_detected(runner):
    branch = [
        message(
            "m1",
            "assistant",
            content=[{"type": "toolCall", "id": "c1", "name": "bash", "arguments": {"command": "ls"}}],
        )
    ]
    result = run_events(runner, drive(branch, GROK, previous=SOL))
    assert "orphaned-tool-result-synthesized" in result["entries"][0]["data"]["degradations"]
    dumped = json.dumps(result["entries"][0]["data"])
    assert "command" not in dumped
    assert '"ls"' not in dumped


def test_a_smaller_window_is_reported_once(runner):
    result = run_events(runner, drive([message("m1", "user", content="hi")], SOL, previous=GROK))
    assert "smaller-context-window" in result["entries"][0]["data"]["degradations"]


def test_persisted_projection_holds_no_prompt_or_message_text(runner):
    prompt = "UNIQUE-SYSTEM-PROMPT-DO-NOT-STORE"
    branch = [message("m1", "user", content="UNIQUE-USER-TEXT-DO-NOT-STORE")]
    result = run_events(runner, drive(branch, GROK, previous=SOL, prompt=prompt))
    dumped = json.dumps(result["entries"][0]["data"])
    assert prompt not in dumped
    assert "UNIQUE-USER-TEXT-DO-NOT-STORE" not in dumped
    assert re.fullmatch(r"[0-9a-f]{16,}", result["entries"][0]["data"]["logicalContext"]["systemPromptHash"])
    assert re.fullmatch(r"[0-9a-f]{16,}", result["entries"][0]["data"]["logicalContext"]["activeToolsHash"])
