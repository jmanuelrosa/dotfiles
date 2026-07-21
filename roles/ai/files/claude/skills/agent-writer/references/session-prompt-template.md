# Session prompt template

When to read: the user wants a reusable prompt for a future session instead of the work done now.
Fill every <PLACEHOLDER>; ground each one in the actual seat file and current state first (read the seat, scan `plugins/` and both registries for adjacent skills and shipped sibling pairs) so the prompt states facts, not guesses.

```markdown
Upgrade the <SEAT> subagent to the failure-modes architecture already shipped for backend-staff-engineer, frontend-staff-engineer, and platform-staff-engineer. The shipped pairs are the source of truth for structure; read them first and do not re-derive or reinvent the pattern.

Templates to read before anything else:
- roles/ai/files/claude/plugins/backend/ (agents/backend-staff-engineer.md + skills/backend-failure-modes/, the plugin exemplar)
- roles/ai/files/claude/plugins/platform/ (second exemplar)
- roles/ai/files/claude/agents/<SEAT>.md (the seat under upgrade)
- <THE ADJACENT SIBLING FILES THAT DEFINE THE DEMARCATION RISK>

Seat scope (respect it everywhere, including researcher briefs): <OWNED SURFACES>. EXCLUDED surfaces owned by siblings: <SURFACE (OWNING SEAT)> pairs. The seat's identity invariants must survive the rewrite intact, in the intro, the never tier, the red flags, and the rationalizations: <THE NEVER-TIER INVARIANTS, VERBATIM FROM THE CURRENT FILE>.

Known gaps in the current file (it predates the pattern; currently <N> lines):
- Missing entirely: Ways of thinking, Red flags refuse-to-ship, Pre-handoff self-check, Common rationalizations, "### Missing gates" and "### Self-check" report sections, Step 3 failure-mode checklists, blast-radius clause in loop step 1. Add all of them per the exemplars.
- The "## <QUALITY BAR SECTION>" gets cut and redistributed into the references, red flags, and self-check.
- Frontmatter description converts to `description: >-` (plain scalars silently break on ": " in continuation lines).
- Align family style: "## Step 1: ..." headings, report sections "Decisions and trade-offs" and "Pending ask-first items", "->" not unicode arrows, boundary tiers kept.
- Seat-specific keeps: <REPORT SECTIONS, GATE WORDING, AND MECHANICS THAT SURVIVE, POSSIBLY RENAMED TO FAMILY CASING>; the static gate gains "If anything fails: fix it, or report the failure honestly with its output. Never report done over a red check."

Coherence rules, apply from the start:
- Agent Step 3 trigger table lists the same domains as SKILL.md's router, same order (agent bare names like `api-design`, router links references/<domain>.md), same "typical brief fires..." example in both.
- "(also an ask-first boundary in the agent)" annotations match the boundary's exact breadth; a reference never escalates what its own Check treats as routine.
- An approved ask-first item must never authorize what the never tier forbids; for this seat: <THE EXECUTION-VS-AUTHORSHIP SPLIT>.

Locked decisions, do not re-ask:
- New skill `<SEAT-SHORT>-failure-modes`: thin-router SKILL.md + ~8 references (~40-55 lines each) with the exact section template ("When to read", "Failure modes to rule out" with the two intro sentences, bold name + `Check:` pairs, "Escalation triggers (`needs-decision`)", "What good looks like").
- Package as a skills-dir plugin: `git mv` the agent and skill into `roles/ai/files/claude/plugins/<DISCIPLINE>/agents/` and `.../skills/`, and write `.claude-plugin/plugin.json` (name <DISCIPLINE>, description, version 0.1.0, author, groups ["<DISCIPLINE>", "<PERSONA>"]). No registry rows, no `dependency_only`. <TAG-COINING CLAUSE IF THE PERSONA TAG IS NEW, INCLUDING THE CLAUDE.MD VOCABULARY UPDATE>.
- Agent edits: insert Step 3 "Open the failure-mode checklists" with the trigger table; renumber the loop and add the blast-radius clause to step 1 (<WHAT THE BLAST RADIUS ENUMERATES FOR THIS SEAT>); self-check gains a first item gating on the opened references; the "Skills used" report line mentions failure-mode references read; the rationalizations intro carries the letter-vs-spirit clause. Hard cap ~200-205 lines; pay for additions by consolidating.
- Demarcation with the sibling skills: <THE SHARPEST OVERLAP AND THE VERB THAT SPLITS IT>. <INSTALLED ADJACENT SKILLS THAT STAY AUTHORITATIVE>; <SKILLS NAMED IN STEP 2 THAT ARE NOT REGISTERED: name them as gaps, not coverage>.
- Keep `model: opus` and per-project scope. Commit nothing (I drive /commit). No research doc is committed.

Process:
1. Launch two background research agents in parallel. If one dies mid-response on a connection error, message it to resend its final report instead of relaunching.
    (a) <SEAT-SHORT>-ladder-researcher: staff-level expectations from public ladders (GitLab, Dropbox, staffeng.com, progression.fyi) and current postings at <8-12 DISCIPLINE-RESPECTED COMPANIES>. Deliverable: discipline-specific judgment themes with behavioral translations for a coding agent, plus 2025-2026 shifts (<THE SHIFTS>). Skip generic staff themes.
    (b) <SEAT-SHORT>-pack-researcher: community packs (wshobson/agents, VoltAgent/awesome-claude-code-subagents, anthropics/claude-plugins-official) plus checklist-rich non-Claude sources (<THE RULE CATALOGS AND OFFICIAL DOCS>), mined for concrete checks a strong model still skips under completion pressure (e.g. <10-15 SEED TRAPS>). Have it flag redundancy with the sibling failure-modes skills explicitly (<THE SPECIFIC SIBLING REFERENCES>). Reject tutorials, tool-version-specific API usage, and arbitrary numeric gates; keep published standards with their source named.
2. While research runs, propose the ~8 reference domains with a one-line scope each and ask me to confirm. This is the only question; everything else proceeds autonomously. Starting suggestion to refine: <8 DOMAINS WITH ONE-LINE SCOPES>.
3. Author the skill, edit the agent, package them as a plugin (per the packaging step above). Fold research deltas in when the researchers report; note in the final summary what was adopted and what was deliberately rejected.
4. Run a synchronous fresh-eyes audit subagent over the new pair + registries + one sibling pair (<THE SIBLING WITH THE DEMARCATION RISK>), checking in priority order: contradictions between agent and references (including annotation breadth and never-vs-ask-first coherence), wiring (trigger tables vs actual filenames, registry entries), technical wrongness (<THE SEAT'S FACT-CHECK TRAP CLASS>), family consistency, style. Apply its must-fix and should-fix findings.
5. Verification sweep, all must pass:
    - agent line count <= ~205 and in family with the siblings
    - zero em/en dashes in every touched file (grep -rnP '[\x{2013}\x{2014}]')
    - frontmatter of the agent and SKILL.md uses `description: >-` and parses under strict YAML (awk-extract the frontmatter block, pipe to ruby -ryaml)
    - ANSIBLE_LOCAL_TEMP="$TMPDIR/ansible-tmp" ansible-lint exits 0
    - plugin.json parses and `claude plugin validate roles/ai/files/claude/plugins/<DISCIPLINE>` passes (benign groups warning)
    - `claude-agent list` (via fish) shows `<DISCIPLINE> (plugin) [groups]`
6. Final message: what shipped with paths and line counts, research evidence adopted vs rejected, audit findings and fixes, verification results, git status. Remind me nothing was committed.

Style, non-negotiable: no em or en dashes anywhere; semantic line breaks (one sentence per line, no hard wrap); reference content is checks against a diff, never tutorials; checks stay stack-agnostic because tool-specific guidance belongs to the installed stack skills.
```

For a brand-new seat (no existing file), replace the "Known gaps" block with the seat definition: scope, invariants, and boundaries drafted per `seat-agent-anatomy.md`.
For an advisor seat, splice in the locked swaps from `advisor-adaptation.md` as a "Pattern adaptations" block and drop the ask-first coherence line in favor of the hard-rules rule.
