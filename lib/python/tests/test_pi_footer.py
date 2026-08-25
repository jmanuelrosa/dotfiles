"""The footer extension owns pi's footer, so everything pi used to render there is now this
file's arithmetic, and all of it fails quietly.

Replacing the built-in footer is the trade footer.ts records at the top: one rendering of the
context percentage instead of two, paid for by re-deriving the token totals, the cache hit rate
and the cost from pi's session entries. Every field that derivation reads belongs to pi, none of
them is checked at load time because pi strips types rather than compiling them, and a renamed
one leaves a footer that renders happily with a zero in it. A cost stuck at `$0.000` looks exactly
like a session that has not spent anything yet.

So the static half reads both sides: whatever the extension imports, pi must export; whatever
field it reads, pi must still declare; whatever colour it paints with, pi's theme must define.
The same bargain [test_pi_velocity.py](test_pi_velocity.py) makes, and it skips rather than fails
when pi is absent for the same reason, since pi is installed by the role these tests cover.

The rest runs the real thing, because the questions that matter here are not name checks. Whether
a 60-column terminal keeps the context gauge, whether the handoff marker appears at the threshold
docs/internals/context-hygiene.md sets, and whether a turn's cost is separated from the session's
are all decisions a grep cannot see, and each of them is wrong in a way that still renders.
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from dotkit.testing import CLAUDE, PI_EXTENSIONS, REPO

EXTENSION = PI_EXTENSIONS / "footer.ts"
STATUSLINE = CLAUDE / "statusline.sh"
# The one file the glyphs, the gauge, the lockfile table and the handoff threshold come from,
# for this harness and for Claude's. Nothing below asserts a literal that lives in it.
VOCABULARY = REPO / "roles/ai/files/statusline.json"
TASKS = REPO / "roles/ai/tasks/main.yml"

PI_PACKAGE = "@earendil-works/pi-coding-agent"
TUI_PACKAGE = "@earendil-works/pi-tui"

# The private functions the executed half drives, re-exported into a copy of the extension so
# pi's own surface stays the single default export it loads.
DRIVEN = (
    "contextSegment",
    "repoSegment",
    "modelSegment",
    "spendSegment",
    "spend",
    "toolchainSegment",
    "detectPackageManager",
    "statusSegment",
    "fit",
    "formatTokens",
)


def pi_package():
    """The installed pi package, found through the `pi` on PATH rather than a pinned cellar path,
    so a version bump is followed rather than reported as missing."""
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


VOCAB = json.loads(VOCABULARY.read_text())


@pytest.fixture(scope="module")
def source():
    return EXTENSION.read_text()


@pytest.fixture(scope="module")
def package():
    found = pi_package()
    if found is None:
        pytest.skip("pi is needed to check the extension against its own API")
    return found


@pytest.fixture(scope="module")
def declarations(package):
    """Every `.d.ts` pi ships as one string, read once for the whole module.

    Its own dist and the packages it bundles, because the two halves of this footer's arithmetic
    are declared in different ones: `ContextUsage` is pi's, and the `Usage` the spend totals are
    summed from belongs to pi-ai. A glob over pi's dist alone finds the field names anyway, in
    unrelated interfaces, and passes while asserting nothing.
    """
    roots = [package / "dist", *(package / "node_modules/@earendil-works").glob("*/dist")]
    return "\n".join(path.read_text() for root in roots for path in root.rglob("*.d.ts"))


def imported(source, module):
    # `[^}]` rather than a lazy `.`, which crosses the closing brace of an earlier import and
    # returns the names of whichever block precedes this one.
    block = re.search(rf'import (?:type )?\{{([^}}]*)\}} from "{re.escape(module)}"', source, re.S)
    assert block, f"the extension must import from {module} by package name"
    return {
        name.replace("type ", "").strip() for name in block.group(1).split(",") if name.strip()
    }


# --- the contract with pi, read off both sides ---------------------------------


def test_every_imported_pi_name_is_exported(source, package):
    """A name pi does not export is an import error at load, which pi reports as an extension
    that failed rather than as a footer that is missing."""
    exports = (package / "dist/index.d.ts").read_text()
    for name in imported(source, PI_PACKAGE):
        assert name in exports, f"{name} is not exported by {PI_PACKAGE}"


def test_every_imported_tui_name_is_exported(source, package):
    exports = (package / "node_modules" / TUI_PACKAGE / "dist/index.d.ts").read_text()
    for name in imported(source, TUI_PACKAGE):
        assert name in exports, f"{name} is not exported by {TUI_PACKAGE}"


def test_the_tui_package_is_one_pi_hands_extensions(source, package):
    """`@earendil-works/pi-tui` is not resolvable from `~/.pi/agent/extensions` by node's own
    rules: it lives inside pi's package, and an extension directory has no node_modules at all.
    Pi injects it, and the width arithmetic here would be an unresolved import the day it stops."""
    loader = (package / "dist/core/extensions/loader.js").read_text()
    assert f'"{TUI_PACKAGE}"' in loader, "pi no longer aliases pi-tui for extensions"
    assert TUI_PACKAGE in source


def test_the_footer_is_replaced_rather_than_appended(source, declarations):
    """The decision the file exists to record. `setStatus` would have been upgrade-proof and
    would have printed a second context reading beside pi's own."""
    assert "ctx.ui.setFooter(" in source
    assert "setFooter(factory:" in declarations


