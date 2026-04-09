---
description: Fill the PR template based on the current branch changes and show it as markdown
---

# Generate PR Description

Read the PR template and the current branch changes, then output the filled template as markdown for copy-paste.

## Steps

1. Read the PR template from `.github/pull_request_template.md`

2. Analyze the current branch by running these commands:
   - `git diff master...HEAD` to see all changes
   - `git log master..HEAD --oneline` to see the commit history
   - `git branch --show-current` to get the branch name

3. Fill in every section of the PR template based on the diff and commits:
   - For **free-text sections** (descriptions, related issues, etc.): write clear, concise content based on what the changes do and why. Focus on the "why" not just the "what". Extract Jira ticket IDs from the branch name (pattern: `[A-Z]+-[0-9]+`) and format as links when relevant.
   - For **checkbox sections**: analyze the diff to determine which boxes should be checked. Check a box (`[x]`) only when there is clear evidence in the diff that supports it. Leave unchecked (`[ ]`) when the item cannot be verified from the code alone (e.g. "tested locally").
   - For **type/category selections**: infer from commit prefixes (`feat:`, `fix:`, `chore:`, `ci:`, `refactor:`, etc.) and check all that apply.

4. Output the filled template inside a markdown code block (```markdown ... ```) so the user can copy & paste the raw markdown
  directly.

## Rules

- Use CLI tools (`gh`) for read operations only — never create or modify PRs
- Use HEREDOC for correct formatting when needed
