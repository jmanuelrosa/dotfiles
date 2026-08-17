# Where a test lives


**Beside what it exercises, unless that thing ships somewhere.** Two shapes, and the difference is whether a `tests/` directory would be carried off the machine with the code:

- **A tool** owns its suite: `files/scripts/<name>/tests/`. Nothing links it anywhere, so it costs nothing.
- **A payload artifact** (a skill's `scripts/`, a hook) is symlinked whole into `~/.claude`, so its suite ships too. They still sit beside their subject and locate it **relatively**, so moving a skill moves its tests with it. `~/.claude/skills/pr/tests/` therefore exists after a sync: inert, since Claude Code reads `SKILL.md` and what it references, and `PYTHONDONTWRITEBYTECODE` in the Makefile and CI keeps pytest from adding `__pycache__` to a shipped skill. Only the **locally authored** skills may hold one: `claude-kit update` replaces an upstream tree wholesale and preserves nothing in the destination, so a suite under one would be deleted on the next sync.

Every root is listed in [pytest.ini](../../pytest.ini) rather than in the Makefile, so a bare `pytest` collects what `make test` does. That file is the single point of failure worth knowing about: pytest only **warns** when a `testpaths` entry collects nothing, which is how four suites and 2,174 lines of tests stayed dark for two commits. [lib/python/tests/test_suites.py](../../lib/python/tests/test_suites.py) closes that loop, asserting every entry exists, that no suite directory in the known families is missing from the list, that nothing imports `conftest`, and that module basenames are unique across suites. It catches an empty leftover directory too, which git cannot show you because it does not track one.
