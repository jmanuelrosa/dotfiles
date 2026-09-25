# harness

The harness-neutral payload Claude Code, Pi and Codex CLI run over: shared instructions, rules, hooks, agents, plugins and skills, plus one policy rendered into each harness's config.
How it is linked into `$HOME` and what each harness loses in translation is in the dotfiles repo's [ai role README](../../README.md) and [harnesses](../../../../docs/internals/harnesses.md).

## Moving it out

The tree is built to be lifted into its own repository.
`harness.toml` marks the root and every reader walks up to it, so no path inside depends on where the tree sits, and `lib/harnessgen` needs nothing but Python 3.11 or newer: `bin/harness-build build` runs from a bare checkout.

What still ties it to the dotfiles repo, and what a move has to take with it:

- **Linking is Ansible's.** `HARNESS_LINKS` and the link, prune and `apply codex` tasks live in `roles/ai/`. A standalone repo needs an installer that reads the same table.
- **Pi's derivation specs live outside.** `test_pi_sandbox.py`, `test_pi_permissions.py` and the other `test_pi_*` suites are in `lib/python/tests/` and import `dotkit.testing`. The generator's own suites in `tests/` import only `harnessgen`.
- **One script imports the repo's library.** `plugins/product-team/skills/product-lead/scripts/pt.py` imports `dotkit.ui` for its output vocabulary.
- **The Makefile targets and `pytest.ini` roots are the repo's.** `make harness*` wraps `bin/harness-build` through `uv`, and `pytest.ini` puts `lib/` on the import path.
- **Rendered files name the checkout.** `{harness}` in `policy/sandbox.toml` expands to this tree's absolute path at render time, so a clone elsewhere runs `harness-build build` once before its rendered files are right.
- **Some comments cite repo paths** (`roles/ai/files/harness/...`, `lib/python/tests/...`). They are prose, not lookups, and read wrong rather than break.
- **Kura is already separate.** It is installed from its own release and pointed at `kura/catalog/`, so only the catalog moves with the tree.
