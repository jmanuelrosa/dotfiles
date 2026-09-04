---
name: cloudflare
description: >-
  Manage Cloudflare from the command line without an MCP server, using the two installed binaries:
  `cf` for the account API surface (zones, DNS, firewall, rulesets, KV, R2, D1, Queues, Pages,
  Workers metadata, Zero Trust) and `wrangler` for the Workers project loop (dev, deploy, tail,
  secrets). Use when adding or editing DNS records, deploying or tailing a Worker, inspecting a
  binding's stored data, or auditing what a Cloudflare account currently holds.
effort: medium
# Reads only. Every mutating command is deliberately absent so it still hits the
# permission prompt, which is the same confirmation the "Before any write" section
# below asks for.
allowed-tools:
  - Bash(cf auth list*)
  - Bash(cf user tokens verify*)
  - Bash(cf zones list*)
  - Bash(cf zones get*)
  - Bash(cf dns records list*)
  - Bash(cf dns records get*)
  - Bash(cf firewall access-rules list*)
  - Bash(cf rulesets list*)
  - Bash(cf kv namespaces list*)
  - Bash(cf r2 buckets list*)
  - Bash(cf d1 list*)
  - Bash(cf queues list*)
  - Bash(cf pages projects list*)
  - Bash(cf workers scripts list*)
  - Bash(cf zero-trust tunnels list*)
  - Bash(cf schema*)
  - Bash(cf agent-context*)
  - Bash(wrangler whoami*)
  - Bash(wrangler deployments list*)
  - Bash(wrangler secret list*)
  - Bash(jq *)
  - Read
---

# Cloudflare from the CLI

Two binaries, and the split is about *where the state lives* rather than which product it belongs to.

| You are touching | Tool |
|---|---|
| Anything that is a row in the Cloudflare account: zones, DNS, firewall, rulesets, KV namespaces, R2 buckets, D1 databases, Queues, Pages projects, Zero Trust, tokens | `cf` |
| Anything that reads the project on disk: local dev server, deploying the Worker in cwd, live logs, a Worker's secrets and bindings | `wrangler` |

The overlap is real and not a problem: `cf d1 list` and `wrangler d1 list` both work. Reach for `cf` when you want the account's answer as JSON, and `wrangler` when the command only makes sense inside a Workers project. The formula is `cloudflare-wrangler` but the binary is `wrangler`; `cf` is a bun global install (`bun add -g cf`). Both are wired up by the `apps` role.

`cf` is a Cloudflare-published technical preview that is being built to *become* wrangler, so expect its commands to move. Check `cf --help` before trusting a command shape from memory, including the ones below.

## Auth

The `shell` role exports the credentials from vault into every fish session, so there is no login step for either tool:

- `CLOUDFLARE_API_TOKEN` is read by both. `cf` resolves it *before* its own OAuth profiles, so `cf auth login` and named profiles never come into play here.
- `CLOUDFLARE_ACCOUNT_ID` is what both need once a token can see more than one account.

Check what the token is actually allowed to do before assuming a failure is your command's fault:

```bash
cf user tokens verify
```

A `403` on one subcommand while others work is almost always a missing token scope, not a bad token. Say so rather than retrying the same call.

**Never suggest the Global API Key.** It authenticates the entire account including billing and cannot be scoped. If a task genuinely needs permission the current token lacks, ask the user to mint a scoped token for it; do not route around the token.

## Before any write

Cloudflare writes hit live DNS, so the blast radius of a mistake is "the domain is down" and the feedback loop is a TTL. `cf` gives you two safety rails the older CLIs never had, so use both:

1. **`--dry-run` first.** It validates the call and shows what would happen without executing. Run it on every mutating command and show the user the output.
2. **Never pass `-f` / `--force`.** Destructive `cf` commands prompt for confirmation on their own, and `--force` exists to skip that in CI. Letting the prompt reach the user is the point.
3. **List before you write.** Record IDs are opaque, are not stable across a delete and recreate, and are the only handle `dns records edit` and `dns records delete` accept. Never carry an ID over from an earlier session.
4. **Never guess a zone.** `-z` takes a zone ID *or* a domain name, so there is no reason to resolve one by hand, but if more than one zone plausibly matches what the user said, ask.
5. **State the proxy mode you are setting.** Proxied (orange cloud) versus DNS-only (grey cloud) decides whether traffic passes through Cloudflare, which changes the visible IP and the TLS terminator. Flipping it on an existing record is a user-visible change even though the record content is untouched.

## cf: the account

Every command takes `-z <zone-id-or-domain>` where a zone is relevant, and **all output is JSON on stdout** with status messages on stderr, so piping into `jq` always works.

```bash
cf zones list | jq -r '.[] | "\(.name)\t\(.id)"'
cf zones get -z example.com
cf dns records list -z example.com | jq -r '.[] | "\(.type)\t\(.name)\t\(.content)\t\(.id)"'
cf dns records list -z example.com --name-contains api
```

```bash
# writes: dry-run first, then the same command without it, and let cf prompt
cf dns records create -z example.com --dry-run --type A --name www --content 203.0.113.10
cf dns records edit -z example.com <dns-record-id> --content 203.0.113.11
cf dns records delete -z example.com <dns-record-id>
```

```bash
cf firewall access-rules list -z example.com
cf rulesets list -z example.com
cf kv namespaces list
cf r2 buckets list
cf d1 list
cf queues list
cf pages projects list
cf workers scripts list
cf zero-trust tunnels list
```

List endpoints paginate. A read that silently stops at the first page and gets reported as the full picture is the most common way an audit here goes wrong, so pass `--per-page` and keep going while a page comes back full.

Two commands worth knowing when a command shape is unclear: `cf schema <command>` prints the API schema behind it, and `cf agent-context [product]` prints Cloudflare's own context for a product. Prefer either over guessing flags.

## wrangler: the Workers project

```bash
wrangler whoami
wrangler dev                        # local dev server; press `e` for the Local Explorer
wrangler deploy                     # deploys the project in cwd
wrangler tail <worker-name>         # live request logs
wrangler deployments list
wrangler rollback                   # previous deployment, confirm first
wrangler secret list --name <worker>
wrangler pages deploy ./dist --project-name <project>
wrangler d1 execute <db> --command "select 1"        # add --remote to hit production
```

Two traps worth naming. `wrangler d1 execute` runs against the **local** simulated database unless you pass `--remote`, so a query that "returns nothing" is usually pointed at the wrong place. And `wrangler deploy` reads `wrangler.jsonc` (or `wrangler.toml`) from the current directory, so it is only meaningful inside a Workers project; run it anywhere else and it fails on missing config rather than doing nothing.

The Local Explorer in `wrangler dev` is the fastest way to see what a binding actually holds locally, so reach for it before writing a script to introspect `.wrangler/state`.

## Not installed

Deliberately absent, so do not reach for them or suggest they should already be there:

- **`cloudflared`**, the tunnel daemon. `cf zero-trust tunnels list` manages tunnel *records*, but actually carrying traffic needs the daemon. If the user wants a tunnel running, that is `brew install cloudflared` plus a one-time `cloudflared tunnel login`, and it is their call to make.
- **`cf-terraforming`** and OpenTofu, for exporting live config into IaC. Say so if a task wants Cloudflare managed declaratively; do not improvise an export.

## Reference

- [cf on npm](https://www.npmjs.com/package/cf) and the [announcement](https://blog.cloudflare.com/cf-cli-local-explorer/)
- [wrangler commands](https://developers.cloudflare.com/workers/wrangler/commands/)
- [API v4](https://developers.cloudflare.com/api/)
