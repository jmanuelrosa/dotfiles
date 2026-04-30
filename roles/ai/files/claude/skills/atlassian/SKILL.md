---
description: Use when the user mentions Jira tickets, Confluence pages, or any Atlassian work — creating, updating, viewing, transitioning, commenting, searching issues. Triggers on Jira ticket IDs (pattern `[A-Z]+-[0-9]+`), or keywords like ticket, issue, story, bug, sprint, epic, Jira, Confluence, Rovo, Compass. Always use the `acli` (Atlassian CLI) — never the web UI, browser links, or raw REST API.
---

# Atlassian via acli

`acli` is the Atlassian CLI, installed via Homebrew (`atlassian/homebrew-acli`) and authenticated locally with `acli auth login`. It covers Jira, Confluence, Compass, and Rovo.

## Rules

- **Always use `acli`**. Do not suggest the Atlassian web UI, deep links, or REST API calls.
- **Discover, don't guess**: when unsure of a subcommand or flag, run `acli --help`, `acli jira --help`, or `acli jira workitem --help`. The CLI is self-documenting; rely on it instead of memory.
- **Use `--json` for parsable output** and pipe through `jq` when extracting fields.
- **Confirm before write operations**: creating issues, transitioning status, adding comments, editing fields, or anything visible to others must be confirmed with the user before execution. Read operations (view/search/list) run freely.
- **Auth failures**: if a command returns an auth/login error, ask the user to run `acli auth login` — do not try to repair credentials yourself.
- **Sensitive content**: ticket bodies and Confluence pages may contain credentials or PII. Don't echo full bodies into commit messages, PR descriptions, or chat logs unless asked.

## Common patterns

Read (safe to run):

```bash
acli jira workitem view DID-1234 --fields summary,status,assignee --json
acli jira workitem search --jql 'assignee = currentUser() AND status != Done' --json
acli confluence page view --id <id> --json
```

Write (confirm with user first):

```bash
acli jira workitem create --project DID --type Task --summary "..." --description "..."
acli jira workitem transition DID-1234 --transition "In Progress"
acli jira workitem comment DID-1234 --body "Patch deployed."
acli jira workitem edit DID-1234 --assignee <accountId>
```

## Reference

- Existing usage in this repo: [roles/work/files/scripts/s-task](roles/work/files/scripts/s-task) reads a Jira issue with `acli jira workitem view ... --fields summary,issuetype --json` and parses it via `jq`.
- `acli` is on the Claude Code sandbox `excludedCommands` allowlist, so it runs unsandboxed without prompting. See [roles/ai/files/claude/settings.json](roles/ai/files/claude/settings.json).
