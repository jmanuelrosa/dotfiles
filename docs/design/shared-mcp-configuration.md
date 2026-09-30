# Shared MCP configuration - Design Doc

**Status:** Implemented in repository; live client configs not applied
**Author:** José Manuel Rosa Moncayo
**Date:** 2026-09-29
**Scope:** `roles/ai/files/harness/mcp.json` (new), `roles/ai/files/harness/adapters/claude/adapter.toml`, `roles/ai/files/harness/adapters/codex/adapter.toml`, `roles/ai/files/harness/lib/harnessgen/`, `roles/ai/defaults/main.yml`, `roles/ai/tasks/main.yml`, `roles/ai/files/harness/tests/`, `Makefile`, `docs/internals/harnesses.md`, `roles/ai/README.md`

## Summary

Define shared, user-global MCP servers once in the dotfiles harness and make them available to Claude Code, Pi and Codex without replacing configuration those applications own. Pi reads the shared file directly; the harness generator translates and merges only managed server entries into Claude Code and Codex.

## Motivation

The harness already uses one neutral policy with per-harness renderings for permissions, sandbox rules and hooks (`docs/internals/harnesses.md:7-21`). Server connections are a separate problem: the `mcp` section of `policy/permissions.toml:206-212` denies tools from named servers but does not define those servers. Pi's newly installed `pi-mcp-adapter` is declared in `adapters/pi/settings.json:56-63`, yet the role still describes it as uninstalled and removes an older `~/.pi/agent/mcp.json` link (`roles/ai/tasks/main.yml:303-324`).

