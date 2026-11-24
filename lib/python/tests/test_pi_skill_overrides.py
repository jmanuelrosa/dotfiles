"""cc-skill-overrides gives pi's model the same view of each skill as Claude's skillOverrides."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from dotkit.testing import PI_EXTENSIONS
from harnessgen import emit_claude, emit_pi, manifest

EXTENSION = PI_EXTENSIONS / "cc-skill-overrides" / "index.ts"
PI_PACKAGE = "@earendil-works/pi-coding-agent"
OVERRIDES = {"quiet": "name-only", "typed": "user-invocable-only", "gone": "off", "plain": "on"}


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
    """The extension in a copy of the adapter layout, so it finds a table this test controls."""
    package = pi_package()
    if package is None or shutil.which("node") is None:
        pytest.skip("pi and node are needed to execute the extension")
    root = tmp_path_factory.mktemp("cc-skill-overrides")
    scope = root / "node_modules" / "@earendil-works"
    scope.mkdir(parents=True)
    (scope / "pi-coding-agent").symlink_to(package)
    table = root / emit_pi.SKILL_OVERRIDES
    table.parent.mkdir(parents=True)
    table.write_text(json.dumps(OVERRIDES))
    copied = root / "adapters/pi/extensions/cc-skill-overrides/index.ts"
    copied.parent.mkdir(parents=True)
    copied.write_text(EXTENSION.read_text())
    return copied


def run(extension, body):
    script = f"""
      import register from {json.dumps(str(extension))};
      const handlers = {{}};
      const notices = [];
      register({{ on: (event, handler) => handlers[event] = handler }});
      const ctx = {{ ui: {{ notify: (message, level) => notices.push([message, level]) }} }};
      {body}
    """
    result = subprocess.run(
        [shutil.which("node"), "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def listed(extension):
    skills = [
        {"name": name, "description": f"{name} does things", "disableModelInvocation": False}
        for name in [*OVERRIDES, "unlisted"]
    ]
    return run(extension, f"""
      const skills = {json.dumps(skills)};
      await handlers.before_agent_start({{ systemPromptOptions: {{ skills }} }}, ctx);
      process.stdout.write(JSON.stringify(Object.fromEntries(skills.map((s) => [s.name, s]))));
    """)


def test_name_only_keeps_the_entry_and_drops_the_description(extension):
    skill = listed(extension)["quiet"]
    assert skill["description"] == ""
    assert skill["disableModelInvocation"] is False


@pytest.mark.parametrize("name", ["typed", "gone"])
def test_hidden_states_leave_the_model_listing(extension, name):
    assert listed(extension)[name]["disableModelInvocation"] is True


@pytest.mark.parametrize("name", ["plain", "unlisted"])
def test_other_skills_are_untouched(extension, name):
    assert listed(extension)[name] == {
        "name": name, "description": f"{name} does things", "disableModelInvocation": False,
    }


def submit(extension, text):
    return run(extension, f"""
      const result = await handlers.input({{ text: {json.dumps(text)}, source: "interactive" }}, ctx);
      process.stdout.write(JSON.stringify({{ result: result ?? null, notices }}));
    """)


def test_a_typed_off_skill_is_refused(extension):
    outcome = submit(extension, "/skill:gone now")
    assert outcome["result"] == {"action": "handled"}
    assert "gone" in outcome["notices"][0][0]


@pytest.mark.parametrize("text", ["/skill:typed go", "/skill:quiet", "tell me about /skill:gone"])
def test_any_other_prompt_passes(extension, text):
    assert submit(extension, text) == {"result": None, "notices": []}


def test_the_rendered_table_is_claudes_minus_its_bundled_skills():
    policy = manifest.load()
    rendered = json.loads((policy.root / emit_pi.SKILL_OVERRIDES).read_text())
    assert rendered == emit_claude.skill_overrides(policy.skill_registry(), {})
