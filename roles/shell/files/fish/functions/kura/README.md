# Kura Television helpers

`_tv_kura_list` renders the skill, agent, and bundle rows used by the Television cables.
`_tv_kura_toggle` applies installation and global-scope changes to the selected rows.
`_tv_kura_skill_action` expands category selections for skill actions and previews.
All derive state exclusively from `kura list`; none reconstructs the catalog, workspace anchoring, or scope rules.

Rows fit the name and status columns to the current results, with status before the dimmed groups.
Linked entries are green, available entries cyan, and missing downloads yellow, using the shared terminal palette and respecting `NO_COLOR`.
Groups stay in the results because Television searches displayed text, so hiding them in a preview would remove group matching.

In `tv kura-skills`, press `Ctrl-S` to cycle to **Categories**.
Rows show each category's skill count and how many are already linked.
Use `Tab` to select categories such as `@frontend` and `@gcp`, then `Enter` to install their skills.
Overlapping skills install once, already-linked skills stay linked, and each skill keeps the scope reported by Kura.
Individual skill rows still toggle installation with `Enter`.
Category previews list their skills; `Ctrl-D`, `Ctrl-U`, and `Ctrl-O` check, update, or edit all selected category members.

Requires `kura` and `jq`.
These are picker helpers rather than standalone user commands.
Their fixed-width rows intentionally stay outside the shared `_ui` line vocabulary because Television owns their layout.