def test_other_extensions_keep_their_footer_output(source, declarations):
    """Replacing the footer without rendering this map is how a custom footer silently deletes
    every other extension's status: velocity.ts, the rtk toggle, the cursor badge and anything
    the packages in settings.json set all arrive through it."""
    assert "getExtensionStatuses()" in source
    assert "getExtensionStatuses(): ReadonlyMap<string, string>" in declarations


def test_the_context_fields_are_still_declared(source, declarations):
    """The gauge is the segment the whole trade was made for, and each of these renders as a
    plausible number when it goes missing: no percent reads as `?`, no window reads as `0`."""
    assert "ctx.getContextUsage()" in source
    for field in ("tokens: number | null", "contextWindow: number", "percent: number | null"):
        assert field in declarations, f"pi no longer declares `{field}` on ContextUsage"


def test_the_usage_fields_are_still_declared(source, declarations):
    """Every name the spend arithmetic reads off a session entry. A renamed one is a footer that
    reports less money than the session spent, in the direction nobody checks."""
    for field in ("input", "output", "cacheRead", "cacheWrite"):
        assert f"{field}: number" in declarations
        assert f"usage.{field}" in source
    assert "usage.cost.total" in source
    assert re.search(r"cost: \{[^}]*total: number", declarations, re.S), (
        "pi no longer declares a `cost.total`, so every dollar figure in the footer reads NaN"
    )


def test_the_summarising_entry_types_are_still_declared(source, declarations):
    """A compaction and a branch summary are model calls the user paid for. Counting only the
    assistant messages drops their cost at the moment it is incurred, which is the one moment a
    footer is being read to find out why the session got expensive."""
    for entry in ("compaction", "branch_summary"):
        assert f'"{entry}"' in source
        assert f'type: "{entry}"' in declarations


def test_the_theme_colours_exist(source, declarations):
    """`theme.fg` takes a `ThemeColor`, and an unknown one is not an error at runtime: pi returns
    the text unpainted, so the gauge loses its warning colour rather than saying anything."""
    palette = re.search(r"export type ThemeColor = ([^;]+);", declarations)
    assert palette, "pi no longer declares a ThemeColor union"
    allowed = set(re.findall(r'"([^"]+)"', palette.group(1)))
    used = set(re.findall(r'theme\.fg\("([^"]+)"', source))
    assert used, "the extension must paint through theme.fg, so the footer follows the theme"
    assert used <= allowed, f"not pi theme colours: {sorted(used - allowed)}"


