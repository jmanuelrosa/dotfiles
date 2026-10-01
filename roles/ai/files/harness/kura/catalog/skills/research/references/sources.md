# Source recipes

CLI-first, per the global tool table: never WebFetch or MCP for a domain that has a CLI. If a CLI is missing or auth-broken, say so and continue with the other sources; never silently fall back.

## Jira (acli)

Read-only pulls for research:

```bash
acli jira workitem view <KEY>            # human-readable
acli jira workitem view <KEY> --json     # structured, includes description + comments
acli jira workitem search --jql "project = <PROJECT> AND text ~ '<topic>'" --json --limit 20
```

Auth: `acli jira auth status` works from the sandbox; trust its result. A genuine `unauthorized` means the user runs `acli jira auth login --web` in their own terminal.

For the delivery step (commenting the memo on a ticket), follow the `/jira` skill: it owns the ADF format rules and the humanization requirements. Never post markdown as a description/comment body.

## Notion (ntn)

```bash
ntn pages get <PAGE_ID>                  # page as Markdown - the research input path
ntn pages get <PAGE_ID> --json           # structured, when properties matter
ntn api /search -d '{"query":"<topic>"}' # find pages by title when you only have a name
```

Page ids come from the URL (the 32-char hex tail, hyphens optional). For delivery: `ntn pages create` takes Markdown content; run `ntn pages create --help` for the parent-page flags before using it.

## GitHub (gh)

```bash
gh pr list --search "<topic>" --state all --limit 20 --json number,title,url,state
gh pr view <num> --json title,body,files,comments
gh issue list --search "<topic>" --state all --limit 20
gh search code "<term>" --owner <org> --limit 20     # find the code area across org repos
```

## GitLab (glab)

Inside a repo, `glab` auto-selects the host: `glab mr list --search "<topic>"`, `glab mr view <num>`.

Repo-agnostic queries must iterate every authenticated host (hosts share `gitlab.com` but carry different tokens):

```bash
HOSTS=$(glab auth status 2>&1 | grep -E '^[^[:space:]]')
printf '%s\n' "$HOSTS" | while IFS= read -r H; do
  [ -z "$H" ] && continue
  glab api --hostname "$H" "search?scope=merge_requests&search=<topic>&per_page=20"
done
```

Dedupe results by `web_url`. If one host errors (expired token), record a line for it and continue with the others.

## Library / SDK / API / CLI / cloud service docs (ctx7)

Training data is stale; fetch current docs before any claim about how a library, framework, SDK, API, CLI tool or cloud service behaves:

```bash
bunx ctx7 library <name> "<question>"
bunx ctx7 docs <id> "<question>"
```

Pick the id by benchmark score among high-reputation results. A `/websites/...` vendor docs site normally beats a bare repo of the same name, which often carries a fraction of the snippets.

## Web (standards, vendors, competitors)

Use the current harness's available web-search and page-reading tools for external facts, factual vendor comparisons, and standards research.
Prefer official sources and keep each search tied to an evidence sub-question.
If required source access is unavailable, report the gap and request the source text rather than answering from memory.

## Slack

When a read-only Slack MCP is available, read the referenced thread, including the parent and replies, and follow pagination until complete.
Cite the thread permalink and distinguish the author's claims from independently verified facts.
If Slack access is unavailable or authentication fails, report it and ask for a paste instead of claiming the thread was read.
For a paste, sender + message per line is enough; record the source as "Slack thread pasted by user (YYYY-MM-DD)".
Do not send Slack messages or publish the memo to Slack.
