---
name: jira
description: Interact with Jira via acli. Create, update, view, transition, and comment on issues. Defaults to the SER project and produces descriptions that both product and engineering can follow, in proper ADF (Atlassian Document Format).
disable-model-invocation: true
---

# Jira via cli

Use Atlassian's official CLI (`acli`) to interact with Jira. Avoid the Atlassian MCP server and `jira-cli` (Go) - both fail against Didomi's SSO + scoped-token org policy. `acli` uses an OAuth device flow that works with SSO.

- `<INSTANCE>` — your Atlassian site, e.g. `acme.atlassian.net`
- `<PROJECT>` — your default Jira project key, e.g. `ENG`
- `<TECH-DEBT-EPIC>` — your tech-debt parent epic key, if you use one

## Prerequisites

### One-time install + auth

```bash
# Install
brew tap atlassian/acli
brew install acli

# Authenticate via SSO (opens browser)
acli jira auth login --web

# Verify
acli jira auth status
# Expected:
#   ✓ Authenticated
#   Site: <INSTANCE>
#   Authentication Type: oauth
```

### Optional shell aliases

Add to `~/.zsh/modules/aliases.zsh` (or equivalent):

```sh
# Jira (acli) - defaults to SER project
alias jql='acli jira workitem search --jql'
alias jmine='acli jira workitem search --jql "project = SER AND assignee = currentUser() AND statusCategory != Done"'
alias jview='acli jira workitem view'
alias jopen='acli jira workitem view --web'
alias jcomment='acli jira workitem comment add'
alias jmove='acli jira workitem transition'
```

## Core commands

### View

```bash
acli jira workitem view <PROJECT>-1234
acli jira workitem view <PROJECT>-1234 --web      # open in browser
acli jira workitem view <PROJECT>-1234 --json     # structured output
```

### Search (JQL)

```bash
acli jira workitem search --jql "project = <PROJECT> AND assignee = currentUser() AND statusCategory != Done"
acli jira workitem search --jql "project = <PROJECT> AND parent = <TECH-DEBT-EPIC>"  # tech debt children
acli jira workitem search --jql "..." --json --limit 50               # scriptable
acli jira workitem search --jql "..." --csv --fields "key,summary,status"
```

### Create

```bash
acli jira workitem create \
  --project <PROJECT> \
  --type Task \
  --parent <TECH-DEBT-EPIC> \
  --assignee @me \
  --summary "🧠 Title here" \
  --description-file /tmp/ticket-adf.json
```

### Edit

```bash
acli jira workitem edit --key <PROJECT>-1234 --summary "New title" --yes
acli jira workitem edit --key <PROJECT>-1234 --description-file /tmp/new-adf.json --yes
acli jira workitem edit --key <PROJECT>-1234 --assignee @me --yes
acli jira workitem edit --key <PROJECT>-1234 --labels "tech-debt,refactor" --yes
```

### Transition / comment

```bash
acli jira workitem transition <PROJECT>-1234 "In Review"
acli jira workitem comment add <PROJECT>-1234 -m "Plain text or ADF via --body-file"
```

## Description format: ADF, not markdown

**Critical:** Jira Cloud uses ADF (Atlassian Document Format), not markdown. If you pass markdown via `--description` or `--description-file`, raw `**bold**` and backticks render literally to the reader.

Always pass ADF JSON via `--description-file`. The file is the bare ADF doc:

```json
{
  "type": "doc",
  "version": 1,
  "content": [ /* nodes */ ]
}
```

### ADF node cheat sheet

| Markdown intent | ADF node |
|---|---|
| Heading (`### Foo`) | `{"type":"heading","attrs":{"level":3},"content":[{"type":"text","text":"Foo"}]}` |
| Paragraph | `{"type":"paragraph","content":[{"type":"text","text":"..."}]}` |
| Bullet list | `{"type":"bulletList","content":[{"type":"listItem","content":[{"type":"paragraph",...}]}]}` |
| Numbered list | `{"type":"orderedList","content":[{"type":"listItem",...}]}` |
| Bold | text node with `"marks":[{"type":"strong"}]` |
| Inline code | text node with `"marks":[{"type":"code"}]` |
| Italic | text node with `"marks":[{"type":"em"}]` |
| Link | text node with `"marks":[{"type":"link","attrs":{"href":"https://..."}}]` |

### ADF gotchas (learned the hard way)

- **Never combine `strong` and `code` marks on the same text node.** acli rejects with `INVALID_INPUT`. Split into two adjacent text nodes instead.
  - ❌ `{"text":".gitignore","marks":[{"type":"strong"},{"type":"code"}]}`
  - ✅ Two nodes: `{"text":"Simplify ","marks":[{"type":"strong"}]}` then `{"text":".gitignore","marks":[{"type":"code"}]}`
- `listItem` content must be wrapped in a `paragraph` node, not raw text.
- Use `acli jira workitem edit --generate-json` to inspect the schema for any field.

