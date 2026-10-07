# ai

Installs and configures AI tooling: Claude Code, Pi (`@earendil-works/pi-coding-agent`, brewed as `pi-coding-agent`), Codex CLI, ChatGPT desktop, Cursor and Ollama.

## Layout

Everything the harnesses read lives in `files/harness/`, one self-contained tree that `harness.toml` marks as its root, so nothing in it hops out to the rest of the repo by relative path.

- `AGENTS.md`, `rules/`, `hooks/`, `agents/`, `statusline.json`, `rtk/`: shared by every harness, by symlink.
- `kura/catalog/`: standalone skills and agents with their registries, plus seat and product bundles under `kura/catalog/bundles/`, projected into each harness by kura.
- `policy/`: permissions, sandbox and hooks, written once in neutral TOML.
- `mcp.json`: user-global MCP server inventory shared across Claude, Pi and Codex without storing credentials.
- `lib/harnessgen/` and `bin/harness-build`: the stdlib-only generator that renders `policy/` into each harness's spelling. Its suites are in `tests/`.
- `adapters/<harness>/`: what only that harness reads, an `adapter.toml` for the knobs the policy has no word for, and `generated/` for the files rendered whole.

`HARNESS_LINKS` in `defaults/main.yml` is the one table of what gets linked where, per harness, and `HARNESS_ENABLED` picks which harnesses a machine gets.
The link tasks read that table generically, and prune any link in a globbed directory that points into this role but whose source is gone.

## The generator

`make harness` renders every file that differs, `make harness-check` names the drift, `make harness-report` lists what each harness cannot carry, and `make harness-apply` merges the policy and shared MCP servers into Codex's own config. `make harness-apply TARGET=claude` merges shared servers into `~/.claude.json`; `CHECK=1` previews either apply.
Claude's `settings.json` is merged key by key rather than written whole, because a running session writes it too, and it cannot be written from inside a Claude session: run `make harness` with none open.
The rules, the per-harness translations and what each one loses are in [harnesses](../../docs/internals/harnesses.md).

## What it does

