# Long-Chain Divebell Capture

Keep the same Divebell page and authenticated browser context across the whole
user path. Read `../divebell.md` first.

## Workflow

```bash
divebell open "https://example.com" --mf
divebell page-snapshot --interactive

divebell click "Profile"
divebell wait --load domcontentloaded
divebell click "Favorites"

divebell page-snapshot --interactive
divebell click "Add"
divebell wait --load networkidle

divebell mf status
```

Use references from `page-snapshot --interactive` when visible text is
ambiguous:

```bash
divebell fill "<input-ref-or-selector>" "Module Federation"
divebell select "<select-ref-or-selector>" "Production"
divebell click "<button-ref-or-selector>"
```

Inspect each command's installed `--help` instead of assuming selector or
wait syntax. For a custom dropdown, use the page snapshot and ordinary
`click` operations; `select` is for native dropdowns.

After reproducing the failure, run the smallest MF command selected by the
installed Extension Skill, for example:

```bash
divebell mf remote trace "<remote/expose>"
divebell mf shared trace "<package>"
```

Then use `divebell errors`, `divebell console`, or `divebell network`
only for browser evidence missing from the structured MF result. Do not detach
the page into a raw CDP session or switch to another browser tool mid-chain.

If the workflow opens another tab, use `divebell tab --help` and keep all tabs
inside the same Divebell session. Close the session with `divebell stop` only
when the task is complete and the browser context is no longer needed.
