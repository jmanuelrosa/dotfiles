# Television shell pickers

`tv_change_dir` opens the `dirs` cable and changes to the selected directory.
`tv_history` opens Fish history using the current prompt as an exact substring query, then replaces the prompt with the selection.
Both repaint the command line afterward.

The managed cables show their main shortcuts above the search input and label previews with the selected entry.
Panels share the Solarized theme, horizontal padding, and wrapped previews.
Jira's named sources show the active view while cycling with `Ctrl-S`.

These functions run in an interactive prompt and require `tv`.
`config.fish` binds `tv_change_dir` to `alt-c`.
