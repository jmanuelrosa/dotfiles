"""Pi's short git workflow commands expand to the corresponding explicit skills."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from dotkit.testing import PI_EXTENSIONS

EXTENSION = PI_EXTENSIONS / "skill-aliases.ts"
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

    root = tmp_path_factory.mktemp("skill-aliases")
    scope = root / "node_modules" / "@earendil-works"
    scope.mkdir(parents=True)
    (scope / "pi-coding-agent").symlink_to(package)
    copied = root / "skill-aliases.ts"
    copied.write_text(EXTENSION.read_text())
    return copied


def invoke(extension, name, args="", idle=True):
    script = f'''
      import register from {json.dumps(str(extension))};
      const commands = {{}};
      const sent = [];
      register({{
        registerCommand: (name, options) => commands[name] = options,
        sendUserMessage: (...args) => sent.push(args),
      }});
      await commands[{json.dumps(name)}].handler(
        {json.dumps(args)},
        {{ isIdle: () => {str(idle).lower()} }},
      );
      process.stdout.write(JSON.stringify({{ names: Object.keys(commands).sort(), sent }}));
    '''
    result = subprocess.run(
        [shutil.which("node"), "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_commit_alias_expands_the_skill_and_forwards_arguments(extension):
    result = invoke(extension, "commit", "dashboard")

    assert result["names"] == ["commit", "pr"]
    assert result["sent"] == [["/skill:commit dashboard", {"expandPromptTemplates": True}]]


def test_pr_alias_queues_the_expanded_skill_when_the_agent_is_busy(extension):
    result = invoke(extension, "pr", "develop", idle=False)

    assert result["sent"] == [[
        "/skill:pr develop",
        {"expandPromptTemplates": True, "deliverAs": "followUp"},
    ]]
