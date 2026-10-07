"""The sandbox wrapper preserves upstream behavior outside its two CLI exemptions."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from dotkit.testing import PI, ai_defaults


EXTENSION = PI / "extensions/sandbox/index.ts"


@pytest.fixture(scope="module")
def sdk():
    node, binary = shutil.which("node"), shutil.which("pi")
    if node is None or binary is None:
        pytest.skip("pi and node are needed to execute the sandbox adapter")
    root = Path(binary).resolve().parent.parent
    package = next(path for path in (
        root / "lib/node_modules/@earendil-works/pi-coding-agent",
        root / "libexec/lib/node_modules/@earendil-works/pi-coding-agent",
    ) if path.is_dir())
    return node, package


def run_adapter(sdk, script, agent_dir=None, path=None):
    node, package = sdk
    loader = package / "dist/core/extensions/loader.js"
    env = {**os.environ, "RTK_ENABLE": ""}
    if agent_dir is not None:
        env["PI_CODING_AGENT_DIR"] = str(agent_dir)
    if path is not None:
        env["PATH"] = str(path) + os.pathsep + env["PATH"]
    result = subprocess.run(
        [node, "--input-type=module", "-e", f"""
import assert from "node:assert/strict";
import {{ loadExtensions }} from {json.dumps(str(loader))};
const loaded = await loadExtensions([{json.dumps(str(EXTENSION))}], process.cwd());
assert.deepEqual(loaded.errors, []);
const extension = loaded.extensions[0];
{script}
"""],
        env=env, text=True, capture_output=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_the_role_installs_the_adapter():
    assert "sandbox" in ai_defaults()["PI_EXTENSIONS"]
    assert (EXTENSION.parent / "README.md").is_file()


def test_the_installed_upstream_package_loads_through_the_wrapper(sdk):
    agent = Path(os.environ.get("PI_CODING_AGENT_DIR", Path.home() / ".pi/agent"))
    if not (agent / "npm/node_modules/pi-sandbox/index.ts").is_file():
        pytest.skip("pi-sandbox is needed to verify upstream integration")
    run_adapter(sdk, """
assert.equal(extension.tools.get("bash").definition.label, "bash (sandboxed)");
for (const name of ["sandbox", "sandbox-enable", "sandbox-disable", "sandbox-allow"]) {
  assert.ok(extension.commands.has(name));
}
for (const event of ["tool_call", "user_bash", "session_start", "session_shutdown"]) {
  assert.equal(extension.handlers.get(event).length, 1);
}
assert.ok(extension.flags.has("no-sandbox"));
""", agent)


def test_only_direct_exempted_calls_use_local_bash(sdk, tmp_path):
    agent = tmp_path / "agent"
    upstream = agent / "npm/node_modules/pi-sandbox/index.ts"
    upstream.parent.mkdir(parents=True)
    upstream.write_text("""
export default function (pi) {
  pi.registerTool({
    name: "bash", label: "sandboxed", description: "sandboxed",
    parameters: { type: "object", properties: { command: { type: "string" } } },
    execute: async () => ({ content: [{ type: "text", text: "sandboxed" }], details: {} }),
  });
  pi.on("tool_call", () => ({ block: true, reason: "upstream sandbox" }));
  pi.on("user_bash", () => ({ result: { output: "sandboxed", exitCode: 1 } }));
  pi.on("session_start", () => "upstream lifecycle");
}
""")
    binary_dir = tmp_path / "bin"
    binary_dir.mkdir()
    commands = json.loads((PI / "sandbox.json").read_text())["excludedCommands"]
    shell = shutil.which("bash")
    for command in commands:
        binary = binary_dir / command
        binary.write_text(f"#!{shell}\nprintf native-{command}")
        binary.chmod(0o755)
    run_adapter(sdk, """
const bash = extension.tools.get("bash").definition;
const toolCall = extension.handlers.get("tool_call")[0];
const userBash = extension.handlers.get("user_bash")[0];
const ctx = { cwd: process.cwd(), hasUI: false,
              sessionManager: { getSessionId: () => "sandbox-test", getSessionFile: () => undefined } };
const call = (command) => ({ type: "tool_call", toolName: "bash", input: { command } });
for (const command of ["gcloud projects list", "  gcloud compute instances list",
                       "bq show --format=json dataset.table", "bq ls"]) {
  assert.equal(await toolCall(call(command), ctx), undefined);
  assert.equal(await userBash({ command }, ctx), undefined);
  const result = await bash.execute("test", { command }, undefined, undefined, ctx);
  assert.match(result.content[0].text, /native-(gcloud|bq)/);
}
for (const command of ["echo hello", "aws s3 ls", "gsutil ls", "gcloudish projects list",
                       "/usr/bin/gcloud projects list", "env gcloud projects list",
                       "gcloud projects list | head", "gcloud projects list && echo hello",
                       "gcloud projects list; echo hello", "gcloud projects list &",
                       "gcloud projects list > output", "gcloud projects list < input",
                       "gcloud projects list\\necho hello", "gcloud projects list $(echo x)",
                       "gcloud projects list `echo x`", "gcloud projects list --project=$PROJECT",
                       "gcloud projects list \\\\; echo hello", "bq ls || echo hello",
                       "gcloud\\u00a0projects list", "gcloud projects list (echo hello)"]) {
  assert.equal((await toolCall(call(command), ctx)).block, true, command);
  assert.equal((await userBash({ command }, ctx)).result.output, "sandboxed", command);
  const result = await bash.execute("test", { command }, undefined, undefined, ctx);
  assert.equal(result.content[0].text, "sandboxed", command);
}
for (const toolName of ["read", "write", "edit"]) {
  assert.equal((await toolCall({ toolName, input: { path: "gcloud" } }, ctx)).block, true);
}
assert.equal(await extension.handlers.get("session_start")[0]({}, ctx), "upstream lifecycle");
""", agent, binary_dir)


def test_the_cloud_readonly_gate_still_blocks_exempted_commands(sdk):
    run_adapter(sdk, f"""
const guardrails = await loadExtensions([{json.dumps(str(PI / "extensions/guardrails/index.ts"))}], process.cwd());
assert.deepEqual(guardrails.errors, []);
const guard = guardrails.extensions[0].handlers.get("tool_call")[0];
const ctx = {{ cwd: process.cwd(), sessionManager: {{ getBranch: () => [] }} }};
for (const command of ["gcloud auth print-access-token", "gcloud projects delete example",
                       "bq rm dataset.table"]) {{
  const result = await guard({{ type: "tool_call", toolName: "bash", input: {{ command }} }}, ctx);
  assert.equal(result.block, true, command);
  assert.match(result.reason, /cloud-readonly-gate/);
}}
""")
