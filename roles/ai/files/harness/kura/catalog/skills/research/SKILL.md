---
name: research
description: Investigates code and external sources to write a cited, verified memo for feasibility, unfamiliar code, general investigation, or fact-only planning groundwork. Use explicitly for "research", "investigate", "is this feasible", or a Jira ticket, Notion document, or Slack thread needing analysis. Also supplies evidence internally to to-plan without recommending a solution or publishing. Uses source gathering, code exploration, and adversarial verification, with authorized subagents for volume reads.
argument-hint: "[question, Jira key, URL, or pasted thread/doc]"
disable-model-invocation: true
model: openai-codex/gpt-5.6-sol
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

Four modes share one workflow; the memo template marks what each mode emphasizes.

| Mode | Trigger shape | Memo emphasis |
|---|---|---|
| **Feasibility** | "can we do X", "how would we achieve X" | Verdict + options + risks + effort |
| **Code deep-dive** | "understand how X works", unfamiliar area | Current-state map, key flows, gotchas |
| **General investigation** | "research X", external tech/vendor/standard | Findings + comparison + recommendation |
| **Planning groundwork** | Invoked by `to-plan`, or "facts before planning" | Current state + external evidence + constraints + decision questions |

In **planning-groundwork** mode, investigate relevant code and external sources without recommending a solution, ranking proposed approaches, or estimating implementation effort.
Factual capability comparisons are evidence, not a design choice.
Return constraints and unresolved decisions for the caller's interview; keep hypotheses labeled as assumptions.
Retain the cited memo, index, and verification outputs, but skip the delivery step.

Open `references/memo-template.md` when writing the memo, and `references/sources.md` for the exact CLI recipes per source (Jira, Notion, GitHub, GitLab, docs, web sources, and Slack).

**Context discipline.** Keep the main conversation focused on synthesis.
Delegate volume reads - source pulls, code sweeps, and claim re-checks - only when the current request or applicable user/project instructions authorize delegation.
Apply the parallel dispatch instructions below within that authorization and the current harness's subagent controls; this skill alone grants no permission.
Authorized read-only agents return distilled findings and citations, not raw dumps, and independent agents within a phase run in parallel.
Otherwise, perform narrow direct reads and verify the same claims yourself without claiming independent review.

## 1. Intake

1. Restate the core question in one sentence and name what a good answer must settle (success criteria). If the ask is genuinely ambiguous, ask one focused question through the current harness's user-question tool; otherwise don't interrupt.
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
| Library / SDK / API / CLI / cloud service docs | `bunx ctx7` - never answer these from memory |
| External standards, vendors, competitors | Current harness's available web-search and page-reading tools |
| Slack thread | Available read-only Slack MCP; otherwise ask for a paste |

With one small source (a single ticket), fetch it inline. With two or more sources, fan out one general-purpose agent per source in a single message, each briefed with: the core question, the exact recipe from sources.md, and the return contract - the facts relevant to the question plus source ids/URLs, not the raw document. If Slack access is unavailable, ask for the paste in the main conversation before spawning the wave, so the wave doesn't idle behind it.

Keep a running source list (key, URL, or "pasted by user") - it becomes the memo's Sources section verbatim.

## 4. Explore the code (read-only, parallel)

Skip this step when the question has no relevant code scope.
Otherwise, fan out `Explore` agents in a single message so they run in parallel: one per sub-question, or one per repo when the scope spans several. Each dispatch prompt carries: the sub-question, the repo path(s), the relevant distilled context from step 3 (so the agent doesn't re-fetch sources), and two hard rules - cite `path:line` for every claim, and report **current behavior as read**, never intended or documented behavior. When the sub-questions were already clear at intake and no gathered source would change them, launch this wave together with step 3's in the same message.

## 5. Analyze

Synthesize findings per sub-question under these rigor rules:

- Every claim cites `path:line` or a URL. A claim with neither is an assumption and must be labeled as one.
- Every finding carries a confidence level: **high** (read the code / multiple independent sources), **medium** (single decent source), **low** (inference or thin sourcing).
- Contradictions between sources (ticket says X, code does Y) are surfaced in their own section, never smoothed over.

## 6. Adversarial verify (parallel)

Before writing the final memo, identify the 3-5 load-bearing claims behind the findings or draft verdict.
When delegation is authorized, spawn one read-only general-purpose refuter per claim in parallel.
Each refuter gets the claim and citations, re-reads the evidence, and hunts for counter-evidence, returning holds / partially holds / refuted with citations.
Keep refuters independent so they cannot anchor on each other's reasoning.
Without delegation authorization, challenge the same claims directly and label the verification as a self-check.
Incorporate the outcomes, downgrade confidence where evidence weakens a claim, and record corrections in Verification notes.
Planning-groundwork mode verifies facts and constraints, not a proposed solution.

## 7. Write the memo

1. `mkdir -p .claude/state/research` at the scope root (the repo, or the parent dir for multi-repo research).
2. Compute the filename: `$(date +%F)-research-<topic-slug>.md` (slug: lowercase, hyphens, 3-6 words).
3. Fill `references/memo-template.md` and write the file.
4. Append one line to `.claude/state/research/INDEX.md` (create it with a `# Research index` heading if missing): `- YYYY-MM-DD [<topic>](<filename>) - <one-line finding or verdict>`.
5. Print the memo path. If `.claude/state/` is not gitignored in this repo, mention once that the user may want it ignored or committed - their call, never touch `.gitignore`.

## 8. Offer delivery

For planning-groundwork, return the memo path and distilled findings to the caller and stop without a delivery prompt.

For other modes, use the current harness's user-question tool to ask where the memo should go: keep local only, publish to Notion (`ntn pages create`), or comment on the source Jira ticket (`acli` - follow the `/jira` skill's ADF and humanization rules). Never publish anywhere without the explicit answer.

## Boundaries

- ✅ Always: cite `path:line` or URLs; label confidence per finding; separate evidence from assumption; run the adversarial pass before finalizing; use authorized read-only agents for volume reads and keep raw dumps out of the main conversation.
- ⚠️ Ask first: publishing anywhere (Notion, Jira comment); expanding scope beyond the repos confirmed at intake; any single wave beyond ~6 agents.
- 🚫 Never: modify code, configs, or `.gitignore`; present assumption as evidence; invent citations; skip the verification pass to save time; use a memo's recommendation as user approval.
