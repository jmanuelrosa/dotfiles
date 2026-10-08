"""Pi's /cc-fewer-permission-prompts forwards to the shared skill of the same name."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from dotkit.testing import PI_EXTENSIONS, SKILLS

NAME = "cc-fewer-permission-prompts"
EXTENSION = PI_EXTENSIONS / NAME / "index.ts"
PI_PACKAGE = "@earendil-works/pi-coding-agent"


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
    assert EXTENSION.is_file(), f"{EXTENSION} is missing"

    root = tmp_path_factory.mktemp(NAME)
    scope = root / "node_modules" / "@earendil-works"
    scope.mkdir(parents=True)
    (scope / "pi-coding-agent").symlink_to(package)
    copied = root / f"{NAME}.ts"
    copied.write_text(EXTENSION.read_text())
    return copied


def invoke(extension, args="", idle=True):
    script = f'''
      import register from {json.dumps(str(extension))};
      const commands = {{}};
      const sent = [];
      register({{
        registerCommand: (name, options) => commands[name] = options,
        sendUserMessage: (...args) => sent.push(args),
      }});
      await commands[{json.dumps(NAME)}].handler(
        {json.dumps(args)},
        {{ isIdle: () => {str(idle).lower()} }},
      );
      process.stdout.write(JSON.stringify({{ names: Object.keys(commands), sent }}));
    '''
    result = subprocess.run(
        [shutil.which("node"), "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_the_target_skill_exists():
    assert (SKILLS / NAME / "SKILL.md").is_file()


def test_command_expands_the_skill_and_forwards_arguments(extension):
    result = invoke(extension, " --min-count 5 ")

    assert result["names"] == [NAME]
    assert result["sent"] == [[f"/skill:{NAME} --min-count 5", {"expandPromptTemplates": True}]]


def test_command_queues_the_skill_when_the_agent_is_busy(extension):
    result = invoke(extension, idle=False)

    assert result["sent"] == [[
        f"/skill:{NAME}",
        {"expandPromptTemplates": True, "deliverAs": "followUp"},
    ]]
