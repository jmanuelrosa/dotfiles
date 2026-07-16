---
name: research
description: Investigate a question and write a cited decision memo - feasibility ("can we do X", "how would we achieve this"), unfamiliar code areas ("understand how X works"), or general/external investigation. Use when asked to "research", "investigate", "is this feasible", "how would we build X", or to turn a Jira ticket, Notion doc, or pasted Slack thread into a written analysis. Fans out parallel agents per phase - source gathering via acli/ntn/gh/glab/ctx7, code exploration across one or more repos, adversarial claim verification - so raw material stays in subagent contexts, and writes .claude/state/research/YYYY-MM-DD-research-<topic>.md.
argument-hint: "[question, Jira key, URL, or pasted thread/doc]"
disable-model-invocation: true
model: opus
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - AskUserQuestion
  - Agent
  - WebSearch
  - WebFetch
  - Bash(date *)
  - Bash(ls *)
  - Bash(mkdir -p *)
  - Bash(git status *)
  - Bash(git branch *)
  - Bash(git remote *)
  - Bash(git log *)
  - Bash(acli jira *)
  - Bash(gh *)
  - Bash(glab *)
  - Bash(ntn *)
  - Bash(bunx ctx7 *)
---

# Research: investigation to decision memo

Answer a real question with evidence, not vibes: pull the context from the tools where it lives, read the actual code, try to break your own conclusion, then write a memo someone can decide from.

Three modes share one workflow; the memo template marks what each mode emphasizes.

| Mode | Trigger shape | Memo emphasis |
|---|---|---|
| **Feasibility** | "can we do X", "how would we achieve X" | Verdict + options + risks + effort |
| **Code deep-dive** | "understand how X works", unfamiliar area | Current-state map, key flows, gotchas |
| **General investigation** | "research X", external tech/vendor/standard | Findings + comparison + recommendation |

Open `references/memo-template.md` when writing the memo, and `references/sources.md` for the exact CLI recipes per source (Jira, Notion, GitHub, GitLab, docs, Slack fallback, `/deep-research` escalation).

**Context discipline.** The main conversation holds the synthesis, never the raw material. Anything that reads at volume - a source dump, a code sweep, a claim re-check - runs inside a subagent whose brief demands a distilled return (findings + citations, a few hundred words), and agents within a phase are spawned in one message so they run in parallel. Never paste raw tool output or file contents into the main context when an agent can digest them.

## 1. Intake

1. Restate the core question in one sentence and name what a good answer must settle (success criteria). If the ask is genuinely ambiguous, ask now (AskUserQuestion); otherwise don't interrupt.
2. Classify the mode from the table above and decompose the question into 2-5 sub-questions. Each sub-question must be answerable by evidence (a file, a doc, a source), not opinion.
3. Detect the code scope: `git remote -v` at CWD means single repo; no repo at CWD but child dirs with `.git` means multi-repo (list them, confirm which are in scope if more than ~4).

## 2. Prior work

Read `.claude/state/research/INDEX.md` if it exists. If a prior memo overlaps the question, say so and offer to extend/update it instead of starting over. An extended memo keeps its filename; note the revision date in its header.

## 3. Gather context (parallel)

Pull every source the request names, using the recipes in `references/sources.md`:

| Source | How |
|---|---|
| Jira ticket | `acli jira workitem view <KEY>` |
| Notion doc | `ntn pages get <id>` (Markdown out) |
| GitHub / GitLab PRs, issues | `gh` / `glab` (multi-host recipe in sources.md) |
| Library / SDK / API docs | `bunx ctx7` - never answer library questions from memory |
| External standards, vendors, competitors | WebSearch / WebFetch; escalate deep external questions to `/deep-research` |
| Slack thread | No CLI exists: ask the user to paste the thread text |

With one small source (a single ticket), fetch it inline. With two or more sources, fan out one general-purpose agent per source in a single message, each briefed with: the core question, the exact recipe from sources.md, and the return contract - the facts relevant to the question plus source ids/URLs, not the raw document. Ask for the Slack paste (a main-context user interaction) **before** spawning the wave, so the wave doesn't idle behind it.

Keep a running source list (key, URL, or "pasted by user") - it becomes the memo's Sources section verbatim.

## 4. Explore the code (read-only, parallel)

Fan out `Explore` agents in a single message so they run in parallel: one per sub-question, or one per repo when the scope spans several. Each dispatch prompt carries: the sub-question, the repo path(s), the relevant distilled context from step 3 (so the agent doesn't re-fetch sources), and two hard rules - cite `path:line` for every claim, and report **current behavior as read**, never intended or documented behavior. When the sub-questions were already clear at intake and no gathered source would change them, launch this wave together with step 3's in the same message.

## 5. Analyze

Synthesize findings per sub-question under these rigor rules:

- Every claim cites `path:line` or a URL. A claim with neither is an assumption and must be labeled as one.
- Every finding carries a confidence level: **high** (read the code / multiple independent sources), **medium** (single decent source), **low** (inference or thin sourcing).
- Contradictions between sources (ticket says X, code does Y) are surfaced in their own section, never smoothed over.

## 6. Adversarial verify (parallel)

Before writing the final memo, identify the 3-5 load-bearing claims behind the draft verdict and spawn one general-purpose refuter per claim, all in a single message. Each refuter gets one claim, its citations, and the brief to **refute** it: re-read the cited code and check it says what the claim says, and hunt for counter-evidence the first pass missed - returning a verdict (holds / partially holds / refuted) with evidence, not a rewrite. Independent refuters can't anchor on each other's reasoning, which is the point. Incorporate what they find - downgrade confidence where one lands a hit, rebut with evidence where it doesn't. Record the exchange in the memo's Verification notes.

## 7. Write the memo

1. `mkdir -p .claude/state/research` at the scope root (the repo, or the parent dir for multi-repo research).
2. Compute the filename: `$(date +%F)-research-<topic-slug>.md` (slug: lowercase, hyphens, 3-6 words).
3. Fill `references/memo-template.md` and write the file.
4. Append one line to `.claude/state/research/INDEX.md` (create it with a `# Research index` heading if missing): `- YYYY-MM-DD [<topic>](<filename>) - <one-line verdict>`.
5. Print the memo path. If `.claude/state/` is not gitignored in this repo, mention once that the user may want it ignored or committed - their call, never touch `.gitignore`.

## 8. Offer delivery

Ask (AskUserQuestion) where the memo should go: keep local only, publish to Notion (`ntn pages create`), or comment on the source Jira ticket (`acli` - follow the `/jira` skill's ADF and humanization rules). Never publish anywhere without the explicit answer.

## Boundaries

- ✅ Always: cite `path:line` or URLs; label confidence per finding; separate evidence from assumption; run the adversarial pass before finalizing; spawn each phase's agents in one message and keep raw dumps in their contexts, not the main one.
- ⚠️ Ask first: publishing anywhere (Notion, Jira comment); expanding scope beyond the repos confirmed at intake; any single wave beyond ~6 agents.
- 🚫 Never: modify code, configs, or `.gitignore`; present assumption as evidence; invent citations; skip the verification pass to save time; read Slack any way other than a user paste.
