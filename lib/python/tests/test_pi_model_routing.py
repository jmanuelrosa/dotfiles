"""Subscription routing blocks Cursor's other models before their transport is called."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from dotkit.testing import PI, PLUGINS, SKILLS


@pytest.fixture(scope="module")
def policy_harness(tmp_path_factory):
    node = shutil.which("node")
    binary = shutil.which("pi")
    if node is None or binary is None:
        pytest.skip("pi and node are needed to execute the provider policy")
    package_root = Path(binary).resolve().parent.parent
    package = next(
        path for path in (
            package_root / "lib/node_modules/@earendil-works/pi-coding-agent",
            package_root / "libexec/lib/node_modules/@earendil-works/pi-coding-agent",
        ) if path.is_dir()
    )
    root = tmp_path_factory.mktemp("model-policy")
    extension = root / "extensions/cursor-model-policy/index.ts"
    extension.parent.mkdir(parents=True)
    extension.write_text((PI / "extensions/cursor-model-policy/index.ts").read_text())
    (root / "model-routing.json").write_text((PI / "model-routing.json").read_text())
    (root / "auth.json").write_text("{}")
    (root / "models.json").write_text("{}")
    return node, package, root, extension


def test_cursor_policy_with_real_registry_and_transport(policy_harness):
    node, package, root, extension = policy_harness
    script = f"""
import assert from 'node:assert/strict';
import {{ ModelRuntime, ModelRegistry }} from {json.dumps(str(package / 'dist/index.js'))};
import {{ createAssistantMessageEventStream }} from {json.dumps(str(package / 'node_modules/@earendil-works/pi-ai/dist/index.js'))};
import register from {json.dumps(str(extension))};
const root = {json.dumps(str(root))};
const runtime = await ModelRuntime.create({{
  authPath: root + '/auth.json',
  modelsPath: root + '/models.json',
  modelsStorePath: root + '/models-store.json',
  refreshOnCreate: false,
  allowModelNetwork: false,
}});
const registry = new ModelRegistry(runtime);
const calls = [];
const model = (id) => ({{
  id, name: id, provider: 'cursor', api: 'cursor-sdk',
  baseUrl: 'https://cursor.invalid', reasoning: false, input: ['text'],
  cost: {{ input: 0, output: 0, cacheRead: 0, cacheWrite: 0 }},
  contextWindow: 1000, maxTokens: 100,
}});
const ids = ['composer-2-5', 'grok-4.6', 'opus', 'claude-opus-5@1m',
  'gpt-5.6-sol@1m', 'auto', 'grok-4.5', 'future-model', 'composer-2-5:fast'];
const catalog = ids.map(model);
const registerCursor = () => registry.registerProvider('cursor', {{
  baseUrl: 'https://cursor.invalid', apiKey: 'test-placeholder', api: 'cursor-sdk',
  models: catalog,
  streamSimple: (m, context, options) => {{
    calls.push([m.id, context, options]);
    const stream = createAssistantMessageEventStream();
    stream.push({{ type: 'done', reason: 'stop', message: {{
      role: 'assistant', content: [{{ type: 'text', text: 'transport result' }}],
      api: m.api, provider: m.provider, model: m.id, stopReason: 'stop', timestamp: 0,
      usage: {{ input: 0, output: 0, cacheRead: 0, cacheWrite: 0, totalTokens: 0,
        cost: {{ input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 }} }},
    }} }});
    stream.end();
    return stream;
  }},
}});
registerCursor();
const ctx = {{ modelRegistry: registry }};
const handlers = {{}};
let registrations = 0;
const pi = {{
  on: (event, handler) => {{ handlers[event] = handler; }},
  registerProvider: (provider) => {{ registrations++; registry.registerProvider(provider); }},
}};
register(pi);
await handlers.session_start({{}}, ctx);
assert.deepEqual(registry.getAll().filter(m => m.provider === 'cursor').map(m => m.id).sort(),
  ['composer-2-5', 'grok-4.6']);
