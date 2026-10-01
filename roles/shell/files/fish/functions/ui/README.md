# Shared Fish output vocabulary

`_ui` is the Fish counterpart of Python's `dotkit.ui`.
Scripts use these kinds instead of inventing colors, glyphs, or formatting:

| Kind | Purpose |
|---|---|
| `title` | Heading; may include a topic emoji |
| `step` | Work in progress |
| `ok` | Successful action |
| `warn` | Warning |
| `err` | Error, sent to stderr |
| `item` | Listed entry |
| `note` | Supporting detail |
| `done` | Closing summary |
| `blank` | Empty line |

```fish
_ui title "Cleanup"
_ui step "Inspecting candidates"
_ui -i 4 item "example"
_ui done "Finished"
```

`-i N` sets indentation before the kind.
`color`, `paint`, and `path` compose fragments instead of printing lines; `path` shortens the home-directory prefix to `~`.
Printed lines honor `NO_COLOR`, then `FORCE_COLOR`, then the destination stream's tty status.
Composed fragments retain escapes unless `NO_COLOR` is set because Fish command substitutions always present a pipe; the printing kind strips escapes when necessary.
Use `color-enabled` before composing rows that will be printed outside `_ui`.

A differential test keeps the Fish and Python renderers byte-for-byte aligned.
See [script output style](../../../../../../docs/internals/script-output-style.md) for the complete contract.
