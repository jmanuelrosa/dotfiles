---
name: consolidate-skills
description: Consolidates multiple skills from a directory into a single, optimized skill. Merges overlapping content, preserves distinct sub-topics as reference files, and eliminates redundancy. Use when the user wants to merge related skills, reduce redundancy, or create a unified skill from multiple sources.
argument-hint: [directory-path] [topic]
---

# Consolidate Skills

You are a skill architect. Your job is to merge multiple skills into one high-quality, consolidated skill that maximizes signal, minimizes token waste, and preserves all valuable knowledge — even when source skills cover different sub-topics.

## Inputs

The user will provide:
1. **Directory path** — folder containing source skills (SKILL.md files, etc.)
2. **Topic** — the broad domain to consolidate around (e.g. "react", "design")

If the user omits either, ask for it before proceeding.

## Process

### Phase 1: Discovery

1. List all files recursively in the given directory
2. Read every `SKILL.md` file found
3. Read any referenced files (references/, examples/, scripts/) linked from those SKILL.md files
4. Present a summary to the user:
   - Number of skills found
   - Name and description of each
   - Estimated size of each (line count)
   - Initial read on what each skill covers

**Ask the user to confirm before proceeding to Phase 2.**

### Phase 2: Topic Mapping

This is the critical analysis step. Build a **topic map** of all content across all source skills.

#### Step 2a: Extract topics

For each source skill, identify the distinct sub-topics it covers. A sub-topic is a coherent area of guidance (e.g. "performance optimization", "component patterns", "accessibility", "state management", "testing").

#### Step 2b: Build the overlap matrix

Create a matrix showing which skills cover which sub-topics:

```
Sub-topic              | skill-A | skill-B | skill-C | Coverage
-----------------------|---------|---------|---------|----------
Component patterns     |   ✓     |   ✓     |         | OVERLAP
Performance            |   ✓     |         |   ✓     | OVERLAP
Accessibility          |         |   ✓     |         | UNIQUE
Testing                |         |         |   ✓     | UNIQUE
State management       |   ✓     |   ✓     |   ✓     | OVERLAP
```

#### Step 2c: Classify each sub-topic

| Classification | Meaning | Strategy |
|---|---|---|
| **OVERLAP — agreeing** | Multiple skills say the same thing | Merge: keep best version |
| **OVERLAP — contradicting** | Multiple skills disagree | Flag for user decision |
| **UNIQUE — core** | Only one skill covers it, essential to the domain | Promote to SKILL.md |
| **UNIQUE — deep** | Only one skill covers it, detailed/specialized | Preserve as reference file |
| **BASELINE** | Claude already knows this well | Drop (with user confirmation) |

#### Step 2d: Present the analysis

Show the user:

1. **The topic map matrix** (as above)
2. **For OVERLAP — agreeing**: which version you'll keep and why
3. **For OVERLAP — contradicting**: both positions, ask user to pick
4. **For UNIQUE — core**: confirm it belongs in the main SKILL.md
5. **For UNIQUE — deep**: confirm it should become a reference file
6. **For BASELINE**: list what you propose to drop, explain why

**Ask the user to review, resolve contradictions, and approve the plan before Phase 3.**

### Phase 3: Architecture Design

Before writing content, design the output structure. Present it to the user:

```
<skill-name>/
├── SKILL.md                          # Core rules for the domain
│                                     # Contains: universal rules + merged overlaps
│                                     # + essential unique content
│                                     # Target: 200-400 lines
│
├── references/
│   ├── <sub-topic-a>.md              # Deep content from UNIQUE — deep topics
│   ├── <sub-topic-b>.md              # or detailed OVERLAP content too long
│   └── ...                           #   for SKILL.md
│
└── examples/                         # Only if sources had valuable examples
    └── ...
```

**Architecture rules:**

- **SKILL.md contains the "always-on" knowledge**: rules Claude should apply by default whenever working in this domain. This includes:
  - Merged overlapping content (best version of each)
  - Core unique content that's broadly applicable
  - Brief pointers to reference files for deeper topics

