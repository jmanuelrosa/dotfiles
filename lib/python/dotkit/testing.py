"""Where things are, for tests that need to read the repo.

One definition of the checkout root, and one name for each tree a suite reads. Five
suites derived these independently before this module existed, each with its own climb
of `.parents[n]` from wherever the test file happened to sit.

That duplication was not merely untidy. Every suite reached its constants through
`from conftest import REPO`, and in pytest's prepend import mode a `conftest.py` in a
directory with no `__init__.py` is named, literally, `conftest`. With two suite
directories on `sys.path`, `sys.modules['conftest']` holds whichever loaded last and a
test module's `import conftest` binds against the wrong file. It fails silently when
the two happen to agree, which is exactly what it did here: four suites collected
clean against claude-kit's conftest for two commits.

So the rule this module exists to enforce: **a test module imports shared names from
here, never from a module whose name another directory could also claim.**

Deliberately pytest-free. `dotkit` is stdlib-only at runtime, and a fixture defined
here would make that false the moment a tool imported the package. Fixtures belong in
each suite's own `conftest.py`, which is the one place a bare name is safe.

`REPO` is derived through `resolve()`, so it is the same path whether this module was
imported through `lib/python` or through the `dotkit` symlink beside a tool. Nothing
here may compare unresolved paths.
"""

from pathlib import Path

# lib/python/dotkit/testing.py -> lib/python/dotkit -> lib/python -> lib -> checkout
REPO = Path(__file__).resolve().parents[3]

# Claude Code's payload: artifacts that ship into ~/.claude rather than onto PATH.
CLAUDE = REPO / "roles/ai/files/claude"
SKILLS = CLAUDE / "skills"
AGENTS = CLAUDE / "agents"
PLUGINS = CLAUDE / "plugins"
HOOKS = CLAUDE / "hooks"

SKILL_REGISTRY = CLAUDE / "skill-registry.json"
AGENT_REGISTRY = CLAUDE / "agent-registry.json"

# Pi's payload. Smaller than Claude's because most of what Pi loads is Claude's: the skills
# and AGENTS.md are shared by symlink, and only settings, models, themes and the extensions
# are Pi's own.
PI = REPO / "roles/ai/files/pi"
PI_EXTENSIONS = PI / "extensions"

# Authored tooling, one directory per role that owns some.
AI_SCRIPTS_DIR = REPO / "roles/ai/files/scripts"
APPS_SCRIPTS_DIR = REPO / "roles/apps/files/scripts"
WORK_SCRIPTS_DIR = REPO / "roles/work/files/scripts"
CORE_SCRIPTS_DIR = REPO / "roles/coreutils/files/scripts"

# The fish half of the output vocabulary lives here, and test_ui.py runs it for real to
# diff its bytes against this package's.
FISH_FUNCTIONS = REPO / "roles/shell/files/fish/functions"


def force_colour(monkeypatch, on):
    """Turn colour on or off for an in-process render.

    colors.enabled reads the environment per call, so this is all a test needs to make
    a non-tty stdout behave like a terminal, or the reverse. The `coloured` and `plain`
    fixtures wrap it for the common case; test_help calls it directly because it
    renders the same help twice, once each way, inside a single test.
    """
    if on:
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("FORCE_COLOR", "1")
    else:
        monkeypatch.delenv("FORCE_COLOR", raising=False)
        monkeypatch.setenv("NO_COLOR", "1")