const restricted = registry.getProvider('cursor');
const context = {{ messages: [] }};
const options = {{ apiKey: 'test-placeholder' }};
for (const id of ids.slice(0, 2)) {{
  for (const method of ['stream', 'streamSimple']) {{
    const result = await restricted[method](model(id), context, options).result();
    assert.equal(result.content[0].text, 'transport result');
  }}
}}
assert.equal(calls.length, 4);
assert.equal(calls[0][1], context);
assert.equal(calls[0][2].apiKey, options.apiKey);
for (const id of ids.slice(2)) {{
  for (const method of ['stream', 'streamSimple']) {{
    assert.throws(() => restricted[method](model(id), context, options), /disabled by model-routing/);
  }}
}}
assert.equal(calls.length, 4);
assert.deepEqual(restricted.filterModels(catalog).map(m => m.id), ids.slice(0, 2));
await runtime.refresh({{ allowNetwork: false }});
assert.deepEqual((await runtime.getAvailable('cursor')).map(m => m.id).sort(), ids.slice(0, 2));
const auth = await runtime.getAuth('cursor');
assert.equal(auth.auth.apiKey, 'test-placeholder');
assert.equal(registrations, 1);
for (const event of ['session_start', 'before_agent_start', 'turn_start', 'model_select',
  'session_before_compact', 'session_before_tree']) {{
  await handlers[event]({{}}, ctx);
}}
assert.equal(registrations, 1);
for (const event of ['before_agent_start', 'turn_start', 'model_select',
  'session_before_compact', 'session_before_tree']) {{
  registerCursor();
  await handlers[event]({{}}, ctx);
  assert.equal(registry.find('cursor', 'opus'), undefined);
  assert.throws(() => registry.getProvider('cursor').streamSimple(model('opus'), context), /disabled/);
}}
assert.equal(calls.length, 4);
const childHandlers = {{}};
register({{
  on: (event, handler) => {{ childHandlers[event] = handler; }},
  registerProvider: (provider) => {{ registrations++; registry.registerProvider(provider); }},
}});
const registrationsBeforeSharedTurns = registrations;
for (let turn = 0; turn < 100; turn++) {{
  const sessionHandlers = turn % 2 === 0 ? handlers : childHandlers;
  await sessionHandlers.turn_start({{}}, ctx);
}}
assert.equal(registrations, registrationsBeforeSharedTurns);
registry.unregisterProvider('cursor');
await handlers.before_agent_start({{}}, ctx);
assert.equal(registry.getProvider('cursor'), undefined);
console.log('provider policy passed');
"""
    result = subprocess.run(
        [node, "--input-type=module", "-e", script],
        capture_output=True, text=True, check=False, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "provider policy passed" in result.stdout


def test_routing_targets_are_enabled_and_cursor_is_restricted():
    routing = json.loads((PI / "model-routing.json").read_text())
    settings = json.loads((PI / "settings.json").read_text())
    enabled = set(settings["enabledModels"])
    allowed_cursor = {f"cursor/{model}" for model in routing["cursorModels"]}

    assert {model for model in enabled if model.startswith("cursor/")} == allowed_cursor
    for target in routing["redirects"].values():
        assert target in enabled
        assert not target.startswith("cursor/")
    for primary, fallbacks in routing["fallbacks"].items():
        assert primary in enabled
        assert fallbacks
        for target in fallbacks:
            assert target in enabled
            assert target.startswith("openai-codex/")
    subagents = json.loads((PI / "subagents.json").read_text())
    assert subagents["scopeModels"] is True


def test_every_cursor_skill_pin_is_allowed_or_redirected():
    routing = json.loads((PI / "model-routing.json").read_text())
    allowed = {f"cursor/{model}" for model in routing["cursorModels"]}

    for root in (SKILLS, PLUGINS):
        for path in root.rglob("SKILL.md"):
            text = path.read_text()
            if not text.startswith("---\n"):
                continue
            frontmatter = yaml.safe_load(text.split("---", 2)[1])
            model = frontmatter.get("model", "inherit")
            if model.startswith("cursor/"):
                assert model in allowed or model in routing["redirects"], str(path)


def test_local_skill_pins_use_selected_providers():
    claude = PI.parent / "claude"
    registry = json.loads((claude / "skill-registry.json").read_text())
    local_skills = registry["local_skills"]
    expected = {
        "humanizer": "sonnet",
        "ac": "sonnet",
        "agent-writer": "opus",
        "coderabbit": "sonnet",
    }
    for entry in local_skills:
        name = entry["name"]
        path = claude / "skills" / name / "SKILL.md"
        frontmatter = yaml.safe_load(path.read_text().split("---", 2)[1])
        model = frontmatter.get("model", "inherit")
        if name in expected:
            assert model == expected[name]
        if model.startswith("cursor/"):
            assert model == "cursor/composer-2-5"
