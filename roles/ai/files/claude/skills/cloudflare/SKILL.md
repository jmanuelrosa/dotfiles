---
name: cloudflare
description: >-
  Manage Cloudflare from the command line without an MCP server. Routes to the right binary for the
  surface being touched: flarectl for zones, DNS and firewall, wrangler for the Workers platform
  (Workers, Pages, R2, KV, D1), cloudflared for tunnels, cf-terraforming to export existing config
  into OpenTofu, and the v4 REST API for anything the CLIs do not cover or when output has to be
  machine-readable. Use when adding or editing DNS records, deploying or tailing a Worker, exposing a
  local service through a tunnel, or auditing what a Cloudflare account currently holds.
effort: medium
# Reads only. Every mutating command is deliberately absent so it still hits the
# permission prompt, which is the same confirmation the "Before any write" section
# below asks for. curl is absent for the same reason: the API's write verbs travel
# on the same command as its reads, so no pattern here can tell them apart.
allowed-tools:
  - Bash(flarectl zone list*)
  - Bash(flarectl zone info*)
  - Bash(flarectl dns list*)
  - Bash(flarectl firewall rules list*)
  - Bash(flarectl user info*)
  - Bash(flarectl ips*)
  - Bash(wrangler whoami*)
  - Bash(wrangler deployments list*)
  - Bash(wrangler kv namespace list*)
  - Bash(wrangler r2 bucket list*)
  - Bash(wrangler d1 list*)
  - Bash(wrangler secret list*)
  - Bash(cloudflared tunnel list*)
  - Bash(jq *)
  - Read
---

# Cloudflare from the CLI

No single Cloudflare binary covers the account, so the first decision is always which one owns the surface you are touching. Getting this wrong wastes a turn: `wrangler` has no DNS commands and `flarectl` has no Workers commands, and neither says so helpfully.

| Surface | Tool |
|---|---|
| Zones, DNS records, firewall, page rules, cache purge, LB | `flarectl` |
| Workers, Pages, R2, KV, D1, Queues, secrets, live logs | `wrangler` |
| Tunnels, exposing a local service, DNS-over-HTTPS proxy | `cloudflared` |
| Exporting live config into OpenTofu / Terraform | `cf-terraforming`, then `tofu` |
| Everything else, and any time you need JSON | v4 REST API via `curl` |

The formula is `cloudflare-wrangler` but the binary it installs is `wrangler`. All five are installed by the `apps` role.

## Auth

The dotfiles `shell` role exports the credentials from vault into every fish session, so nothing here needs a login step:

- `CLOUDFLARE_API_TOKEN` is read by `wrangler`, `cf-terraforming` and the OpenTofu Cloudflare provider.
- `CF_API_TOKEN` is the same token under the name `flarectl` reads. `flarectl` supports no config file at all, so the environment is the only channel.
- `CLOUDFLARE_ACCOUNT_ID` is what `wrangler` needs once a token can see more than one account.

Verify the token and see exactly what it is allowed to do before assuming a failure is your command's fault:

```bash
curl -s -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  https://api.cloudflare.com/client/v4/user/tokens/verify | jq
```

A `403` with `Authentication error` on one subcommand while others work is almost always a missing token scope, not a bad token. Say so rather than retrying the same call.

**Never suggest the Global API Key.** It authenticates the entire account including billing and cannot be scoped or narrowed. If a task genuinely needs permission the current token lacks, ask the user to mint a scoped token for it; do not route around the token.

`cloudflared` is the exception: it holds its own certificate at `~/.cloudflared/cert.pem`, written by `cloudflared tunnel login` in a browser. That is a one-time step the user runs themselves.

## Before any write

Cloudflare writes hit live DNS, so the blast radius of a mistake is "the domain is down" and the feedback loop is a TTL. None of these CLIs has a dry-run or an undo.

1. **List before you write.** Record IDs are opaque, are not stable across a delete and recreate, and are the only handle `dns update` and `dns delete` accept. Never carry an ID over from an earlier session.
2. **Show the user the exact command and get confirmation** for anything that deletes, changes an existing record's content, purges cache, or edits firewall rules. Creating a new record on a name that does not exist yet is the one low-risk write.
3. **Never guess a zone or a record name.** Resolve the zone with `flarectl zone list` and ask if more than one plausibly matches.
4. **State the proxy mode you are setting.** `--proxy` (orange cloud) versus DNS-only (grey cloud) decides whether traffic passes through Cloudflare, which changes the visible IP and the TLS terminator. Flipping it on an existing record is a user-visible change even though the record content is untouched.

## flarectl: zones, DNS, firewall

