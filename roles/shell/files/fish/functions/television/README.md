# Television shell pickers

`tv_change_dir` opens the `dirs` cable and changes to the selected directory.
`tv_history` opens Fish history using the current prompt as an exact substring query, then replaces the prompt with the selection.
Both repaint the command line afterward.

These functions run in an interactive prompt and require `tv`.
`config.fish` binds `tv_change_dir` to `alt-c`.
