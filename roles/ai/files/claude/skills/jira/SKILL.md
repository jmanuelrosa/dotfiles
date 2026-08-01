---
name: jira
description: >-
  Interact with Jira via acli. Create, update, view, transition, and comment on issues. Descriptions
  are built with the bundled adf.py, which emits proper ADF (Atlassian Document Format) for the
  squad's agreed template: Context, Gherkin acceptance criteria, a link back to the source, and
  Design, each under a colored status-lozenge header.
effort: medium
disable-model-invocation: true
allowed-tools:
  - Bash(acli jira *)
  - Bash(gh pr view *)
  - Bash(gh pr edit *)
  - Bash(python3 *skills/jira/scripts/adf.py *)
  - Read
  - Edit(//tmp/claude/**)
  - Edit(//private/tmp/claude/**)
---

# Jira via cli

Use Atlassian's official CLI (`acli`) to interact with Jira. Avoid the Atlassian MCP server and `jira-cli` (Go) - both fail against Didomi's SSO + scoped-token org policy. `acli` uses an OAuth device flow that works with SSO.

Install and auth are one-time: `brew install acli` (tap `atlassian/acli`), then `acli jira auth login --web` in your own terminal. `acli jira auth status` prints `✓ Authenticated` plus the site and auth type.

Three values are yours, never guessed:

- `<INSTANCE>`: your Atlassian site, e.g. `acme.atlassian.net`. `acli jira auth status` prints it.
- `<PROJECT>`: your default Jira project key, e.g. `ENG`. `acli` has no config entry for it, so resolve it in this order and stop at the first that answers: a key the user names in the request, `$JIRA_PROJECT` if it is set in the environment, then `acli jira project list`. If none of those yields exactly one candidate, ask; never assume a project key, and never carry one over from an earlier session.
- `<TECH-DEBT-EPIC>`: your tech-debt parent epic key, if you use one. Ask, or find it with a JQL search for epics.

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
  --description-file /tmp/claude/ticket-adf.json
```

### Edit

```bash
acli jira workitem edit --key <PROJECT>-1234 --summary "New title" --yes
acli jira workitem edit --key <PROJECT>-1234 --description-file /tmp/claude/new-adf.json --yes
acli jira workitem edit --key <PROJECT>-1234 --assignee @me --yes
acli jira workitem edit --key <PROJECT>-1234 --labels "tech-debt,refactor" --yes
```

### Transition / comment

```bash
acli jira workitem transition --key <PROJECT>-1234 --status "In Review" --yes
acli jira workitem comment create --key <PROJECT>-1234 --body "Plain text, or ADF via --body-file"
```

`edit`, `transition` and `comment create` address the work item with `--key`, never a bare positional key; only `edit` and `transition` have a confirmation prompt, so `--yes` belongs on those two and nowhere else. `create` is the exception on both counts: it takes `--project` and prompts for nothing. To inspect the field schema for anything not covered here, `acli jira workitem create --generate-json` (or `edit --generate-json`).

## Description: build it with adf.py

Jira Cloud takes ADF (Atlassian Document Format), not markdown. Markdown passed to `--description` or `--description-file` renders raw `**bold**` and backticks to the reader.

Never hand-write the ADF. `scripts/adf.py` takes the template's sections as markdown-ish text and emits the document `--description-file` expects. Global install: `~/.claude/skills/jira/scripts/`; project install: `.claude/skills/jira/scripts/`.

```bash
python3 ~/.claude/skills/jira/scripts/adf.py - --out /tmp/claude/<topic>-adf.json <<'EOF'
## Context
The Stripe webhook handler crashes when the payload exceeds 1MB (logs from 2026-04-29, request id `req_8aF2`).
Today we call `JSON.parse` on the full body, and there is no retry, so a dropped event is silently lost.

## Acceptance criteria
Scenario: oversized payloads are rejected
GIVEN a webhook payload larger than 1MB
WHEN the handler receives it
THEN it responds 413
AND the rejection is recorded with the request id

## Resource / sources
https://example.slack.com/archives/C0123/p456

## Design
[Figma mockup](https://figma.com/file/abc)
EOF
```

`--out` writes the file (creating its directory) and prints its path; without it the ADF goes to stdout. `--investigation` appends the investigation-only sentence to Context.

Every temp file this skill writes goes under `/tmp/claude/`, the same place `/commit` and `/pr` use: bare `/tmp` is not writable from a tool call, and `$TMPDIR` is no good for a path a later Read or Edit has to name literally. `/tmp/claude/` is shared across sessions, so keep `<topic>` specific enough not to collide.

Headings are the four template names, with `AC` and `Sources` accepted as short forms. Inline `**bold**`, `` `code` ``, `*italic*`, `[label](url)`, bare URLs, `-` bullets and `1.` lists all work. Everything else about the shape is the script's job, so it cannot be got wrong: it fixes the section order and lozenge colors, splits any node that would carry `code` beside `strong` or `em` (which acli rejects as `INVALID_INPUT`), wraps list items in paragraphs, keeps a section's blocks as siblings of its heading, and rewrites em dashes, en dashes and curly quotes.

Malformed input exits non-zero with the offending line number and writes nothing, so a bad description never reaches Jira: `2` an off-template, duplicated or empty section, `3` a missing Context or Acceptance criteria, `4` acceptance criteria that are not strict Gherkin. Fix the input and re-run; do not fall back to writing JSON by hand.

## Humanization (required)

Every word that ends up in a Jira summary, description, or comment must read like a teammate wrote it. This is not optional. Output should be specific, plain, and honest: no AI tells.

**Vocabulary to avoid** (and their cousins): *additionally, leverage, robust, seamless, comprehensive, holistic, delve, crucial, pivotal, key, vital, intricate, tapestry, landscape (figurative), testament, underscore, highlight (verb), enduring, vibrant, foster, journey, ecosystem, empower, unlock*. Use plain English.

**Constructions to avoid:**

- Em dashes between clauses. Use commas or periods.
- Negative parallelisms: "not only X but Y", "it's not just X, it's Y".
- Copula avoidance: *serves as / stands as / marks / represents*. Use *is* or *has*.
- Tail "-ing" clauses tacked on for depth ("…highlighting our commitment", "…ensuring scalability").
- Forced rule-of-three lists when there are really one or two things.
- Promotional adjectives (*powerful, seamless, robust, cutting-edge, modern*).
- Bold-header bullets (`**Performance:** …`): write a sentence.
- Emojis anywhere in body copy (the category emoji at the start of a title is the one exception, see below).
- Title Case Headings. Use sentence case.
- Filler ("in order to" → "to"; "it is important to note that" → drop it).
- Stacked hedges ("could potentially possibly").
- Generic positive endings ("a major step forward", "exciting things ahead").
- Curly quotes (`"…"`). Use straight quotes.
- Chatbot artifacts: "I hope this helps", "Let me know if…", "Certainly!".

**Voice:** say what's happening or what was found, not how transformative it is. Reference concrete things: ticket IDs, file paths, error messages, dates, numbers. If something's blocked or uncertain, say so plainly ("can't repro on staging yet") instead of papering over it. Vary sentence length naturally.

### Bad vs good

Bad summary:

> Implement Robust Error Handling Layer to Empower Seamless User Experience

Good summary:

> Webhook handler crashes on payloads over 1MB

Bad description:

> This ticket aims to introduce a comprehensive new error-handling layer, leveraging best-in-class patterns to deliver a seamless and resilient user experience - serving as a key milestone in our journey toward operational excellence.

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

The description is four sections, each headed by a colored ADF status lozenge. `adf.py` owns the order, the title strings and the colors; what you write is the content:

| Section | Lozenge color | Contents |
|---|---|---|
| Context | `blue` | 2-4 sentences in your own words: what is happening, who raised it, why it matters. No large verbatim quotes. |
| Acceptance criteria | `green` | Gherkin scenarios (see the rule below). |
| Resource / sources | `yellow` | A link back to the originating discussion. Always present when a source exists. |
| Design | `red` | Only when the source has design assets (mockups, Figma links, UI screenshots). Omit the whole section otherwise. |

**Acceptance criteria are strict Gherkin, no exceptions.** Each criterion is its own scenario: a `Scenario: <name>` line, then `GIVEN` / `WHEN` / `THEN` on the following lines using those exact capitalized keywords, one scenario per distinct behavior. Add `AND` lines under any of them when a scenario genuinely needs more than one condition, action, or outcome. `adf.py` enforces all of that and refuses bullets, so the judgment left to you is the wording: each `THEN` must be concrete enough that an engineer could verify it without asking "what does done look like?" - never soften it to "it works correctly", and never split one behavior across two scenarios to dodge an `AND`.

If the source does not state an explicit expected outcome (it only describes a symptom, or multiple directions are discussed without a decision), stop and ask the user the specific open questions before drafting acceptance criteria. Do not invent scope.

**Resource / sources vs the PR conventions below:** the link here is the *originating discussion* (Slack thread, Notion doc, incident), not the implementing PR. The "don't reference PR numbers" and "don't paste raw GitHub URLs" conventions still hold for the implementing PR. When a PR-driven ticket has no discussion source, follow those conventions and leave the raw PR URL out of the body unless the user asks for it.

Example of the Acceptance criteria section content:

```text
Scenario: GBP invoice export succeeds
GIVEN a partner account with currency set to GBP
WHEN the user exports the monthly invoice from the partner portal
THEN the export completes
AND the totals are formatted in GBP
```

### Investigation tickets (vs implementation)

When the work is research / decision-making and implementation is deferred, use the same four-section structure with these adjustments:

- Title: category emoji + `Investigate ...` (e.g. `🧠 Investigate geoip-lite usage and shrink Docker image`).
- Pass `--investigation` to `adf.py`, which ends the **Context** section with the sentence that flags it ("This ticket is for investigation only, implementation will be tracked in a separate follow-up once we agree on a direction"). Writing that sentence yourself is fine too; it is not repeated.
- **Acceptance criteria** describe the investigation outcome, not a code change. Scenarios assert that a decision or recommendation is reached and written down, e.g. `Scenario: image-size options are compared` -> `THEN the ticket records each option with its trade-offs and a recommended direction`.
- **Design** is omitted unless the investigation itself involves design assets.

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
- **No dashes (em dashes).** Use a regular hyphen `-` everywhere - global rule across all repos. `adf.py` rewrites them in the description, but the summary and comments do not pass through it, so write those clean.
- **Don't reference PR numbers in the ticket body.** That belongs on the PR side, not in the ticket.
- **Don't paste raw GitHub URLs** unless the user asks for it.
- **Update the linked PR's "Related issues"** to the new <PROJECT>-#### after creating a ticket from a PR.

## Auth check

Before pushing a create, edit, or transition, verify with `acli jira auth status`. It works from here: the Bash sandbox can read `acli`'s OAuth token from the macOS Keychain, so a `✓ Authenticated` result is real - trust it and proceed.

- **Trust the status check.** `acli` auth/view/search/create/edit all work under the sandbox. The *only* thing it can't do here is `acli jira auth login` - the one operation that writes `~/.config/acli`, which is read-only in the sandbox. Never copy the config dir to `$TMPDIR` or override `HOME`/`XDG_CONFIG_HOME` to "fix" auth; that is never the problem, and the workaround itself fails.
- A genuine `unauthorized` here means the session actually lapsed (rarely, a Keychain ACL prompt a spawned process can't answer) - not a false negative to assume away. Recovery: ask the user to run `acli jira auth login --web` once in their own terminal, then re-run `acli jira auth status` yourself to confirm. Don't wait to be told the state changed - re-check it.
- Keep the drafted sections ready while you wait so nothing is lost; `adf.py` needs no auth, so the description can be built before the session is fixed.

## Workflow patterns

### A) Update an existing ticket from PR context

User says: "update <PROJECT>-875 with context from these PRs: <urls>"

1. `acli jira workitem view <PROJECT>-875` - read the existing description.
2. `gh pr view <num> --repo <owner>/<repo> --json title,body,files,state,mergedAt` for each PR.
3. Draft a new description in the standard structure (Context / Acceptance criteria / Resource / sources / Design). Show the user as plain text and ask to push.
4. On confirmation: build the ADF with `adf.py --out /tmp/claude/<topic>-adf.json`, then run:

   ```bash
   acli jira workitem edit --key <PROJECT>-875 --description-file /tmp/claude/<topic>-adf.json --yes
   ```

5. Verify with `acli jira workitem view <PROJECT>-875`.

### B) Create a new ticket from PR(s)

User says: "make a ticket in the same epic from <pr-urls>"

1. Fetch PR(s) with `gh pr view`.
2. Draft title (with the matching category emoji - 🧠 for backend, 💿 for infra, etc.), type (usually `Task`), parent (usually `<TECH-DEBT-EPIC>` for tech debt), and the description sections using the standard structure (Context / Acceptance criteria / Resource / sources / Design). The PR is only the source of context - write the Context as a current, unfixed problem (present-tense symptoms) and the acceptance criteria as the behavior that must hold once fixed, with no PR reference in the body.
3. Show the user, ask to push.
4. On confirmation: build the ADF with `adf.py --out /tmp/claude/<topic>-adf.json` and create:

   ```bash
   acli jira workitem create \
     --project <PROJECT> --type Task --parent <TECH-DEBT-EPIC> \
     --assignee @me \
     --summary "🧠 Title" \
     --description-file /tmp/claude/<topic>-adf.json
   ```

5. Capture the new <PROJECT>-#### from the output.
6. **Update the source PR's "Related issues" line** to the new key:

   ```bash
   gh pr view <num> --repo <owner>/<repo> --json body -q .body > /tmp/claude/pr-body.txt
   # edit /tmp/claude/pr-body.txt to replace the old <PROJECT>-#### with the new one
   gh pr edit <num> --repo <owner>/<repo> --body-file /tmp/claude/pr-body.txt
   ```

7. Return the Jira URL of the form `https://<INSTANCE>/browse/<PROJECT>-####`.

### C) Investigation ticket (no implementation yet)

Same as B, but:

- Title is `<category-emoji> Investigate ...` (e.g. `🧠 Investigate ...` for backend, `💿 Investigate ...` for infra).
- Pass `--investigation` to `adf.py` so Context ends with the sentence flagging a separate implementation follow-up.
- Acceptance criteria describe the investigation outcome (a decision or recommendation is reached and recorded), not a code change.

See the "Investigation tickets (vs implementation)" convention above for the full adjustments.

## Branch / commit / PR naming

Tickets created or referenced here flow into branches, commits, and PRs that follow shared conventions:

- **Branch:** `<type>/<TICKET>-<slug>`. Use `s-task <TICKET>` to scaffold one from a Jira key; pass `--type` to override the inferred branch type when the issue type doesn't fit.
- **Commit subject:** `<type>(<scope>): <subject>` (Conventional Commits; see commit skill, Step 6).
- **PR title:** `<type>(<scope>): <subject> (<TICKET>)` (see pr skill, Step 6).

`s-task` pushes the branch to `origin` on creation (pass `--no-push` to keep it local). That push is what makes the branch appear in the ticket's **Development** panel: the Jira git integration finds it by scanning branch names for the issue key, which `s-task` always includes. There is nothing to call for this. `acli jira workitem link` creates issue-to-issue links (blocks, relates to), not source-code links, and the endpoint that writes development information (`/rest/devinfo/0.10/bulk`) authenticates as a Connect app rather than as a user. If the panel stays empty, the integration app is missing or has not synced yet, not something a command here can fix.

`s-task` is dual-provider: it also branches from a GitHub issue (`s-task 456`, `s-task '#456'`, an issue URL, or `--github` to force it), producing `<type>/gh-456-<slug>`. The branch shape and the commit subject carry over unchanged; the PR title does not. A GitHub issue gets **no** `(<TICKET>)` suffix, and the pr skill links it as `Closes #456` in the body instead. Its branch type is inferred from the issue's GitHub type or labels rather than a Jira issue type, and it is created through `gh issue develop` so the issue gets a real linked branch. Issues tracked on a GitHub board are outside this skill's scope; `acli` never sees them.

The Jira category emoji (🧠, 💻, 💿, …) belongs only in the **Jira summary**, never in branch names, commit subjects, or PR titles.

## Authentication troubleshooting

- **`acli jira auth status` says unauthorized here but your own terminal says authenticated:** rare. Claude runs `acli` *inside* the Bash sandbox, and the sandbox can reach the macOS Keychain, so `acli` normally authenticates fine from here - just run `acli jira auth status` and trust the result instead of assuming it'll fail. The only sandbox limitation is that `~/.config/acli` is read-only, which affects `acli jira auth login` only - not status, query, create, or edit. If status *genuinely* reports unauthorized, the session has lapsed (or a Keychain ACL prompt can't be answered by a spawned process): run `acli jira auth login --web` once in your own terminal, then have me re-run `acli jira auth status` to confirm. See the Auth check section above.
- **Don't suggest API tokens, the MCP server, or `jira-cli` (Go).** Didomi's org enforces scoped tokens + SSO; classic tokens are not creatable, and scoped tokens 401 against basic-auth tools.
- **Verify auth at any time:** `acli jira auth status`.

## Reference

- [acli docs](https://developer.atlassian.com/cloud/acli/guides/introduction/)
- [ADF spec](https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/)
- Never define shell aliases for these commands, here or in the dotfiles repo. `## Core commands` already carries every one of them, and a tool call spells `acli` out in full: an alias is a second copy to keep in sync and is invisible to anyone reading the transcript.