```bash
flarectl zone list
flarectl zone info --zone example.com
flarectl dns list --zone example.com
```

```bash
# create (low risk on a fresh name)
flarectl dns create --zone example.com --name www --type A --content 203.0.113.10 --proxy
flarectl dns create --zone example.com --name @ --type MX --content mail.example.com --priority 10

# update and delete address the record by --id, taken from `dns list` in this session
flarectl dns update --zone example.com --id <record-id> --content 203.0.113.11
flarectl dns delete --zone example.com --id <record-id>
```

```bash
flarectl firewall rules list --zone example.com
flarectl zone purge --zone example.com --everything   # account-visible, confirm first
flarectl user info
flarectl ips                                          # Cloudflare's own edge ranges
```

`flarectl` prints human-readable tables and has no global JSON flag, so do not try to pipe it into `jq`. When a task needs structured output, or needs a resource `flarectl` never exposed, go to the REST API instead of parsing the table. `flarectl` tracks the API loosely and is the least complete of these tools.

## wrangler: the Workers platform

```bash
wrangler whoami
wrangler dev                        # local dev server
wrangler deploy                     # deploy from wrangler.toml in cwd
wrangler tail <worker-name>         # live request logs
wrangler deployments list
wrangler rollback                   # previous deployment, confirm first
```

```bash
wrangler kv namespace list
wrangler r2 bucket list
wrangler d1 list
wrangler d1 execute <db> --command "select 1"        # add --remote to hit production
wrangler secret list --name <worker>
wrangler pages deploy ./dist --project-name <project>
```

Two traps worth naming. `wrangler d1 execute` runs against the **local** simulated database unless you pass `--remote`, so a query that "returns nothing" is usually pointed at the wrong place. And `wrangler deploy` reads `wrangler.toml` from the current directory, so it is only meaningful inside a Workers project; run it anywhere else and it fails on a missing config rather than doing nothing.

## cloudflared: tunnels

This is the tool people reach for expecting general Cloudflare management. It does tunnels and nothing else.

```bash
cloudflared tunnel list
cloudflared tunnel create <name>
cloudflared tunnel route dns <name> app.example.com   # writes a CNAME into the zone
cloudflared tunnel run <name>
cloudflared tunnel delete <name>                      # confirm first
```

`tunnel route dns` is a DNS write dressed up as a tunnel command, so it falls under the confirmation rule above.

## cf-terraforming: live config into code

Use this when the user wants Cloudflare managed declaratively rather than by imperative CLI calls, or wants a reviewable diff before a change lands.

```bash
# cf-terraforming takes a zone ID, not a zone name; flarectl prints tables, so get it from the API
ZONE_ID=$(curl -s -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  "https://api.cloudflare.com/client/v4/zones?name=example.com" | jq -r '.result[0].id')

cf-terraforming generate --resource-type cloudflare_record --zone "$ZONE_ID"
cf-terraforming import   --resource-type cloudflare_record --zone "$ZONE_ID"
```

`generate` writes the HCL for what exists; `import` writes the state-import commands that bind that HCL to the real resources. You need both, in that order, or the first `tofu plan` proposes creating everything you already have. Run `tofu plan` and show it to the user; never `tofu apply` on their behalf.

## REST API: the complete surface

Everything is here, including the resources the CLIs skip. This is the right tool for reads that feed into other work.

```bash
cf() { curl -s -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
         -H "Content-Type: application/json" "https://api.cloudflare.com/client/v4/$1"; }

cf zones | jq -r '.result[] | "\(.name)\t\(.id)"'
cf "zones/$ZONE_ID/dns_records?per_page=100" | jq -r '.result[] | "\(.type)\t\(.name)\t\(.content)\t\(.id)"'
cf "zones/$ZONE_ID/settings/ssl" | jq '.result.value'
```

Responses always carry `success`, `errors` and `result`. Check `success` rather than the HTTP status: the API returns `200` with `"success": false` for several classes of validation failure, so a naive `curl -f` reports a write as having worked when it did not.

List endpoints paginate at 20 by default. A read that silently stops at 20 records and gets reported as the full picture is the most common way an audit here goes wrong, so pass `per_page` and check `result_info.total_count`.

## Reference

- [flarectl README](https://github.com/cloudflare/cloudflare-go/blob/master/cmd/flarectl/README.md)
- [wrangler commands](https://developers.cloudflare.com/workers/wrangler/commands/)
- [cloudflared tunnels](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
- [cf-terraforming](https://github.com/cloudflare/cf-terraforming)
- [API v4](https://developers.cloudflare.com/api/)
