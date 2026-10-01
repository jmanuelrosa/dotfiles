# Kura Television helpers

`_tv_kura_list` renders the skill rows used by the Television cables.
`_tv_kura_toggle` applies installation and global-scope changes to the selected rows.
Both derive state exclusively from `kura list --json`; neither reconstructs the catalog, workspace anchoring, or scope rules.

Requires `kura` and `jq`.
These are picker helpers rather than standalone user commands.
Their fixed-width rows intentionally stay outside the shared `_ui` line vocabulary because Television owns their layout.
