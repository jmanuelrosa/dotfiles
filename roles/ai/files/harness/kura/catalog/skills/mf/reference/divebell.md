# Divebell Browser And MF Extension

Read this reference before any MF workflow opens, inspects, or operates a real
browser page.

Divebell is installed on the Agent machine. Do not add `@divebell/cli` or
`@divebell/extension-mf` to the application being diagnosed.

## Install And Discover The CLI Skill

Use an existing global `divebell` command when available. Otherwise install
it globally:

```bash
npm install --global @divebell/cli
```

Then inspect the installed CLI and read its bundled Skill:

```bash
divebell --help
divebell skill
```

`divebell skill` prints an absolute path to the installed Divebell
`SKILL.md`. Read that file in full before the first browser operation and
follow its authentication, session, command-discovery, and evidence rules. If
the printed path is missing or unreadable, reinstall/update the published CLI
with the same global install command, rerun `divebell skill`, and do not guess
the workflow from memory.

Treat installed `--help` output as the command source of truth:

```bash
divebell setup
divebell <command> --help
```

## Install And Discover The MF Extension Skill

Check whether the MF command is already installed:

```bash
divebell mf --help
```

If the CLI reports an unknown `mf` command, install the trusted MF Extension:

```bash
divebell extensions add @divebell/extension-mf
```

Do not infer another package name. After installation, discover the actual
command and its command-specific Skill:

```bash
divebell --help
divebell mf --help
divebell mf --skill
```

`divebell mf --skill` prints the installed Extension Skill path. Read that
`SKILL.md` in full before running an MF subcommand. The installed command
Skill, not this repository's memory of a release, governs command selection,
result fields, ambiguity handling, and compatibility warnings.

If a custom distribution exposes a different command name, use the name shown
by `divebell --help` or `divebell stack`, then run
`divebell <command> --skill`. Keep that command name for the rest of the
task.

## Open The Page

Open every page that needs MF structured evidence with the Extension's open
hook enabled:

```bash
divebell open "<url>" --mf
```

The bare `--mf` on `divebell open` enables diagnostics before navigation.
It is different from `--mf <name>` on some `divebell mf` subcommands, which
only selects one visible MF instance after the page is open.

By default Divebell reuses the current OS user's most recently used Chrome
Profile. Use `divebell profiles`, `open --profile`, or `open --state` only
when the task requires a specific prepared account or environment. Use
`--no-default-profile` only when a clean project Restore State is intended.
Never copy a Chrome profile, launch Chrome with
`--remote-debugging-port`, kill the user's Chrome, or bypass authorization.

If an MF command reports late injection, missing page context, or incomplete
earlier history, reopen the page with `--mf`, reproduce the same authorized
user path, and rerun the smallest relevant command.

## Browser Operation Rule

After selecting Divebell, keep every browser action and browser-derived fact in
the same Divebell session:

- use `page-snapshot`, `click`, `fill`, `select`, `press`, and
  `wait` for page interaction;
- use the installed MF Extension command for MF state, Remote, Shared, Bridge,
  trace, and module-performance evidence;
- use `console`, `errors`, `network`, `eval`, `get-window`, and
  `screenshot` only for evidence the MF Extension does not expose; and
- verify the final page result separately from MF runtime loading success.

Do not mix Divebell with raw CDP/WebSocket clients, Playwright, Puppeteer,
Cypress, Electron test browsers, another browser-control skill, or temporary
browser scripts. Do not add Runtime SDK integration merely to inspect a page.
