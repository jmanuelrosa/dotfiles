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

The one rule not expressed as a name is the last test: the counts come from pi's patch, so a diff
computed here would be a second implementation of something pi already did, and it would disagree
with `git diff` the first time one call carried two edits.
"""

import re
import shutil
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

# A unified patch's file headers. The extension must skip both, or every edit scores two phantom
# lines: one addition for `+++` and one removal for `---`.
HEADERS = ("+++", "---")


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
    block = re.search(rf'import \{{(.*?)\}} from "{re.escape(PACKAGE)}"', source, re.S)
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


def test_patch_headers_are_skipped(source):
    """Without this the counts are wrong on every single edit, which is the one bug here that
    would look plausible rather than broken."""
    for header in HEADERS:
        assert f'"{header}"' in source, f"the patch header {header} is not skipped"


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
