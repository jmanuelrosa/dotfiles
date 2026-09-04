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
DRIVEN = ("claudeMessage", "decorateEditorLines", "describeActivity")
TEST_EXPORTS = ("claudeMessage", "decorateEditorLines")


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
    (home / "activity.ts").write_text(f"{EXTENSION.read_text()}\nexport {{ {', '.join(TEST_EXPORTS)} }};\n")
    return home


def run(runner, body):
    script = runner / "run.mjs"
    script.write_text(f'import activity, {{ {", ".join(DRIVEN)} }} from "./activity.ts";\n{body}')
    result = subprocess.run(["node", str(script)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_uses_public_rendering_and_activity_apis(source):
    assert "createReadToolDefinition" in source
    assert "registerMarkdownTransformer" in source
    assert "setEditorComponent" in source
    assert "setWorkingIndicator" in source
    assert "setWorkingMessage" in source
    assert "setWorkingVisible" in source
    assert "setHiddenThinkingLabel" in source
    assert "registerEntryRenderer" not in source
    assert "appendEntry" not in source
    assert "setToolsExpanded" not in source
    assert "dist/modes" not in source


def test_user_messages_use_the_claude_prompt_caret(runner):
    result = run(
        runner,
        '''
process.stdout.write(JSON.stringify({
  user: claudeMessage("Fix the failing test", { messageType: "user" }),
  assistant: claudeMessage("I found the issue", { messageType: "assistant" }),
  thinking: claudeMessage("Checking the tests", { messageType: "assistant-thinking" }),
}));
''',
    )
    assert result == {
        "user": "❯ Fix the failing test",
        "assistant": "⏺ I found the issue",
        "thinking": "Checking the tests",
    }


def test_editor_prompt_reuses_padding_for_the_claude_caret(runner):
    result = run(
        runner,
        '''
process.stdout.write(JSON.stringify(decorateEditorLines(
  ["────────", "  hello ", "────────"],
  "❯ ",
)));
''',
    )
    assert result == ["────────", "❯ hello ", "────────"]


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


def test_tool_hierarchy_uses_semantic_labels_and_balanced_previews(runner):
    result = run(
        runner,
        '''
import { initTheme } from "@earendil-works/pi-coding-agent";
initTheme("dark", false);
const handlers = new Map();
const tools = [];
let editorFactory;
let workingIndicator;
const identity = (text) => text;
const theme = {
  fg: (_color, text) => text,
  bg: (_color, text) => text,
  bold: identity,
  italic: identity,
  underline: identity,
  inverse: identity,
  strikethrough: identity,
  getFgAnsi: () => "",
  getBgAnsi: () => "",
  getColorMode: () => "truecolor",
  getThinkingBorderColor: () => identity,
  getBashModeBorderColor: () => identity,
};
const ui = {
  theme,
  setEditorComponent(value) { editorFactory = value; },
  setStatus() {},
  setWorkingIndicator(value) { workingIndicator = value; },
  setWorkingMessage() {},
  setWorkingVisible() {},
  setHiddenThinkingLabel() {},
};
activity({
  on(event, handler) { handlers.set(event, handler); },
  registerMarkdownTransformer() {},
  registerTool(tool) { tools.push(tool); },
});
const ctx = { cwd: "/repo", mode: "tui", ui };
await handlers.get("session_start")({ reason: "startup" }, ctx);
const render = (toolName, args, content, { expanded = false, isError = false, details = {} } = {}) => {
  const tool = tools.find((candidate) => candidate.name === toolName);
  const state = {};
  const context = {
    args,
    toolCallId: `${toolName}-1`,
    invalidate() {},
    lastComponent: undefined,
    state,
    cwd: "/repo",
    executionStarted: true,
    argsComplete: true,
    isPartial: false,
    expanded,
    showImages: false,
    isError,
  };
  const call = tool.renderCall(args, theme, context);
  const result = tool.renderResult(
    { content: [{ type: "text", text: content }], details },
    { expanded, isPartial: false },
    theme,
    context,
  );
  return {
    call: call.render(120).map((line) => line.replace(/\x1b\\[[0-9;]*m/g, "").trimEnd()),
    result: result.render(120).map((line) => line.replace(/\x1b\\[[0-9;]*m/g, "").trimEnd()),
  };
};
const twelveLines = Array.from({ length: 12 }, (_, index) => `line ${index + 1}`).join("\\n");
const shellLines = Array.from({ length: 22 }, (_, index) => `output ${index + 1}`).join("\\n");
process.stdout.write(JSON.stringify({
  read: render("read", { path: "src/auth.ts" }, twelveLines),
  readExpanded: render("read", { path: "src/auth.ts" }, twelveLines, { expanded: true }),
  write: render("write", { path: "src/auth.ts", content: twelveLines }, "Successfully wrote 86 bytes to src/auth.ts"),
  bash: render("bash", { command: "make test" }, shellLines),
  error: render("read", { path: "private.txt" }, "Permission denied\\nprivate.txt", { isError: true }),
  hasEditor: typeof editorFactory === "function",
  workingFrames: workingIndicator.frames,
}));
''',
    )
    assert result["read"]["call"] == ["⏺ Read(src/auth.ts)"]
    assert result["read"]["result"] == [
        "  ⎿  Read 12 lines",
        "     line 1",
        "     line 2",
        "     line 3",
        "     line 4",
        "     line 5",
        "     line 6",
        "     line 7",
        "     line 8",
        "     line 9",
        "     line 10",
        "     +2 lines ( to expand)",
    ]
    assert result["readExpanded"]["result"] == [
        "  ⎿  Read 12 lines",
        *[f"     line {index}" for index in range(1, 13)],
    ]

    assert result["write"]["call"] == ["⏺ Write(src/auth.ts)"]
    assert result["write"]["result"] == [
        "  ⎿  Wrote 12 lines to src/auth.ts",
        *[f"     line {index}" for index in range(1, 11)],
        "     +2 lines ( to expand)",
    ]

    assert result["bash"]["call"] == ["⏺ Bash(make test)"]
    assert result["bash"]["result"] == [
        "  ⎿  Completed",
        *[f"     output {index}" for index in range(3, 23)],
        "     +2 lines ( to expand)",
    ]

    assert result["error"]["result"] == [
        "  ⎿  Failed reading private.txt",
        "     Permission denied",
        "     private.txt",
    ]

    assert result["hasEditor"] is True
    assert result["workingFrames"] == ["✻", "✽", "✶", "✳", "✢", "✳", "✶", "✽"]


def test_thinking_uses_pis_native_inline_label(runner):
    result = run(
        runner,
        '''
const handlers = new Map();
let registeredEntryRenderer = false;
let appendedEntry = false;
let hiddenThinkingLabel;
const ui = {
  theme: { fg: (_color, text) => text },
  setEditorComponent() {},
  setWorkingIndicator() {},
  setWorkingMessage() {},
  setWorkingVisible() {},
  setHiddenThinkingLabel(value) { hiddenThinkingLabel = value; },
};
activity({
  on(event, handler) { handlers.set(event, handler); },
  registerMarkdownTransformer() {},
  registerTool() {},
  registerEntryRenderer() { registeredEntryRenderer = true; },
  appendEntry() { appendedEntry = true; },
});
const ctx = { cwd: "/repo", mode: "tui", ui };
await handlers.get("session_start")({ reason: "startup" }, ctx);
process.stdout.write(JSON.stringify({
  registeredEntryRenderer,
  appendedEntry,
  hiddenThinkingLabel,
}));
''',
    )
    assert result == {
        "registeredEntryRenderer": False,
        "appendedEntry": False,
        "hiddenThinkingLabel": "✻ Thinking…",
    }


def test_activity_does_not_hide_tool_results_after_the_turn(source):
    assert 'pi.on("message_end"' not in source
    assert "showErrors" not in source


def test_tool_rendering_uses_only_theme_colours(source):
    assert "theme.fg(" in source
    assert "#" not in source
    for colour in ("accent", "dim", "error", "muted"):
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
