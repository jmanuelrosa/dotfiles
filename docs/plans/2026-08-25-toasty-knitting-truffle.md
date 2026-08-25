# One status line vocabulary, three readers

## Context

Claude's `statusline.sh` and pi's `footer.ts` now render the same information in two languages, and the values they agree on are typed out in both.
The handoff threshold is the worst case: `35` is a literal in `statusline.sh:28`, in `hooks/context-nudge.sh:44` and in `footer.ts`, and only two of those three are pinned against each other by a test.
The lockfile table, the gauge glyphs and the segment emoji are duplicated with no pin at all, so the first person to add `deno.lock` to one harness will ship a status line that disagrees with the other and nothing will say so.

The goal is that a value is written once and every harness follows.
Not shared rendering: the two colour models are genuinely different (truecolor Solarized stops against a user-authored pi theme), and pi's token format deliberately matches pi's own footer rather than Claude's.
Those stay separate and stay pinned by tests.

The mechanism already exists in this repo and is in production: `guardrails.ts:79` resolves its own symlink with `realpathSync(fileURLToPath(import.meta.url))` to find Claude's hook scripts inside the checkout.
Every artifact here is symlinked from `roles/ai/files/`, so any reader that resolves its own realpath can reach a sibling file with no new install task.

## The shared file

`roles/ai/files/statusline.json`, a sibling of `claude/` and `pi/` because it belongs to neither.

```json
{
  "handoffPct": 35,
  "bar": { "width": 8, "filled": "▓", "empty": "░" },
  "glyphs": {
    "repo": "📁", "node": "⬢", "packageManager": "📦",
    "velocity": "⚡", "rtk": "✂️", "model": "🤖", "cursor": "⌁", "warning": "⚠️"
  },
  "labels": {
    "context": "context", "handoff": "handoff",
    "rtkOn": "rtk", "rtkOff": "rtk off", "gatesOff": "gates off"
  },
  "packageManagers": [
    { "lockfile": "bun.lockb", "name": "bun" },
    { "lockfile": "bun.lock", "name": "bun" },
    { "lockfile": "pnpm-lock.yaml", "name": "pnpm" },
    { "lockfile": "yarn.lock", "name": "yarn" },
    { "lockfile": "package-lock.json", "name": "npm" },
    { "lockfile": "npm-shrinkwrap.json", "name": "npm" }
  ]
}
```

The array is ordered, specific before `npm`, because that order is what makes a bun repo carrying a `package-lock.json` read as bun.
An object keyed by lockfile would lose it.

## Readers

Every reader keeps its current literals as an in-code default and merges the file over them.
A missing or corrupt file then degrades to exactly today's behaviour rather than to an empty footer or a status line that exits non-zero, which is the one failure mode none of these three can afford.

| File | Resolves | Takes |
|---|---|---|
| `roles/ai/files/claude/statusline.sh` | `realpath(__file__)` → `../statusline.json` | threshold, bar, lockfile table, all glyphs, `rtk` wording |
| `roles/ai/files/claude/hooks/context-nudge.sh` | `realpath(__file__)` → `../../statusline.json` | threshold only, through the `read_json` helper it already has at line 66 |
| `roles/ai/files/pi/extensions/footer.ts` | `realpathSync(fileURLToPath(import.meta.url))` → `../../statusline.json` | threshold, bar, lockfile table, glyphs |
| `roles/ai/files/pi/extensions/velocity.ts` | same | `velocity` glyph |
| `roles/ai/files/pi/extensions/guardrails.ts` | same | `rtk` and `cursor` glyphs, `rtk` and gates wording |

The three pi extensions want one loader between them.
It cannot live in `extensions/`, because pi loads every `.ts` in that directory as an extension and a module with no default export would be reported as one that failed.
Put it at `roles/ai/files/pi/statusline.ts` and import it relatively.

**Verify that import first, before writing anything else.**
Pi loads extensions through jiti, and a relative `.ts` import from an extension is the one mechanism here with no precedent in this repo: `guardrails.ts` spawns Claude's files, it never imports one.
The check is two minutes with the harness this work already used:

```
node -e 'import("<pi dist>/core/extensions/loader.js").then(m => m.loadExtensions(["~/.pi/agent/extensions/footer.ts"], process.cwd())).then(r => console.log(r.errors))'
```

If jiti will not resolve it, fall back to an eight-line loader inlined in each of the three extensions.
That duplicates a loader, which is cheap, rather than the values, which is the thing this plan exists to stop.

## What stays duplicated, deliberately

- **The colour ramp.** `statusline.sh` interpolates truecolor Solarized stops; `footer.ts` paints with pi `ThemeColor` names so a user-authored theme in `roles/ai/files/pi/themes/` still governs. Sharing hex values would break the theme.
- **Token formatting.** Claude's `fmt_tokens` and pi's `formatTokens` round differently on purpose, because pi's matches pi's own footer and a session that switches renderings should see the same figures pi always showed it.

Both keep their existing pin tests, which is what stops the divergence from becoming accidental.

## Tests

- **New** `lib/python/tests/test_statusline_shared.py`:
  - the file parses and carries every key each reader asks for;
  - each reader's default block equals the shared file, so the fallback cannot drift from the source it mirrors (defaults duplicate the values by design, and this is the assertion that keeps that honest);
  - no reader hardcodes a value the file owns outside its default block, which is the guard that keeps the sharing real rather than decorative.
- **Update** `test_pi_footer.py::test_the_handoff_threshold_matches_the_claude_statusline` and `test_pi_guardrails.py::test_the_footer_mirrors_the_claude_statusline`: both now assert the two harnesses read the shared file, instead of comparing two literals.
- **New** minimal `statusline.sh` coverage, which has none today: it exits 0 and prints a non-empty line both with the shared file present and with it hidden. The fallback is the whole reason the load is safe, and nothing currently exercises it.

## Docs

- `docs/internals/pi-harness.md`: the footer section gains the shared-file mechanism beside the trade it already records.
- `docs/internals/context-hygiene.md`: name the file that owns the `35`, since the prose there is what the number answers to.
- `roles/ai/README.md`: one line, since the file is a new thing under `files/`.

## Verification

1. `make test`.
2. `statusline.sh` prints byte-identical output before and after, since no value changes: feed it a real payload on stdin and diff against a capture taken from the pre-change file.
3. Load all three extensions through pi's own `loadExtensions` and confirm no errors, then render the footer component against the real `solarized-dark` theme with a stub TUI, the harness this work already used.
4. The acceptance check for the whole change: set `handoffPct` to 50 in the JSON, confirm the marker moves in pi's footer, in Claude's status line and in the nudge hook without touching any other file, then set it back to 35.
5. Hide the JSON (`mv` it aside) and confirm all five readers still render today's values, then restore it.
