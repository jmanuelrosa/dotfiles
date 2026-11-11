---
name: dotfiles QA index
description: Native test workflow and harness parity testing conventions
type: project
---

- Run tests through `make test PYTEST='uv run --offline --with pytest --with pyyaml pytest <paths> <selectors>'` when cached dependencies are available and sandbox networking cannot reach PyPI. Make appends `-q`.
- `pytest.ini` lists the suite roots and provides `dotkit` and `harnessgen` import paths. There is no separate configured Python typecheck target.
- Hooks named `.sh` can be Python scripts. Their subprocess tests submit synthetic JSON events to the actual hook and check exit 0/2.
- Pi guardrails runtime tests in `lib/python/tests/test_pi_guardrails.py` currently use Node with the installed `@earendil-works/pi-coding-agent` package. Reuse `runner`, `isolated_runner`, `run_in_node`, and `guarded_call`; `real_runner` links actual hooks and the generated table. The runner skips when Pi/Node is absent; CI currently does not provision Pi.
- Guard tests needing remotes should initialize throwaway Git repos, disable global/system Git config and inherited `GIT_*` inputs, and never run the push command itself. Feed push text to the guard only.
- In the sandbox `uvx --offline ruff@0.17.2` can fail writing its tools directory; `uv run --offline --with ruff==0.17.2 ruff check <paths>` executes the same project-pinned linter from the available cache.
- Use `fish --no-config -c` for shell logic to avoid user shell startup SSH-agent writes. Scope diff checks to owned files when the worktree has unrelated user changes.
