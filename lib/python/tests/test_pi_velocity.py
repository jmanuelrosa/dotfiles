"""The velocity extension's couplings are all with pi's own API, so they fail silently.

Every name this extension depends on belongs to the installed pi package: the guard that tells an
edit result from a write one, the `patch` field it counts, the theme colours it paints with, and
the footer call itself. None of them is checked at load time, because pi strips types rather than
compiling them, so a renamed field leaves an extension that loads, runs on every tool result, and
reports `+0/-0` for the rest of the session. From the user's side a velocity segment stuck at zero
looks exactly like a session that changed nothing.

So the assertions here read both halves and compare them: whatever the extension imports, the
package must export; whatever field it reads, the package must still declare. That is the same
bargain [test_pi_discovery.py](test_pi_discovery.py) makes with `loadSkillsFromDir`, and it skips
rather than fails when pi is absent for the same reason, since pi is installed by the role these
tests cover and `make test` promises to run with nothing configured.

Name checks cannot say whether the counting is right, though, and a footer that is merely wrong
looks the same as one whose field was renamed. So the counting half runs for real: the extension
is copied beside a link to pi's `node_modules`, handed patches pi's own generator built, and asked
what it makes of them.

The one rule not expressed as either is the last test: the counts come from pi's patch, so a diff
computed here would be a second implementation of something pi already did, and it would disagree
with `git diff` the first time one call carried two edits.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from dotkit.testing import PI_EXTENSIONS, REPO

EXTENSION = PI_EXTENSIONS / "velocity.ts"
TASKS = REPO / "roles/ai/tasks/main.yml"

PACKAGE = "@earendil-works/pi-coding-agent"

# Where every number in the segment comes from. Pi declares a `diff` field beside it for display,
# so a rename would not break the guard that reads this one: the extension would find undefined
# and quietly count nothing.
PATCH_FIELD = "patch"

# The private function the behavioural half drives, re-exported into a copy of the extension so
# pi's own surface stays a single default export.
COUNTER = "countPatch"

# Pi's patch generator, so the patches counted here are the ones pi's edit tool hands the
# extension rather than literals written to match what this file believes that format to be.
PATCHER = "core/tools/edit-diff.js"

# Reads a `{ before, after }` pair on stdin and prints pi's patch for it beside the counts the
# extension reported. Both halves in one process, so nothing here reimplements either.
RUNNER = """
import { %(counter)s } from "./velocity.ts";
import { generateUnifiedPatch } from %(patcher)s;

let raw = "";
process.stdin.setEncoding("utf8");
for await (const chunk of process.stdin) raw += chunk;
const { before, after } = JSON.parse(raw);
const patch = generateUnifiedPatch("SKILL.md", before, after);
process.stdout.write(JSON.stringify({ patch, ...%(counter)s(patch) }));
"""


@pytest.fixture(scope="module")
def source():
    return EXTENSION.read_text()


@pytest.fixture(scope="module")
def dist():
    """Pi's own `dist`, or a skip.

    Found through the `pi` on PATH rather than a pinned cellar path, so a version bump is
    followed rather than reported as missing.
    """
    binary = shutil.which("pi")
    if binary is None:
        pytest.skip("pi is needed to check the extension against its own API")
    root = Path(binary).resolve().parent.parent
    for prefix in ("lib/node_modules", "libexec/lib/node_modules"):
        found = root / prefix / PACKAGE / "dist"
        if found.is_dir():
            return found
    pytest.skip(f"no {PACKAGE} dist beside {binary}")


@pytest.fixture(scope="module")
def declarations(dist):
    """Every `.d.ts` in pi's dist as one string, read once for the whole module."""
    return "\n".join(path.read_text() for path in dist.rglob("*.d.ts"))