## Humanization (required)

Every word that ends up in a Jira summary, description, or comment must read like a teammate wrote it. This is not optional. Output should be specific, plain, and honest — no AI tells.

**Vocabulary to avoid** (and their cousins): *additionally, leverage, robust, seamless, comprehensive, holistic, delve, crucial, pivotal, key, vital, intricate, tapestry, landscape (figurative), testament, underscore, highlight (verb), enduring, vibrant, foster, journey, ecosystem, empower, unlock*. Use plain English.

**Constructions to avoid:**

- Em dashes between clauses. Use commas or periods.
- Negative parallelisms: "not only X but Y", "it's not just X, it's Y".
- Copula avoidance: *serves as / stands as / marks / represents*. Use *is* or *has*.
- Tail "-ing" clauses tacked on for depth ("…highlighting our commitment", "…ensuring scalability").
- Forced rule-of-three lists when there are really one or two things.
- Promotional adjectives (*powerful, seamless, robust, cutting-edge, modern*).
- Bold-header bullets (`**Performance:** …`) — write a sentence.
- Emojis anywhere in body copy (the category emoji at the start of a title is the one exception, see below).
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

## Ticket-writing convention

Tickets need to be understood by both product and engineering. Frame the body as **what has to be done**, not what was done. Keep the tone plain and outcome-focused so product can follow it, while keeping file names, library names, and technical specifics accurate so engineering has enough detail to act on.

### Write from the reporter's perspective

Write the body as the person reporting the problem, before the fix and investigation are done. This holds **even when a fix already exists or has shipped** - a ticket created after the work is a record of the problem, not a changelog.

- Describe symptoms in the present tense, as currently happening ("the handler crashes when the payload exceeds 1MB"), not "was crashing" or "is now fixed".
- Keep any proposed fix in the future / conditional tense ("could switch to a streaming parser", "should reject early with 413"). Never state the fix as done.
- Don't reference the implementing PR or completed work in the description (see the "Don't reference PR numbers" and "Don't paste raw GitHub URLs" conventions below).

### Standard structure

```text
**Goal**
One paragraph: the outcome and the reason in plain language.

**Scope**
Numbered list. Each item leads with a bold action phrase, then a dash and a plain-language explanation. Mention concrete file names / package names in `code` font.

**Why it matters**
Bulleted list of business-flavored benefits (faster shipping, less maintenance, fewer incidents, faster onboarding, lower costs). One line each.

**Out of scope**
What is explicitly NOT covered, with a pointer to where it lives instead (other ticket, separate concern).
```

### Investigation tickets (vs implementation)

When the work is research / decision-making and implementation is deferred:

- Title: category emoji + `Investigate ...` (e.g. `🧠 Investigate geoip-lite usage and shrink Docker image`).
- Add a `**Note**` heading right after `**Goal**`: "This ticket is for investigation only - implementation will be tracked in a separate follow-up ticket once we agree on a direction."
- Section heading: `**Scope (investigation only)**`.
- `**Out of scope**` must explicitly call out implementation as separate.

### Conventions

- **Category emoji prefix on titles.** Pick the emoji that matches the area of work and put it at the start of the summary. The mapping is shared across the Didomi backlog:

  | Emoji | Category |
  |-------|----------|
  | 💻 | Frontend |
  | 🧠 | Backend |
  | 💿 | Infra |
  | 📊 | Analytics |
  | 🚀 | UI Library |
  | 🚪 | Shell |

  Server-side / `aw-gtm-cloud-image` work is **Backend** -> use the brain emoji. Cloud Run / Terraform / GitHub Actions work is **Infra** -> use the disc emoji. When the area is ambiguous, ask the user.

- **Parent epic for tech debt:** `--parent <TECH-DEBT-EPIC>` for any tech debt work in the <PROJECT> project. The category emoji is independent of the parent epic - a backend tech-debt ticket uses the brain emoji prefix together with `--parent <TECH-DEBT-EPIC>`.
- **No dashes (em dashes).** Use a regular hyphen `-` everywhere - global rule across all repos.
- **Don't reference PR numbers in the ticket body.** That belongs on the PR side, not in the ticket.
- **Don't paste raw GitHub URLs** unless the user asks for it.
- **Update the linked PR's "Related issues"** to the new <PROJECT>-#### after creating a ticket from a PR.

## Auth check

Before pushing a create, edit, or transition, verify with `acli jira auth status`. It works from here: the Bash sandbox can read `acli`'s OAuth token from the macOS Keychain, so a `✓ Authenticated` result is real - trust it and proceed.