def test_no_optional_theme_colour_is_painted_with(source, declarations):
    """`thinkingMax` and `searchMatchText` are optional in pi's theme schema, so a user-authored
    theme in roles/ai/files/pi/themes may define neither. Painting the max thinking level with
    one would leave that level as the only unstyled word in the segment."""
    optional = re.search(r"type OptionalThemeColor = ([^;]+);", declarations)
    assert optional, "pi no longer declares which theme colours are optional"
    used = set(re.findall(r'"([^"]+)"', source))
    assert used.isdisjoint(set(re.findall(r'"([^"]+)"', optional.group(1))))


def test_the_threshold_is_read_rather_than_typed(source):
    """The marker is what turns an ambient gauge into a prompt, and three files answer to the
    number behind it: this footer, Claude's statusline.sh and Claude's context-nudge.sh. It used
    to be a literal in each, pinned by comparing two of them. Now they read it, and what this
    asserts is that none of them has quietly gone back to typing it in."""
    assert "handoffPct" in source
    assert not re.search(r"HANDOFF_PCT\s*=\s*\d", source), (
        "footer.ts hardcodes the handoff threshold again; it belongs to statusline.json"
    )
    assert json.loads(VOCABULARY.read_text())["handoffPct"] > 0


def test_the_shared_glyphs_are_not_typed_into_the_extension(source):
    """The same rule for the vocabulary the two harnesses share. A glyph typed here renders
    correctly today and stops matching Claude's the first time one of them is changed."""
    vocabulary = json.loads(VOCABULARY.read_text())
    for name, mark in vocabulary["glyphs"].items():
        if name in ("rtk", "cursor", "warning"):  # guardrails.ts renders those three
            continue
        assert mark not in source, f"{name} is hardcoded in footer.ts; it belongs to statusline.json"


def test_the_render_path_spawns_nothing(source):
    """`render` is called per frame. statusline.sh caches its `--version` spawns to a temp file
    because Claude re-executes it every turn; this extension is alive for the whole session, so
    the resolution happens once per directory and off the render path entirely."""
    body = source[source.index("private rows(") :]
    assert "pi.exec" not in body, "a child process on the render path costs a spawn per frame"


def test_the_role_installs_the_extension():
    """The glob covers any `.ts` dropped in the directory, so this file needs no task of its own.
    Asserted anyway, because that is exactly the kind of thing a later refactor narrows to a named
    list, and a dropped extension is silent at both ends."""
    assert "files/pi/extensions/*.ts" in TASKS.read_text()


# --- the extension, executed ---------------------------------------------------


@pytest.fixture(scope="module")
def runner(package, tmp_path_factory):
    """A directory the extension can be imported from, with pi, pi-tui and the vocabulary
    resolvable.

    The layout mirrors the repo rather than being flat: the extension reads
    `../../statusline.json` relative to its own realpath, so a copy dropped in a bare temp
    directory would find no vocabulary and every glyph assertion below would pass against an
    empty string. `<root>/pi/extensions/footer.ts` beside `<root>/statusline.json` is the same
    two levels the checkout has, and the vocabulary is linked rather than copied so a test can
    never assert against a stale duplicate of the file it is supposed to be pinning.

    The extension itself is written rather than linked because node resolves a bare import from
    the realpath of the importing module, so a link would send it looking for node_modules in
    this checkout. pi-tui is linked out of pi's own node_modules, which is where pi's loader
    takes it from.
    """
    if shutil.which("node") is None:
        pytest.skip("node is needed to execute the extension")
    root = tmp_path_factory.mktemp("footer")
    scope = root / "node_modules" / "@earendil-works"
    scope.mkdir(parents=True)
    (scope / "pi-coding-agent").symlink_to(package)
    (scope / "pi-tui").symlink_to(package / "node_modules" / TUI_PACKAGE)
    (root / "statusline.json").symlink_to(VOCABULARY)
    extensions = root / "pi" / "extensions"
    extensions.mkdir(parents=True)
    (extensions / "footer.ts").write_text(
        f"{EXTENSION.read_text()}\nexport {{ {', '.join(DRIVEN)} }};\n"
    )
    return extensions