def imported(source):
    """The names the extension imports from pi, type imports included."""
    # `[^}]` rather than a lazy `.`, which crosses the closing brace of an earlier import and
    # returns the names of whichever block precedes this one.
    block = re.search(rf'import \{{([^}}]*)\}} from "{re.escape(PACKAGE)}"', source, re.S)
    assert block, "the extension must import from pi by package name, as guardrails.ts does"
    return {name.replace("type ", "").strip() for name in block.group(1).split(",") if name.strip()}


def test_every_imported_name_is_exported_by_pi(source, dist):
    """A name pi does not export is an import error at load, which pi reports as an extension
    that failed rather than as a footer that is missing. Cheap to check, and the whole file rests
    on five of them."""
    exports = (dist / "index.d.ts").read_text()
    for name in imported(source):
        assert name in exports, f"{name} is not exported by {PACKAGE}"


def test_the_counted_field_is_still_declared(source, declarations):
    assert PATCH_FIELD in source
    assert re.search(rf"\b{PATCH_FIELD}: string", declarations), (
        f"pi no longer declares a `{PATCH_FIELD}: string` on its edit details, so the velocity "
        f"counts have nothing to read and the segment silently reports +0/-0"
    )


def test_the_theme_colours_exist(source, declarations):
    """`theme.fg` takes a `ThemeColor`, and an unknown one is not an error at runtime: pi returns
    the text unpainted, so the segment loses its colour rather than saying anything."""
    palette = re.search(r"export type ThemeColor = ([^;]+);", declarations)
    assert palette, "pi no longer declares a ThemeColor union"
    allowed = set(re.findall(r'"([^"]+)"', palette.group(1)))
    used = set(re.findall(r'theme\.fg\("([^"]+)"', source))
    assert used, "the extension must paint through theme.fg, so the segment follows the theme"
    assert used <= allowed, f"not pi theme colours: {sorted(used - allowed)}"


def test_the_glyph_is_read_rather_than_typed(source):
    """`⚡` is Claude's statusline.sh glyph too, so it lives in statusline.json and both read it.
    A copy here renders correctly today and stops matching the first time one is changed."""
    vocabulary = json.loads((REPO / "roles/ai/files/statusline.json").read_text())
    assert 'glyph("velocity")' in source
    # Past the file's header comment, which names the segment it renders and is prose.
    code = source.split("*/", 1)[1]
    assert vocabulary["glyphs"]["velocity"] not in code, (
        "the velocity glyph is hardcoded in the segment again; it belongs to statusline.json"
    )


def test_the_counts_use_the_themes_diff_colours(source):
    """Rather than success and error, so the segment agrees with the diffs pi renders above it
    instead of reading as a pass and a failure."""
    used = set(re.findall(r'theme\.fg\("([^"]+)"', source))
    assert {"toolDiffAdded", "toolDiffRemoved"} <= used


def test_the_footer_is_written_through_set_status(source, declarations):
    """The one call that puts anything on screen, and the only one of these UI methods that
    survives RPC mode, where setFooter and the widget calls are documented no-ops."""
    assert "ctx.ui.setStatus(" in source
    assert "setStatus(key: string" in declarations


def test_the_status_is_cleared_rather_than_zeroed(source, declarations):
    """Passing undefined is how pi drops a status entry, so a fresh session shows no segment
    instead of a `+0/-0` that reads as a finished run which changed nothing."""
    assert "setStatus(STATUS_KEY, undefined)" in source
    assert "text: string | undefined" in declarations


@pytest.fixture(scope="module")
def counter(dist, tmp_path_factory):
    """The extension's own line counting, callable from python.

    A grep for `startsWith("---")` cannot tell a test for the file header from a test for
    anything beginning with it, and that difference is the whole of the bug this drives out. So
    the extension is copied beside a link to pi's `node_modules` and run, the way
    [test_pi_discovery.py](test_pi_discovery.py) runs pi's own skill loader.
    """
    if shutil.which("node") is None:
        pytest.skip("node is needed to run the extension's own counting")
    home = tmp_path_factory.mktemp("velocity")
    # A `node_modules` beside the copy rather than NODE_PATH, which node's ESM resolver ignores.
    (home / "node_modules").symlink_to(dist.parents[2])
    (home / "velocity.ts").write_text(f"{EXTENSION.read_text()}\nexport {{ {COUNTER} }};\n")
    runner = home / "run.mjs"
    runner.write_text(RUNNER % {"counter": COUNTER, "patcher": json.dumps(str(dist / PATCHER))})
    return runner