- Installs pi-coding-agent, rtk and uv, plus casks for ChatGPT, Claude, Claude Code, Codex, Cursor and Ollama, via `BREW_PACKAGES`.
- Links each enabled harness's files from `HARNESS_LINKS`: `~/.claude/` for Claude Code, `~/.pi/agent/` for Pi, `~/.codex/` for Codex. Kura owns the global skill and agent links. The neutral `AGENTS.md` is Claude's `~/.claude/CLAUDE.md`, Pi's `~/.pi/agent/AGENTS.md` and Codex's `~/.codex/AGENTS.md`.
- Renders the shared `mcp.json` with Pi's Slack OAuth settings into `adapters/pi/generated/mcp.json` and links it to Pi's native `~/.pi/agent/mcp.json`. Claude and Codex receive both shared servers. Notion's existing MCP tool denies remain in force for Claude and Pi. Run `pi mcp list`, sign in with `pi mcp login <server>` as needed, then `/reload` in Pi.
- Runs `harness-build apply` for each enabled harness among Claude and Codex. For Claude it merges the shared MCP servers into `~/.claude.json`. For Codex it merges owned keys and MCP server names into `~/.codex/config.toml` and writes `~/.codex/rules/dotfiles.rules` as a real file. Neither is a link, because Codex writes both locations itself. After a first run, trust the two hooks once in Codex's `/hooks`.
- Configures Pi to call Ollama Cloud directly through `models.json`, without `pi-ollama-cloud` or a local Ollama server. `nemotron-3-ultra` and `gpt-oss:120b` are enabled as coding models available on the free account. In Pi, run `/login`, choose API key authentication, select `ollama-cloud`, and paste a key from the Ollama account settings.
- The Ollama app uses its own account session: run `ollama signin` after provisioning when using the CLI or desktop app.
- Pi's Cursor models come from the `npm:pi-cursor-sdk` package in `adapters/pi/settings.json`, not from a `cursor` block in `models.json`, which is only for HTTP APIs Pi already speaks. Auth is a Cursor SDK API key saved once with `/login` (or `CURSOR_API_KEY`), then `/cursor-refresh-models` if you logged in after startup. Desktop/CLI login is not reused, and the key stays out of the repo.
- Cursor-backed tool failures only ever show a canned reason (`missing completion`, `aborted`, `SDK run failed`, `run ended during drain`). `pi_debug` and `pi_last_error`, from the shell role's fish functions, launch pi with the package's debug capture on and print the real error back afterward.
- Links `adapters/pi/APPEND_SYSTEM.md` rather than a `SYSTEM.md`, because Pi reads the latter as a *replacement* for its own system prompt.
- Links the extension directories named by `PI_EXTENSIONS` into `~/.pi/agent/extensions/`, where Pi discovers each `index.ts`. Every directory carries a README explaining why it exists, what it owns and how it is verified. The `claude-ui` experiment is documented in the source tree but left out of the manifest, so it is not loaded.
- Gives Pi the same two permission layers Claude has: `adapters/pi/sandbox.json` for `pi-sandbox`, the layer that *contains*, and `adapters/pi/permission-system/config.json` for `@gotgenes/pi-permission-system`, the layer that *decides*. Both are rendered from `policy/`. The permission package is the one `packages` entry pinned to a version, because its breaking releases are fail-closed corrections that `pi update` must not move.
- `statusline.json` holds the values Claude's status line and Pi's footer both render, so a threshold or glyph is written once.
- Runs `herdr integration install` for each enabled harness among Claude and Pi, each only when `herdr integration status` does not report it current, so a herdr upgrade that ships a newer hook reinstalls on the next run.
- Links each tool named in `AI_SCRIPTS` into `~/.local/bin/`, from `files/scripts/<name>/<name>`. Today that is `tokencost`, which prices a stretch of work from the session transcripts: `tokencost <project>` buckets Claude Code spend by skill, and `tokencost --pi <project>` buckets Pi's by `provider/model`, using the cost Pi recorded rather than a rate table.
- Installs `kura` from its own repository: `get_url` fetches the release pinned in `KURA` to `~/.local/bin/kura` and verifies the checksum, so an upgrade and a rollback are the same edit in opposite directions.
- Links kura's machine config from `files/harness/kura/config.json` to `~/.config/kura/config.json` (Claude Code and Pi are the global harnesses, with Pi's installed subagent extension reading `.pi/agents` in projects), and links `~/.config/kura/catalog` to `files/harness/kura/catalog`. Then runs `kura sync`, which creates the native skill and agent roots and links every global artifact into them.

## Kura

Skills and standalone agents declare machine roots with `global: true`; their `groups` are descriptive only.
Bundle registry rows carry names and descriptive `groups`, not global policy, and all shipped bundles remain project-scoped.

The role runs `kura sync` on every play, so the global skills and agents always match the catalog.
After editing the catalog or a `global` flag between plays, run it by hand, and repair initialized projects with:

```bash
kura sync                              # project global skills and agents into both native harness views
kura converge --all --root ~/Developer # repair the skill views of every initialized project below ~/Developer
```

Codex is not a kura harness. It reads global skills from `~/.agents/skills/`, which exists because kura's `pi` harness writes it, so removing `pi` from `globalHarnesses` would also take Codex's skills away.
Claude's SessionStart hook runs `kura converge --quiet` when the cwd holds a `kura.json`, so an initialized project is repaired on open.

## Vars

- `BREW_PACKAGES`: formulas and casks, as above.
- `HARNESS_DIR`, `HARNESS_ENABLED`, `HARNESS_LINKS`: where the payload is, which harnesses a machine gets, and what each one links.
- `PI_EXTENSIONS`, `AI_SCRIPTS`, `KURA`: the Pi extension manifest, the linked scripts, and the pinned kura release.
- **There is no var for the global artifact set.** `kura sync` derives it from `global: true` in both registries and expands declared dependencies.

## Notes

The herdr integration is the one thing in `~/.claude/hooks/` this role does not link from the repo: herdr writes `herdr-agent-state.sh` there as a real file and appends its own `SessionStart` entry to `settings.json`, keyed on the absolute hook path. The `herdr` formula comes from the apps role, which runs before this one.

Library and SDK docs come from the Context7 CLI, run on demand via `bunx ctx7` (bun is installed by the apps role) on the free anonymous tier, so nothing is installed and no API key is configured. The usage rule lives in `files/harness/AGENTS.md`; the `CTX7_TELEMETRY_DISABLED` opt-out is exported by the shell role.