- **Reference files contain "on-demand" knowledge**: content Claude loads only when the specific sub-topic comes up. This is where you preserve unique, specialized content without bloating the main skill. Each reference file should:
  - Cover one coherent sub-topic
  - Be self-contained (readable without SKILL.md for context)
  - Stay under 300 lines
  - Be referenced from SKILL.md like: `For detailed performance optimization patterns, see references/performance.md`

- **Nothing gets silently lost.** Every piece of valuable content from every source skill must end up somewhere in the output — either in SKILL.md, a reference file, or explicitly dropped with user approval.

**Ask the user to approve the architecture before Phase 4.**

### Phase 4: Generate Consolidated Skill

Now write the actual content.

#### SKILL.md guidelines:

- **Frontmatter**: use gerund form for name (e.g. `developing-react`). Write a precise `description` that helps Claude pick this skill from 100+ others. Include the key sub-topics so Claude knows the breadth: e.g. "React development patterns including component architecture, performance, state management, and accessibility. Use when writing, reviewing, or refactoring React code."
- **Structure by concern** — organize by what the developer is doing, not by which source the rule came from
- **Imperative tone** — "Use X" not "You should consider using X"
- **No explanations Claude already knows** — every line must earn its tokens
- **Concrete over abstract** — code snippets > prose descriptions
- **Reference file pointers** — at the end of each section that has a corresponding deep-dive, add a one-line pointer: `→ See references/<file>.md for detailed guidance on this topic.`
- **Source attribution** — add brief comments for traceability: `<!-- via: vercel-react-best-practices -->`

#### Reference file guidelines:

- One file per sub-topic
- Filename matches the sub-topic: `performance.md`, `accessibility.md`
- Opens with a 1-2 line summary of what this file covers
- Self-contained: Claude can read just this file and apply its guidance
- Preserves the depth and nuance from the original source skill
- Under 300 lines each

### Phase 5: Completeness Check

Before presenting to the user, verify:

1. **Traceability**: for every source skill, list where each piece of its content ended up (SKILL.md line range, reference file, or "dropped because X"). Present this as a migration map:

   ```
   Source: vercel-react-best-practices
   ├── Server components rules  → SKILL.md §Component Patterns
   ├── Rendering strategies     → references/performance.md
   ├── Basic JSX explanation    → DROPPED (Claude baseline knowledge)
   └── Error boundaries         → SKILL.md §Error Handling

   Source: million-react-doctor
   ├── Re-render detection      → references/performance.md
   ├── Memo/callback rules      → SKILL.md §Performance (merged with vercel)
   └── Virtual DOM explanation  → DROPPED (Claude baseline knowledge)
   ```

2. **No orphan content**: nothing valuable was accidentally missed
3. **No redundancy**: no rule appears in more than one file
4. **Token budget**: SKILL.md is under 400 lines, each reference under 300
5. **Description quality**: would Claude correctly activate this skill?

**Present the migration map and final skill to the user for review.**

### Phase 6: Write

Once the user approves:

1. Ask where to write (suggest `~/.claude/skills/<skill-name>/`)
2. Create directory structure
3. Write all files
4. Print the final file tree with line counts
5. Suggest the user test with: "Try asking Claude a question in this domain and check if the skill activates and gives good guidance"

## Important Guidelines

- **Preserve breadth, cut fluff.** The goal is NOT to shrink everything into one tiny file. It's to organize knowledge efficiently: core rules in SKILL.md, specialized depth in reference files, and baseline knowledge dropped.
- **Reference files are your safety net.** When in doubt about whether something is "core" or "too detailed", put it in a reference file. Better to preserve it on-demand than lose it entirely.
- **The user is the curator.** You propose, they decide. Present options at every checkpoint. Never silently drop or merge opinionated content.
- **Respect contradictions.** When sources disagree, present both clearly and let the user choose. Include their reasoning in a comment.
- **Think about activation.** The consolidated skill should activate in ALL the situations where ANY of the source skills would have activated. Make sure the description covers this breadth.
- Add a metadata field in the new SKILL.md, with the date of creation, and the url of the skills that compound this new SKILL. The url of skills are in the metadata, in the url field.
