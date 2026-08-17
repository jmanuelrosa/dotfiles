# Script output style


Every script here prints through **one vocabulary, expressed twice**: [_ui.fish](../../roles/shell/files/fish/functions/_ui.fish) for fish and [dotkit/ui.py](../../lib/python/dotkit/ui.py) for python. Same kinds, same glyphs, same palette, same reset bytes. **Never hand-roll `set_color` / ANSI escapes in a new script**, and never invent a glyph: if a line does not fit a kind below, the kind is missing and belongs in both files.

| kind | renders | for |
|---|---|---|
| `title` | bold text | a section heading, and the only line that may carry a topic emoji |
| `step` | cyan `→` | an action being taken |
| `ok` | green `✓` | it worked |
| `warn` | yellow `⚠` | worth reading, not fatal |
| `err` | magenta `✗`, on **stderr** | a refusal |
| `item` | dim `·`, indent 2 | one entry of a list |
| `note` | dim text, indent 2 | an aside under the line above it |
| `done` | `✨` + text | the closing summary, one per run |

```fish
_ui title "🧹 Removing Claude artifacts"     # fish: _ui <kind> <text>, -i N to indent
_ui item (_ui path "$dir")                   # _ui path collapses $HOME to ~
_ui done "Removed 3 of 3"
```
```python
ui.title("🧩 Available skills:")             # python: ui.<kind>(text, indent=…)
ui.item(ui.path(destination))                # ui.render(kind, text) returns the string
ui.done("42 skills, 3 installed")
```

Two rules carry the style, and both exist for a reason:

- **Status is a coloured glyph; a topic is an emoji, and only on a `title` or a `done`.** Emoji are double-width, so one used as a row marker knocks every following column out of alignment; `✓ ⚠ ✗ · →` are narrow and keep a listing a listing. `test_ui.py` asserts this against `unicodedata`, and `✨` is wide but allowed because `done` starts at column zero with nothing beneath it. Pick a topic emoji with emoji presentation by default (`🧹 📦 🔎 🔄 📋 🧩 🤖 🔌 📚`); anything needing U+FE0F to render as an emoji renders as monochrome text on some terminals.
- **Colour is decided per stream, not by `set_color`.** `NO_COLOR` beats `FORCE_COLOR`, which beats the tty check, so piping to a file yields plain text and `cmd 2>log` never writes escapes into the log. Both halves agree on the order, which is what lets a test harness force colour on for either.

The two halves are held together by a **differential test**: `test_both_halves_render_identical_bytes` renders every kind through each and compares the bytes, so drift in either fails rather than being noticed by eye. A row (a name plus coloured suffixes) is still composed by hand from `ui.paint` in `listing.py`, because only its glyph is coloured; the palette is the shared one even there.

**In fish, a composing helper cannot make that per-stream decision, and must not try.** `_ui color` and `_ui paint` are only useful inside a command substitution, and fish gives one a pipe of its own for stdout, so the isatty they would run answers for that pipe and never for the terminal: it is false however the command was run. Deciding there is what left every `lns` arrow and every `clean_claude` marker uncoloured on a real terminal, and it is undetectable by eye in a test harness, since forcing colour on is exactly what hides it. So the two helpers state **intent** (`NO_COLOR` alone silences them) and the printing kind resolves it, stripping the escapes its own stream refuses, as `dotkit.colors.for_stream` does in python. `ui.paint` needs none of this: in-process it can see the stream it is painting for.

A fish script that prints a row with `echo` or `printf` has no printing kind to resolve it, so it asks **`_ui color-enabled`** first, as a bare command, while fd 1 is still its own stdout, and builds its palette inside that `if`. Initialise each colour to `""` rather than leaving it unset: an empty *list* vanishes from a `printf` argument list and shifts every argument after it. No script does this today (`claude-skill` and `claude-agent` were the two, and they are gone), so this is the rule for the next one rather than a description of the current tree.

A python tool reaches `ui` by putting **its own directory** on `sys.path` and importing `dotkit`, exactly as the claude-kit shim reaches its package:

```python
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dotkit import ui
```

That works because every python tool directory holds a **committed relative symlink** named `dotkit`, pointing at [lib/python/dotkit](../../lib/python/dotkit). The one real copy lives outside the roles because neither role can import from the other, and `weekly-recap` in `work` needs the same vocabulary `claude-kit` in `ai` does. A copy would be a third statement of a style that is already stated twice, so it is a link. `resolve()` follows both the `~/.local/bin` install symlink and this one, which is what makes a tool directory self-contained enough to `cp -r` anywhere and still run.

These are the **only committed symlinks in the repo** (`mode 120000`), so `test_suites.py` asserts each resolves to the real package and that its target is relative: a clone with `core.symlinks=false` materialises them as regular files holding a path, and the resulting `ImportError` points nowhere near the cause.

Fish scripts anywhere, including the work role's, autoload `_ui` from `~/.config/fish/functions`; the `work` profile includes the `shell` role, so it is always present.

**Television cable rows are the one exemption**, and deliberately so: [_tv_claude_fmt](../../roles/shell/files/fish/functions/_tv_claude_list.fish) and [_tv_jira](../../roles/work/files/fish/functions/_tv_jira.fish) emit fixed-width columns for a picker to lay out and filter (`string match -e '[linked]'` reads them back), not lines for a human to read, and `_tv_jira` colours from inside a jq program where `_ui` cannot reach. Their emoji are type icons in a fixed column, not status.