- **Trust the status check.** `acli` auth/view/search/create/edit all work under the sandbox. The *only* thing it can't do here is `acli jira auth login` - the one operation that writes `~/.config/acli`, which is read-only in the sandbox. Never copy the config dir to `$TMPDIR` or override `HOME`/`XDG_CONFIG_HOME` to "fix" auth; that is never the problem, and the workaround itself fails.
- A genuine `unauthorized` here means the session actually lapsed (rarely, a Keychain ACL prompt a spawned process can't answer) - not a false negative to assume away. Recovery: ask the user to run `acli jira auth login --web` once in their own terminal, then re-run `acli jira auth status` yourself to confirm. Don't wait to be told the state changed - re-check it.
- Keep the drafted ADF ready while you wait so nothing is lost.

## Workflow patterns

### A) Update an existing ticket from PR context

User says: "update <PROJECT>-875 with context from these PRs: <urls>"

1. `acli jira workitem view <PROJECT>-875` - read the existing description.
2. `gh pr view <num> --repo <owner>/<repo> --json title,body,files,state,mergedAt` for each PR.
3. Draft a new description in the standard structure (Goal / Scope / Why it matters / Out of scope). Show the user as plain text and ask to push.
4. On confirmation: build ADF JSON, write to `/tmp/<topic>-adf.json`, then run:

   ```bash
   acli jira workitem edit --key <PROJECT>-875 --description-file /tmp/<topic>-adf.json --yes
   ```

5. Verify with `acli jira workitem view <PROJECT>-875`.

### B) Create a new ticket from PR(s)

User says: "make a ticket in the same epic from <pr-urls>"

1. Fetch PR(s) with `gh pr view`.
2. Draft title (with the matching category emoji - 🧠 for backend, 💿 for infra, etc.), type (usually `Task`), parent (usually `<TECH-DEBT-EPIC>` for tech debt), and ADF description using the standard structure. The PR is only the source of context - write the description as a current, unfixed problem (present-tense symptoms, future-tense fix, no PR reference in the body).
3. Show the user, ask to push.
4. On confirmation: write ADF to `/tmp/<topic>-adf.json` and create:

   ```bash
   acli jira workitem create \
     --project <PROJECT> --type Task --parent <TECH-DEBT-EPIC> \
     --assignee @me \
     --summary "🧠 Title" \
     --description-file /tmp/<topic>-adf.json
   ```

5. Capture the new <PROJECT>-#### from the output.
6. **Update the source PR's "Related issues" line** to the new key:

   ```bash
   gh pr view <num> --repo <owner>/<repo> --json body -q .body > /tmp/pr-body.txt
   # edit /tmp/pr-body.txt to replace the old <PROJECT>-#### with the new one
   gh pr edit <num> --repo <owner>/<repo> --body-file /tmp/pr-body.txt
   ```

7. Return the Jira URL of the form `https://<INSTANCE>/browse/<PROJECT>-####`.

### C) Investigation ticket (no implementation yet)

Same as B, but:

- Title is `<category-emoji> Investigate ...` (e.g. `🧠 Investigate ...` for backend, `💿 Investigate ...` for infra).
- Body includes a `**Note**` heading flagging investigation-only.
- `**Scope**` heading reads `**Scope (investigation only)**`.
- `**Out of scope**` explicitly lists implementation as a separate follow-up.

## Branch / commit / PR naming

Tickets created or referenced here flow into branches, commits, and PRs that follow shared conventions:

- **Branch:** `<type>/<TICKET>-<slug>` (see commit skill, Step 2 regex). Use `s-task <TICKET>` to scaffold one from a Jira key; pass `--type` to override the inferred branch type when the issue type doesn't fit.
- **Commit subject:** `<type>(<scope>): <subject>` (Conventional Commits; see commit skill, Step 6).
- **PR title:** `<type>(<scope>): <subject> (<TICKET>)` (see pr skill, Step 6).

The Jira category emoji (🧠, 💻, 💿, …) belongs only in the **Jira summary** — never in branch names, commit subjects, or PR titles.

## Authentication troubleshooting

- **`acli jira auth status` says unauthorized here but your own terminal says authenticated:** rare. Claude runs `acli` *inside* the Bash sandbox, and the sandbox can reach the macOS Keychain, so `acli` normally authenticates fine from here - just run `acli jira auth status` and trust the result instead of assuming it'll fail. The only sandbox limitation is that `~/.config/acli` is read-only, which affects `acli jira auth login` only - not status, query, create, or edit. If status *genuinely* reports unauthorized, the session has lapsed (or a Keychain ACL prompt can't be answered by a spawned process): run `acli jira auth login --web` once in your own terminal, then have me re-run `acli jira auth status` to confirm. See the Auth check section above.
- **Don't suggest API tokens, the MCP server, or `jira-cli` (Go).** Didomi's org enforces scoped tokens + SSO; classic tokens are not creatable, and scoped tokens 401 against basic-auth tools.
- **Verify auth at any time:** `acli jira auth status`.

## Reference

- [acli docs](https://developer.atlassian.com/cloud/acli/guides/introduction/)
- [ADF spec](https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/)
