# Divebell Browser Setup

Use this setup for every MF workflow that needs a real page. Read
`../divebell.md` first.

## Prepare

```bash
divebell setup
divebell --help
```

`setup` checks and repairs the browser environment only when necessary.
Do not create a copied Chrome debug profile, expose a CDP port, edit shell
startup files, or kill the user's Chrome.

For MF structured evidence, make sure the trusted Extension and its installed
Skill have been discovered as described in `../divebell.md`, then open:

```bash
divebell open "<url>" --mf
```

Divebell uses the most recently used Chrome Profile by default. For an explicit
authorized context, inspect and select it through Divebell:

```bash
divebell profiles
divebell open "<url>" --profile "<name-or-path>" --mf
divebell open "<url>" --state "<state-path>" --mf
```

Use `--no-default-profile` only for an intentionally clean project Restore
State. Follow the installed Divebell CLI Skill for authentication diagnosis;
never copy cookies or bypass an access boundary.

## Verify

After opening, use:

```bash
divebell page-snapshot --interactive
divebell mf status
```

If the page redirects to login or shows an authorization wall, continue only
with an authorized Profile or saved state. If the service itself is
unreachable, distinguish that with a cheap HTTP check, then fix or start the
service before repeating `divebell open`.

If `mf status` reports missing page context, late injection, or incomplete
history, reopen with `--mf`, reproduce the same user path, and retry. Do not
replace this workflow with raw CDP or another browser runtime.
