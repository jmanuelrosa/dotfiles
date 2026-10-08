"""/cc-batch sends Claude Code's /batch orchestration prompt, rewritten for Pi."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from dotkit.testing import PI_EXTENSIONS

SOURCE = PI_EXTENSIONS / "cc-batch"
PI_PACKAGE = "@earendil-works/pi-coding-agent"
PLACEHOLDER = "{{instruction}}"
CWD = "/work/repository"


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
def extension(tmp_path_factory):
    package = pi_package()
    if package is None or shutil.which("node") is None:
        pytest.skip("pi and node are needed to execute the extension")

    root = tmp_path_factory.mktemp("cc-batch")
    scope = root / "node_modules" / "@earendil-works"
    scope.mkdir(parents=True)
    (scope / "pi-coding-agent").symlink_to(package)
    (root / "prompt.md").write_text((SOURCE / "prompt.md").read_text())
    copied = root / "cc-batch.ts"
    copied.write_text((SOURCE / "index.ts").read_text())
    return copied


def invoke(extension, args, idle=True, repository=True, probe_throws=False):
    stdout = "true\n" if repository else ""
    code = 0 if repository else 128
    outcome = (
        'throw new Error("probe unavailable")'
        if probe_throws
        else f'return {{ stdout: {json.dumps(stdout)}, stderr: "", code: {code}, killed: false }}'
    )
    script = f'''
      import register from {json.dumps(str(extension))};
      const commands = {{}};
      const sent = [];
      const notified = [];
      const probes = [];
      register({{
        registerCommand: (name, options) => commands[name] = options,
        sendUserMessage: (...args) => sent.push(args),
        exec: async (...call) => {{ probes.push(call); {outcome}; }},
      }});
      await commands["cc-batch"].handler(
        {json.dumps(args)},
        {{
          cwd: {json.dumps(CWD)},
          isIdle: () => {str(idle).lower()},
          ui: {{ notify: (message, type) => notified.push([message, type]) }},
        }},
      );
      process.stdout.write(JSON.stringify({{ names: Object.keys(commands), sent, notified, probes }}));
    '''
    result = subprocess.run(
        [shutil.which("node"), "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_prompt_carries_exactly_one_instruction_slot():
    assert (SOURCE / "prompt.md").read_text().count(PLACEHOLDER) == 1


def test_instruction_is_substituted_into_the_orchestration_prompt(extension):
    instruction = "rename foo to bar across the repo"
    result = invoke(extension, f"  {instruction}  ")

    assert result["names"] == ["cc-batch"]
    assert result["notified"] == []
    assert result["probes"] == [["git", ["rev-parse", "--is-inside-work-tree"], {"cwd": CWD}]]
    [[prompt, *options]] = result["sent"]
    assert options == []
    assert prompt.startswith("# Batch: Parallel Work Orchestration")
    assert f"## User Instruction\n\n{instruction}\n" in prompt
    assert PLACEHOLDER not in prompt


def test_replacement_patterns_in_the_instruction_stay_literal(extension):
    instruction = "replace $& and $1 with {{instruction}}"
    [[prompt]] = invoke(extension, instruction)["sent"]

    assert f"\n{instruction}\n" in prompt


def test_busy_session_queues_the_prompt_as_a_follow_up(extension):
    [[_, options]] = invoke(extension, "migrate from react to vue", idle=False)["sent"]

    assert options == {"deliverAs": "followUp"}


def test_empty_instruction_prints_usage_and_sends_nothing(extension):
    result = invoke(extension, "   ")

    assert result["sent"] == []
    [[message, kind]] = result["notified"]
    assert message.startswith("Provide an instruction describing the batch change")
    assert "/cc-batch " in message
    assert kind == "warning"


@pytest.mark.parametrize("probe", [{"repository": False}, {"probe_throws": True}])
def test_outside_a_repository_refuses_and_sends_nothing(extension, probe):
    result = invoke(extension, "migrate from react to vue", **probe)

    assert result["sent"] == []
    [[message, kind]] = result["notified"]
    assert "git repository" in message
    assert kind == "error"