def counted(counter, before, after):
    """What the extension counts for the patch pi builds between two versions of a file."""
    done = subprocess.run(
        ["node", str(counter)],
        input=json.dumps({"before": before, "after": after}),
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def doc(*body):
    """A file, newline-terminated, since that is what pi diffs."""
    return "".join(f"{line}\n" for line in body)


def test_a_removed_frontmatter_delimiter_is_counted(counter):
    """Removing a line whose content is `---` produces the patch line `----`, and a skipping rule
    keyed on how a line begins reads that as a file header and drops it. Every skill and agent
    file in this repo is delimited by `---`, so editing frontmatter is the common case and this is
    the reading the footer gets most often, not a corner."""
    result = counted(
        counter,
        doc("---", "name: x", "---", "body", "tail"),
        doc("name: x", "body", "tail"),
    )
    assert "----" in result["patch"], "pi no longer prefixes a removed line with a bare `-`"
    assert (result["added"], result["removed"]) == (0, 2)


def test_the_file_headers_are_not_counted(counter):
    """Both of them, or every edit scores one phantom addition and one phantom removal."""
    result = counted(counter, doc("alpha", "beta"), doc("alpha", "gamma"))
    assert result["patch"].startswith("--- SKILL.md\n+++ SKILL.md\n")
    assert (result["added"], result["removed"]) == (1, 1)


def test_a_changed_line_that_looks_like_a_header_is_counted(counter):
    """`---` and `+++` are content in the files this repo edits, so what a line is has to be
    decided by where it sits in the patch rather than by the characters it opens with."""
    body = doc("alpha", "+++", "---", "omega")
    trimmed = doc("alpha", "omega")
    assert counted(counter, body, trimmed)["removed"] == 2
    assert counted(counter, trimmed, body)["added"] == 2


def test_both_sides_tally_across_hunks(counter):
    """Pi asks for four lines of context, so a second change far enough away arrives in a hunk of
    its own. A count that stopped at the first hunk would still look plausible in the footer."""
    before = [f"line-{n}" for n in range(1, 31)]
    after = list(before)
    after[1:2] = ["line-2a", "line-2b"]
    after.remove("line-25")
    result = counted(counter, doc(*before), doc(*after))
    assert sum(line.startswith("@@") for line in result["patch"].split("\n")) == 2
    assert (result["added"], result["removed"]) == (2, 2)


def test_a_failed_call_is_not_counted(source):
    """A refused write changed nothing on disk. Counting it would make the guardrails extension
    look like churn every time it blocked something."""
    assert "event.isError" in source


def test_no_diff_is_computed_here(source):
    """The rule that keeps this an adapter, as it keeps guardrails.ts one.

    Pi already produced the patch, and each entry in an `edits` array is matched against the
    original file rather than against the results of the entries before it, so a count derived
    from those entries disagrees with `git diff` whenever one call carries two of them. Reaching
    for those fields is the shape that mistake takes.
    """
    for field in ("oldText", "newText"):
        assert field not in source, (
            f"velocity.ts reads {field}, which means it is deriving a diff pi already reported. "
            f"Count the patch pi applied instead."
        )


def test_the_role_installs_the_extension():
    """The glob covers any `.ts` dropped in the directory, so this file needs no task of its own.
    Asserted anyway, because that is exactly the kind of thing a later refactor narrows to a named
    list, and a dropped extension is silent at both ends."""
    assert "files/pi/extensions/*.ts" in TASKS.read_text()
