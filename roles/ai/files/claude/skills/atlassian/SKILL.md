---
name: atlassian
description: Use when the user mentions Jira tickets, Confluence pages, or any Atlassian work — creating, updating, viewing, transitioning, commenting, searching issues. Triggers on Jira ticket IDs (pattern `[A-Z]+-[0-9]+`), or keywords like ticket, issue, story, bug, sprint, epic, Jira, Confluence, Rovo, Compass. Always use the `acli` (Atlassian CLI) — never the web UI, browser links, or raw REST API.
license: MIT
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

## Humanization (required)

Every word that ends up in a Jira summary, description, comment, or Confluence page must read like a teammate wrote it. This is not optional. Output should be specific, plain, and honest — no AI tells.

**Vocabulary to avoid** (and their cousins): *additionally, leverage, robust, seamless, comprehensive, holistic, delve, crucial, pivotal, key, vital, intricate, tapestry, landscape (figurative), testament, underscore, highlight (verb), enduring, vibrant, foster, journey, ecosystem, empower, unlock*. Use plain English.

**Constructions to avoid:**

- Em dashes between clauses. Use commas or periods.
- Negative parallelisms: "not only X but Y", "it's not just X, it's Y".
- Copula avoidance: *serves as / stands as / marks / represents*. Use *is* or *has*.
- Tail "-ing" clauses tacked on for depth ("…highlighting our commitment", "…ensuring scalability").
- Forced rule-of-three lists when there are really one or two things.
- Promotional adjectives (*powerful, seamless, robust, cutting-edge, modern*).
- Bold-header bullets (`**Performance:** …`) — write a sentence.
- Emojis. Anywhere.
- Title Case Headings. Use sentence case.
- Filler ("in order to" → "to"; "it is important to note that" → drop it).
- Stacked hedges ("could potentially possibly").
- Generic positive endings ("a major step forward", "exciting things ahead").
- Curly quotes (`"…"`). Use straight quotes.
- Chatbot artifacts: "I hope this helps", "Let me know if…", "Certainly!".

**Voice:** say what's happening or what was found, not how transformative it is. Reference concrete things — ticket IDs, file paths, error messages, dates, numbers. If something's blocked or uncertain, say so plainly ("can't repro on staging yet") instead of papering over it. Vary sentence length naturally.

### Bad vs good

Bad summary:

> Implement Robust Error Handling Layer to Empower Seamless User Experience

Good summary:

> Webhook handler crashes on payloads over 1MB

Bad description:

> This ticket aims to introduce a comprehensive new error-handling layer, leveraging best-in-class patterns to deliver a seamless and resilient user experience — serving as a key milestone in our journey toward operational excellence.

Good description:

> The Stripe webhook handler crashes when the payload exceeds 1MB (see logs from 2026-04-29, request id `req_8aF2`). Today we use `JSON.parse` on the full body. Two options: switch to a streaming parser, or reject early with 413. We have no retry today, so dropped events are silently lost.

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