The three clients do not share a writable configuration format. The installed `pi-mcp-adapter` 2.36.0 reads `~/.config/mcp/mcp.json` as a user-global source (`~/.pi/agent/npm/node_modules/pi-mcp-adapter/config.ts:16-21,458-512`). Claude Code keeps user-scoped MCP servers in the top-level `mcpServers` of `~/.claude.json` ([Claude Code MCP documentation](https://code.claude.com/docs/en/mcp)). Codex keeps them under `mcp_servers` in `~/.codex/config.toml`, a file it and the ChatGPT app modify (`docs/internals/harnesses.md:197-207`). A single file cannot simply be linked into all three locations.

Codex already has an app-managed `node_repl` server that its merge tests deliberately preserve (`roles/ai/files/harness/tests/test_harnessgen_codex.py:12-44,174-190`). Replacing whole server tables would erase such entries. A shared inventory must therefore have explicit ownership and a safe removal path, not just three formats.

## Non-goals

- Unifying each client's OAuth tokens, approval state, tool permissions or sandbox policy. Authentication occurs independently in each client; server definitions do not grant tool permission. The existing Notion MCP denies in Claude and Pi remain in force.
- Importing all existing user, project, plugin or app-managed servers automatically. This design shares only explicitly selected user-global definitions and leaves Codex's `node_repl` alone.
- Automatically sharing project `.mcp.json` files. Project scope and trust differ from the global inventory.
- Providing a new server management UI or allowing a running client's edits to silently change the committed source.
- Supporting every client-specific MCP extension in the first version. A field that cannot be translated faithfully is rejected or explicitly reported, not silently dropped.

## Background

### Existing harness flow

`harnessgen/manifest.py:54-74` loads the neutral policy, while `harnessgen/cli.py:24-65` renders whole files and merges owned Claude settings keys. Codex uses a separate apply command that replaces only adapter-owned config paths (`harnessgen/cli.py:74-100`; `harnessgen/emit_codex.py:40-47`). The role links rendered Claude and Pi files but leaves Codex's config as a selective merge (`roles/ai/defaults/main.yml:88-182`). `make harness`, `make harness-check` and `make harness-apply` expose those operations (`Makefile:33-48`).

The Codex apply task is gated by `HARNESS_ENABLED` (`roles/ai/tasks/main.yml:369-385`), which currently names only Claude and Pi (`roles/ai/defaults/main.yml:72-76`). Codex remains available through the explicit `make harness-apply` path; sharing MCP does not implicitly enable the whole Codex role.

### Pi adapter's configuration precedence

The installed adapter reads the generic global file, then `.agents` global files, then its `~/.pi/agent/mcp.json` global override, followed by project sources (`~/.pi/agent/npm/node_modules/pi-mcp-adapter/config.ts:458-564`). Later definitions of the same name can override earlier fields (`config.ts:326-346,643-711`). Its host-config discovery is off unless enabled (`config.ts:388-397`). Linking the shared file to the generic global path avoids a Pi-specific copy and avoids importing Claude and Codex configs back into Pi. An existing Pi override or project server with the same name is still a collision to inspect, not proof that all clients are using one definition.

### Client formats

Claude Code's user scope is `~/.claude.json`, while a project `.mcp.json` is a different, approval-gated scope ([Claude Code MCP documentation](https://code.claude.com/docs/en/mcp)). Codex uses `[mcp_servers.<name>]` tables with `command`/`args` or `url`; stdio supports environment pass-through and HTTP supports an environment-named bearer token ([Codex MCP configuration](https://github.com/openai/codex/blob/main/codex-rs/cli/src/mcp_cmd.rs)). The adapter accepts the standard `mcpServers` JSON shape (`~/.pi/agent/npm/node_modules/pi-mcp-adapter/types.ts:700-706`).

## Design rules

- **One committed inventory, multiple runtime representations.** `mcp.json` is the only place shared server definitions are edited. The three clients may also retain entries they own independently.
- **Server-level ownership, not whole-table ownership.** The generator may update and remove only server names it previously installed. An unmanaged collision is an error, not permission to adopt that entry. Previously managed entries are overwritten on apply, even if changed manually.
- **No secrets in source or output logs.** Use environment references or each client's separate OAuth flow. Do not change existing app config permissions or MCP permission policy.
- **Translate exactly or stop.** Server identity, transport and credential semantics must match. Reject unsupported fields or formats before touching any target.
- **Idempotent and checkable.** Reapplying unchanged policy writes nothing; check mode and tests name drift without changing files.
- **A deep interface for a bounded problem.** One `mcpServers` entry hides per-client format conversion, selective merge and removal bookkeeping. The implementation is bounded to a portable subset instead of exposing three parallel definitions to authors.

## Design

### 1. Canonical inventory

Add `roles/ai/files/harness/mcp.json` with the standard `mcpServers` object. The initial inventory contains only Notion's official Streamable HTTP endpoint ([Notion MCP guide](https://developers.notion.com/guides/mcp/get-started-with-mcp)):

```json
{
  "mcpServers": {
    "notion": {
      "type": "http",
      "url": "https://mcp.notion.com/mcp"
    }
  }
}
```

Project-scoped and app-managed servers remain outside it. The first version also accepts stdio `command`, `args`, optional `env` and `cwd`, and Streamable HTTP `type: "http"`, `url` with no static headers. HTTP servers can use each client's own OAuth flow. It rejects unknown, Pi-specific or client-specific fields rather than letting one client silently ignore them. Keep MCP deny rules in `policy/permissions.toml` unchanged and independent of this connection file (`harnessgen/emit_claude.py:41,64-70`): `notion` and `Notion` are currently denied, so installing this server does **not** make its tools available in Claude or Pi. Codex reports these MCP denies as untranslatable (`harnessgen/emit_codex.py:118`), so its effective tool permissions may differ.

### 2. Pi consumes the source directly

Link `roles/ai/files/harness/mcp.json` to `~/.config/mcp/mcp.json` through the role's existing link table (`roles/ai/defaults/main.yml:88-165`). Do not restore the `~/.pi/agent/mcp.json` link: that is a higher-precedence Pi override, not the shared path. Change the stale cleanup in `roles/ai/tasks/main.yml:303-324` to remove only known superseded links, preserving a real user-authored Pi override. Before installing the new link, refuse to replace a real file or foreign symlink at `~/.config/mcp/mcp.json`; require explicit migration instead. If any higher-precedence user-global source (`~/.agents/mcp.json`, `~/.agents/mcp/mcp.json`, or `~/.pi/agent/mcp.json`) defines a name from the shared inventory, stop provisioning and name the conflict without altering the override. Do not scan project configs during machine provisioning; project-local overrides remain the project's responsibility. Document that `/mcp edit global` writes the linked source and therefore is not the maintenance route for a committed policy.

### 3. Claude Code receives a selective merge

Extend `harness-build apply` with a Claude target. Read `~/.claude.json` and replace only `mcpServers.<managed-name>` entries, preserving its other keys, local/project data and unmanaged global servers. Do not put servers in `adapters/claude/settings.json`: its existing key-by-key merge is for settings, not Claude's user-scope MCP storage (`harnessgen/cli.py:40-65`). Check mode reports pending names without writing. Apply creates the file when absent, preserves the mode of an existing file, and makes a one-time backup before its first mutation. Run this merge only when no Claude session is open, as with existing rendered Claude settings (`docs/internals/harnesses.md:17-21`).

### 4. Codex receives a selective merge

Translate each managed entry to `mcp_servers.<name>` and extend the existing `apply codex` flow (`harnessgen/cli.py:74-100`). Keep the rest of `mcp_servers`, including `node_repl`, intact. Do not claim ownership of the whole `mcp_servers` table in `emit_codex.owned()`: that would defeat the existing preservation guarantee. Keep Codex as an explicit apply target; do not enable the broader Codex role for this change.

| Shared source | Claude user scope | Pi adapter | Codex |
|---|---|---|---|
| Server name | `mcpServers.<name>` | `mcpServers.<name>` | `mcp_servers.<name>` |
| `command`, `args` | Same stdio entry | Same file | `command`, `args` |
| `env: {"KEY": "${KEY}"}` | Environment reference | Environment reference | `env_vars = ["KEY"]`; do not write the placeholder as a literal env value |
| HTTP `type: "http"`, `url` | HTTP entry | URL entry; adapter ignores the extra type field | Streamable HTTP `url` |
| HTTP OAuth without static header | Client's OAuth login | Adapter's OAuth login | Client's OAuth login |

Only the exact placeholder form is portable for stdio env pass-through in this initial design. Reject composed env values, all configured HTTP headers, SSE-only transports and unsupported connection fields until a correct per-client translation is specified. HTTP bearer-token support is deferred until its user-global credential behavior has been verified in all three clients. Verify the installed client schemas, stdio launch-time env resolution and OAuth behavior during implementation; do not assume identical OAuth credentials or support based on another client's loader.

### 5. Ownership, drift and deletion

Record only managed server names in a local sidecar beside each app config, for example `~/.claude/.harness-mcp-owned.json` and `~/.codex/.harness-mcp-owned.json`. It contains no definitions or credential values. Adding a new name refuses an existing unmanaged name. Updating or removing a previously managed name affects only that entry, even if it was edited outside the harness; edit the shared source instead. If the sidecar is missing, do not infer ownership from matching content.

Plan collisions and format translations before writing either app config or its sidecar. The `--check` path reports pending adds, updates, removals and collisions without modifying files. After an apply, write the names record only after the app config succeeds; if interrupted between writes, the next run stops on the untracked entry rather than adopting it. The first migration of an existing same-named server needs an explicit adoption decision. Preserve `apply codex`'s existing one-time config backup (`harnessgen/cli.py:89-100`); do not introduce changes to existing file modes or permission policy.

### 6. Commands and provisioning

Keep `make harness` for repository renders and `make harness-check` for their drift. Extend `harness-build apply <claude|codex>` and let `make harness-apply TARGET=<claude|codex> CHECK=1` choose a target, defaulting to Codex to preserve its current behavior (`Makefile:33-48`). The AI role runs the Claude merge when Claude is enabled and the Codex merge when Codex is enabled, alongside linking the Pi source; Ansible check mode invokes apply with `--check`. Document that a policy edit requires the appropriate apply command for each app-owned target, or a role run, while Pi sees the linked file after restart/reload.

## Runtime behavior matrix

| State | Pi | Claude Code | Codex |
|---|---|---|---|
| Shared server added and applied | Reads linked global JSON | Managed user entry added | Managed table added after explicit apply |
| Shared server removed and applied | No longer in shared global JSON | Previously managed entry removed | Previously managed entry removed |
| Unmanaged name collision | Higher-precedence user-global source: provisioning refuses; project overrides are not scanned | Apply refuses adoption | Apply refuses adoption |
| Client-only server | Stays in its own supported source | Unmanaged entry preserved | App-managed entry preserved |
| Credential absent | Connection fails or prompts as client permits | Client resolves env or prompts for OAuth | Client resolves env or prompts for OAuth |
| Notion tools after installation | Existing MCP deny remains | Existing MCP deny remains | No equivalent MCP deny enforced by the generator |
| No source change | Reads same file | Check reports clean; no rewrite | Check reports clean; no rewrite |

## Alternatives considered

- **Link the same JSON into all three clients.** Claude's user-scope servers live in `~/.claude.json` and Codex expects TOML in a file it also writes. Direct links would be unreadable or overwrite unrelated state.
- **Make Pi import Claude and Codex host configs.** The adapter can import those formats (`~/.pi/agent/npm/node_modules/pi-mcp-adapter/config.ts:78-96,966-1078`), but that gives Pi two mutable inventories and cannot make Claude and Codex agree with each other. Host discovery is off by default for a reason.
- **Generate a Pi-only `~/.pi/agent/mcp.json`.** It duplicates a representation the adapter already reads natively and reintroduces the stale higher-precedence override the role currently removes.
- **Own the entire MCP table in each app config.** Simpler to render, but it would delete Codex's app-managed server and Claude's unrelated user entries.
- **Put actual tokens in the source to avoid per-client login.** Not acceptable in a committed dotfiles repository; OAuth and environment resolution remain client-specific.

## Testing decisions

Test external behavior at the file boundary: canonical definition to each client's effective entry, repeat apply, read-only check, removal, user-global Pi override conflict, and name collisions in app-owned configs. Add fixtures for stdout-safe secret references, unsupported fields, pre-existing foreign files/symlinks, managed entries edited outside the harness (replaced on apply), and app-owned keys surviving a round trip. Assert that adding Notion leaves existing permission policy unchanged. Keep installed-client verification separate from unit tests so `make test` stays offline. Mirror `roles/ai/files/harness/tests/test_harnessgen_codex.py:174-229` for selective merges, preservation and backup; cover whole-file drift as in `test_harnessgen_drift.py:32-54`.

## Open questions

- Verify installed Claude and Codex client behavior for stdio environment placeholders, user-scope writes, and OAuth before finalizing the supported field set. Codex's executable is not currently on this session's PATH, so a live Codex check cannot yet be claimed. Bearer-token HTTP is out of scope for the first version.

## Appendix - affected files

- `roles/ai/files/harness/mcp.json` (new)
- `roles/ai/files/harness/adapters/claude/adapter.toml`
- `roles/ai/files/harness/adapters/codex/adapter.toml`
- `roles/ai/files/harness/lib/harnessgen/cli.py`
- `roles/ai/files/harness/lib/harnessgen/mcp.py` (new, translation and selective ownership merge)
- `roles/ai/files/harness/tests/test_harnessgen_codex.py`
- `roles/ai/files/harness/tests/test_harnessgen_drift.py`
- `roles/ai/files/harness/tests/test_harnessgen_mcp.py` (new)
- `roles/ai/defaults/main.yml`
- `roles/ai/tasks/main.yml`
- `Makefile`
- `docs/internals/harnesses.md`
- `roles/ai/README.md`
- `~/.config/mcp/mcp.json` (new link, installed)
- `~/.claude.json` and `~/.claude/.harness-mcp-owned.json` (selective installed merge and ownership record)
- `~/.codex/config.toml` and `~/.codex/.harness-mcp-owned.json` (selective installed merge and ownership record)
