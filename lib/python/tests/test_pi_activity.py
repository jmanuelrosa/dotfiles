"""Conversation-first Pi activity must use only supported extension APIs.

The feature deliberately does not patch Pi's transcript internals. These checks keep that
boundary visible while driving the activity labels that are otherwise easy to regress into raw
tool names or absolute paths.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from dotkit.testing import PI_EXTENSIONS

EXTENSION = PI_EXTENSIONS / "activity.ts"
PACKAGE = "@earendil-works/pi-coding-agent"
DRIVEN = ("describeActivity",)


@pytest.fixture(scope="module")
def source():
    return EXTENSION.read_text()


@pytest.fixture(scope="module")
def runner(tmp_path_factory):
    if shutil.which("node") is None:
        pytest.skip("node is needed to run the activity extension")
    binary = shutil.which("pi")
    if binary is None:
        pytest.skip("pi is needed to run the activity extension")
    home = tmp_path_factory.mktemp("pi-activity")
    package = Path(binary).resolve().parent.parent / "libexec/lib/node_modules" / PACKAGE
    if not package.is_dir():
        pytest.skip("pi is needed to run the activity extension")
    scope = home / "node_modules" / "@earendil-works"
    scope.mkdir(parents=True)
    (scope / "pi-coding-agent").symlink_to(package)
    (scope / "pi-tui").symlink_to(package / "node_modules" / "@earendil-works/pi-tui")
    (home / "activity.ts").write_text(f"{EXTENSION.read_text()}\nexport {{ {', '.join(DRIVEN)} }};\n")
    return home


def run(runner, body):
    script = runner / "run.mjs"
    script.write_text(f'import activity, {{ {", ".join(DRIVEN)} }} from "./activity.ts";\n{body}')
    result = subprocess.run(["node", str(script)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_uses_public_rendering_and_activity_apis(source):
    assert "createReadToolDefinition" in source
    assert "setWorkingMessage" in source
    assert "setWorkingVisible" in source
    assert "setToolsExpanded" not in source
    assert "context.expanded && definition.renderCall" in source
    assert "context.expanded && definition.renderResult" in source
    assert "dist/modes" not in source


def test_read_activity_uses_a_relative_path(runner):
    result = run(
        runner,
        'process.stdout.write(JSON.stringify(describeActivity("read", { path: "/repo/src/auth.ts" }, "/repo")));',
    )
    assert result == {"action": "Reading", "target": "src/auth.ts"}


def test_search_activity_quotes_its_pattern(runner):
    result = run(
        runner,
        'process.stdout.write(JSON.stringify(describeActivity("grep", { pattern: "token refresh" }, "/repo")));',
    )
    assert result == {"action": "Searching for", "target": '"token refresh"'}


def test_recovered_failures_are_hidden_after_final_assistant_prose(runner):
    result = run(
        runner,
        '''
import { initTheme } from "@earendil-works/pi-coding-agent";
initTheme("dark", false);
const handlers = new Map();
const tools = [];
const ui = {
  theme: { fg: (_color, text) => text },
  setStatus() {},
  setWorkingMessage() {},
  setWorkingVisible() {},
};
activity({
  on(event, handler) { handlers.set(event, handler); },
  registerTool(tool) { tools.push(tool); },
});
const ctx = { cwd: "/repo", mode: "tui", ui };
await handlers.get("session_start")({ reason: "startup" }, ctx);
handlers.get("tool_result")({ isError: true }, ctx);
let invalidated = false;
const renderContext = {
  args: { path: "src/auth.ts" },
  expanded: false,
  isError: true,
  invalidate() { invalidated = true; },
};
const read = tools.find((tool) => tool.name === "read");
const visible = read.renderResult({ content: [], details: {} }, { expanded: false }, ui.theme, renderContext);
handlers.get("message_end")({ message: { role: "assistant", content: [{ type: "text" }] } });
const hidden = read.renderResult({ content: [], details: {} }, { expanded: false }, ui.theme, renderContext);
process.stdout.write(JSON.stringify({ visible: visible.render(120), hidden: hidden.render(120), invalidated }));
''',
    )
    assert "Failed reading src/auth.ts" in "\n".join(result["visible"])
    assert result["hidden"] == []
    assert result["invalidated"] is True


def test_tool_rendering_uses_only_theme_colours(source):
    assert "theme.fg(" in source
    assert "#" not in source
    for colour in ("accent", "dim", "error", "muted", "toolDiffAdded"):
        assert f'"{colour}"' in source


def test_pi_exports_the_factories_the_extension_uses(source):
    binary = shutil.which("pi")
    if binary is None:
        pytest.skip("pi is needed to check the extension against its own API")
    root = Path(binary).resolve().parent.parent
    declarations = (root / "libexec/lib/node_modules" / PACKAGE / "dist/index.d.ts").read_text()
    for name in (
        "createReadToolDefinition",
        "createGrepToolDefinition",
        "createLsToolDefinition",
        "createFindToolDefinition",
        "createEditToolDefinition",
        "createWriteToolDefinition",
        "createBashToolDefinition",
        "createPowerShellToolDefinition",
    ):
        assert name in declarations