def run_in_node(runner, body, cwd=None):
    """`body` as an ES module beside the extension, with its stdout parsed as JSON."""
    script = f'import {{ {", ".join(DRIVEN)} }} from "{runner}/footer.ts";\n{body}'
    done = subprocess.run(
        [shutil.which("node"), "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        cwd=cwd or runner,
        env={**os.environ},
        check=False,
    )
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def test_the_extension_survives_type_stripping(runner):
    """Pi strips types rather than compiling them, so TypeScript that has to be *emitted* rather
    than erased is a load error and not a type error. Constructor parameter properties are the
    trap this caught: `constructor(private readonly ctx: X)` is ordinary TypeScript, is what an
    editor suggests, and takes the whole extension down at startup with the rest of the footer.
    """
    body = 'const mod = await import("./footer.ts"); process.stdout.write(JSON.stringify(typeof mod.default));'
    assert run_in_node(runner, body) == "function"


# A theme whose colours cost no columns, for the assertions that are about width. The stub every
# other test uses names the colour it was asked for, which is the right shape for a colour
# assertion and would make every string three times too wide for a fit() one.
PLAIN_THEME = "const theme = { fg: (_c, text) => text, bold: (text) => text };"
NAMED_THEME = "const theme = { fg: (c, text) => `<${c}>${text}`, bold: (text) => `*${text}*` };"


def context_for(runner, usage, width=120, theme=PLAIN_THEME):
    body = f"""
    {theme}
    const ctx = {{ getContextUsage: () => ({json.dumps(usage)}) }};
    process.stdout.write(JSON.stringify(contextSegment(ctx, theme, {width})));
    """
    return run_in_node(runner, body)


def test_the_gauge_marks_the_handoff_threshold(runner):
    """The threshold docs/internals/context-hygiene.md sets, wherever statusline.json currently
    puts it. The marker is the whole reason the gauge is worth footer width: a percentage is a
    fact, a percentage with a threshold applied to it is a prompt."""
    threshold = VOCAB["handoffPct"]
    marker = VOCAB["labels"]["handoff"]
    below = context_for(runner, {"tokens": 1, "contextWindow": 200_000, "percent": threshold - 1})
    at = context_for(runner, {"tokens": 1, "contextWindow": 200_000, "percent": threshold})
    assert marker not in below
    assert marker in at


def test_the_gauge_reddens_before_the_window_runs_out(runner):
    """Pi's own footer reddens at 90, which is a colour with nothing left to warn about: by then
    the handoff it should have prompted was due twenty points earlier."""
    warning = context_for(
        runner,
        {"tokens": 100_000, "contextWindow": 200_000, "percent": VOCAB["handoffPct"] + 15},
        theme=NAMED_THEME,
    )
    critical = context_for(
        runner, {"tokens": 150_000, "contextWindow": 200_000, "percent": 75}, theme=NAMED_THEME
    )
    assert f"<warning>({VOCAB['handoffPct'] + 15}%)" in warning
    assert "<error>(75%)" in critical


def test_an_unknown_context_is_shown_as_unknown(runner):
    """The turn after a compaction, where pi has no token count until the next response. A gauge
    that guessed would be reporting a window it cannot see."""
    unknown = context_for(runner, {"tokens": None, "contextWindow": 200_000, "percent": None})
    assert unknown == f"{VOCAB['labels']['context']} ?/200k"


def test_the_bar_is_dropped_before_the_reading_is(runner):
    """A narrow terminal keeps the number and loses the picture, because eight columns of bar
    say nothing the percentage beside it does not."""
    usage = {"tokens": 39_000, "contextWindow": 200_000, "percent": 19}
    assert VOCAB["bar"]["empty"] in context_for(runner, usage, width=120)
    assert VOCAB["bar"]["empty"] not in context_for(runner, usage, width=60)
    assert "(19%)" in context_for(runner, usage, width=60)


def spend_for(runner, entries):
    body = f"""
    const entries = {json.dumps(entries)};
    process.stdout.write(JSON.stringify(spend(entries)));
    """
    return run_in_node(runner, body)


def usage(cost, **tokens):
    filled = {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, **tokens}
    return {**filled, "cost": {**{k: 0 for k in filled}, "total": cost}}


def test_the_session_total_counts_every_entry_that_carries_usage(runner):
    """Not just the assistant messages: a tool result can carry its own usage, and a compaction
    or a branch summary is a model call whose cost would otherwise vanish from the total at the
    moment it happened."""
    totals = spend_for(
        runner,
        [
            {"type": "message", "message": {"role": "user"}},
            {"type": "message", "message": {"role": "assistant", "usage": usage(0.20, input=1000)}},
            {"type": "message", "message": {"role": "toolResult", "usage": usage(0.01)}},
            {"type": "compaction", "usage": usage(0.05, input=500)},
            {"type": "branch_summary", "usage": usage(0.04)},
        ],
    )
    assert round(totals["cost"], 3) == 0.30
    assert totals["input"] == 1500


def test_the_turn_is_the_spend_since_the_last_user_message(runner):
    """The split pi's single dollar figure hides: a session at `$4.10` says nothing about whether
    the question being answered right now is the cheap one or the expensive one."""
    totals = spend_for(
        runner,
        [
            {"type": "message", "message": {"role": "user"}},
            {"type": "message", "message": {"role": "assistant", "usage": usage(0.25)}},
            {"type": "message", "message": {"role": "user"}},
            {"type": "message", "message": {"role": "assistant", "usage": usage(0.03)}},
        ],
    )
    assert round(totals["cost"], 3) == 0.28
    assert round(totals["turn"], 3) == 0.03


def test_the_cache_hit_rate_is_the_latest_prompt(runner):
    """A running average would flatten exactly the thing the number is read for, which is whether
    the prompt sent a moment ago hit the cache."""
    totals = spend_for(
        runner,
        [
            {
                "type": "message",
                "message": {"role": "assistant", "usage": usage(0.1, input=1000, cacheRead=0)},
            },
            {
                "type": "message",
                "message": {"role": "assistant", "usage": usage(0.1, input=100, cacheRead=900)},
            },
        ],
    )
    assert round(totals["cacheHit"]) == 90


def fit_for(runner, segments, width):
    body = f"""
    {PLAIN_THEME}
    const segments = {json.dumps(segments)};
    process.stdout.write(JSON.stringify(fit(segments, {width}, theme)));
    """
    return run_in_node(runner, body)


def test_a_row_is_filled_in_priority_order(runner):
    """A segment that does not fit is skipped and the next one is still offered the space. The
    bug this replaced: assembling the row and trimming the cheapest segments dropped a wide one
    and left the columns it had occupied empty, so an 80-column row lost its whole toolchain to a
    cost figure that did not fit either."""
    row = fit_for(
        runner,
        [
            {"text": "toolchain", "keep": 10},
            {"text": "a-very-wide-spend-segment", "keep": 30},
            {"text": "context", "keep": 100},
        ],
        width=24,
    )
    assert row == "toolchain │ context"


def test_the_row_keeps_its_order_whatever_the_priorities(runner):
    """Priority decides what survives, never where it sits: a footer whose segments moved
    between repaints would have to be read rather than glanced at."""
    row = fit_for(
        runner,
        [{"text": "left", "keep": 10}, {"text": "right", "keep": 100}],
        width=80,
    )
    assert row == "left │ right"


def test_a_terminal_too_narrow_for_anything_still_shows_something(runner):
    """A row emptied by a narrow terminal is indistinguishable from a footer that failed to
    render, so the first segment admitted is admitted unconditionally and truncated."""
    row = fit_for(runner, [{"text": "context [▓▓░░░░░░] 39k (19%)", "keep": 100}], width=10)
    plain = re.sub(r"\x1b\[[0-9;]*m", "", row)
    assert plain.startswith("context")
    assert len(plain) <= 10


def test_the_statuses_are_ordered_and_flattened(runner):
    """Pi's own two rules for the status line, kept because they are the reason it can be read at
    a glance: sorted by key so a repaint never reorders the badges, and stripped of control
    characters so one extension's newline cannot push the footer off its own row."""
    body = """
    const statuses = new Map([["z-second", "second"], ["a-first", "first\\nwrapped"]]);
    const data = { getExtensionStatuses: () => statuses };
    process.stdout.write(JSON.stringify(statusSegment(data)));
    """
    assert run_in_node(runner, body) == "first wrapped  second"


def test_the_package_manager_is_found_above_the_working_directory(runner, tmp_path):
    """A monorepo keeps its lockfile at the root and its package.json files in the packages, so a
    check that stopped at cwd would report nothing from the repos where it matters most."""
    (tmp_path / "pnpm-lock.yaml").write_text("")
    nested = tmp_path / "packages" / "web"
    nested.mkdir(parents=True)
    body = f'process.stdout.write(JSON.stringify(detectPackageManager({json.dumps(str(nested))})));'
    assert run_in_node(runner, body)["name"] == "pnpm"


def test_a_declared_package_manager_beats_the_lockfile(runner, tmp_path):
    """`packageManager` carries the version too, so preferring it saves the child process a
    lockfile hit would have cost. The corepack integrity hash is not part of the version."""
    (tmp_path / "yarn.lock").write_text("")
    (tmp_path / "package.json").write_text(json.dumps({"packageManager": "bun@1.1.0+sha224.abc"}))
    body = f'process.stdout.write(JSON.stringify(detectPackageManager({json.dumps(str(tmp_path))})));'
    assert run_in_node(runner, body) == {"name": "bun", "version": "1.1.0"}


def test_an_unknown_package_manager_is_not_reported(runner, tmp_path):
    """The field is free text, and a footer that printed whatever it found there would be
    rendering a stranger's string into pi's chrome."""
    (tmp_path / "package.json").write_text(json.dumps({"packageManager": "cargo@1.0.0"}))
    body = f'process.stdout.write(JSON.stringify(detectPackageManager({json.dumps(str(tmp_path))}) ?? null));'
    assert run_in_node(runner, body) is None


def test_the_thinking_level_is_painted_with_its_own_theme_colour(runner):
    """The same colour pi gives that level everywhere else, so the footer agrees with the
    thinking blocks above it instead of introducing a second vocabulary for one setting."""
    body = f"""
    {NAMED_THEME}
    const ctx = {{
      model: {{ id: "claude-opus-5", provider: "cursor", reasoning: true }},
      thinkingLevel: "high",
    }};
    process.stdout.write(JSON.stringify(modelSegment(ctx, theme)));
    """
    assert "<thinkingHigh>high" in run_in_node(runner, body)


def test_a_model_without_reasoning_shows_no_thinking_level(runner):
    """`off` on a model that has no thinking to turn off is a setting the reader cannot act on."""
    body = f"""
    {PLAIN_THEME}
    const ctx = {{ model: {{ id: "grok-4.6", provider: "xai" }}, thinkingLevel: "high" }};
    process.stdout.write(JSON.stringify(modelSegment(ctx, theme)));
    """
    assert run_in_node(runner, body) == f"{VOCAB['glyphs']['model']} grok-4.6 (xai)"


def test_the_provider_is_always_named(runner):
    """Where pi names it only when more than one is configured. This footer is read on a machine
    whose default provider routes tool calls through Cursor's own host tools, and which provider
    is answering decides whether the guardrail gates run at all."""
    body = f"""
    {PLAIN_THEME}
    const ctx = {{ model: {{ id: "composer-2-5", provider: "cursor" }} }};
    process.stdout.write(JSON.stringify(modelSegment(ctx, theme)));
    """
    assert "(cursor)" in run_in_node(runner, body)
