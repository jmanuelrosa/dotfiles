---
name: weekly-recap
description: Summarize what I worked on in the last 7 days across Jira (acli), GitHub (gh), and GitLab (glab). Output is markdown grouped by project / repo, ready to paste into the weekly team meeting.
---

# Weekly recap

Produce a markdown recap of my last 7 days of activity across Jira, GitHub, and GitLab. The window is today minus 7 days through today, fixed, no questions asked. Output goes straight to stdout grouped by project / repo.

## Steps

1. **Compute the window** (macOS BSD `date`):

   ```sh
   SINCE=$(date -v-7d +%Y-%m-%d)
   TODAY=$(date +%Y-%m-%d)
   ```

2. **Run the three platforms in parallel**. Each block below is independent, fire them all in the same tool turn.

   ### Jira (acli)

   ```sh
   acli jira workitem search \
     --jql "(assignee = currentUser() OR reporter = currentUser()) AND updated >= -7d ORDER BY updated DESC" \
     --json --limit 100
   ```

   Extract per item: `key`, `fields.summary`, `fields.status.name`, `fields.project.key`, `fields.updated`. The Jira project key (e.g. `SER`) is the group label.

   If `acli jira auth status` reports unauthenticated, emit one line `Jira: not authenticated, run \`acli jira auth login --web\`` and move on without failing.

   ### GitHub (gh)

   Three queries, all in parallel:

   ```sh
   # Opened in the window
   gh search prs --author=@me --created=">=$SINCE" \
     --json repository,number,title,state,createdAt,mergedAt,url --limit 100

   # Merged in the window (catches PRs opened earlier but merged this week)
   gh search prs --author=@me --merged --merged-at=">=$SINCE" \
     --json repository,number,title,mergedAt,url --limit 100

   # Reviewed in the window
   gh search prs --reviewed-by=@me --updated=">=$SINCE" \
     --json repository,number,title,author,state,url --limit 100
   ```

   Dedupe by `url`. A single PR can appear in all three buckets; collapse it to one item and pick the strongest label in this order: `merged` > `opened` > `reviewed`. `reviewed` only applies when the author is not me. The group label is `repository.nameWithOwner`.

   ### GitLab (glab)

   ```sh
   ME=$(glab api /user --jq .username)

   # MRs I authored
   glab api "merge_requests?scope=created_by_me&updated_after=${SINCE}T00:00:00Z&per_page=100"

   # MRs I'm a reviewer on
   glab api "merge_requests?reviewer_username=${ME}&updated_after=${SINCE}T00:00:00Z&per_page=100"
   ```

   Dedupe by `web_url`. Classify each MR as `opened`, `merged` (when `state == "merged"` and `merged_at >= $SINCE`), or `reviewed` (author username differs from `$ME`). The group label is the project path from `references.full` with the `!N` suffix stripped, i.e. `group/project`.

   If `glab auth status` reports unauthenticated, emit `GitLab: not authenticated, run \`glab auth login\`` and move on.

3. **Group, sort, format**:
   - One `##` header per project / repo. Sort groups alphabetically.
   - Items within a group: most recently updated first.
   - Don't merge Jira / GitHub / GitLab groups even if they represent the same logical project. List them as separate sections, each labelled with the platform in parentheses (e.g. `## didomi/console (GitHub)`).
   - Skip empty groups entirely (no orphan headers).

4. **Item shape** (use parentheses for status, not em dashes):
   - Jira: `- SER-1234 (In Review) Webhook handler crash on >1MB payloads`
   - GitHub opened: `- #4570 (opened) chore: refactor auth middleware`
   - GitHub merged: `- #4567 (merged) feat: add OAuth login (PROJ-456)`
   - GitHub reviewed: `- #4571 (reviewed, author: alice) fix: cookie banner z-index`
   - GitLab: `- !89 (merged) fix: rate limit edge case`

5. **Print only the markdown to stdout**, no preamble, no trailing commentary:

   ```markdown
   # Weekly recap, <SINCE> to <TODAY>

   ## SER (Jira)
   - SER-1234 (In Review) Webhook handler crash on >1MB payloads
   - SER-1235 (In Progress) Add OAuth login

   ## didomi/console (GitHub)
   - #4567 (merged) feat: add OAuth login (PROJ-456)
   - #4570 (opened) chore: refactor auth middleware
   - #4571 (reviewed, author: alice) fix: cookie banner z-index

   ## didomi/internal-tools (GitLab)
   - !89 (merged) fix: rate limit edge case
   ```

   If all three platforms returned zero items, print `No activity recorded between <SINCE> and <TODAY>.` instead.

## Rules

- The window is fixed at today minus 7 days. If the user invokes the skill with explicit override instructions, honour those; otherwise do not ask.
- No commentary before or after the markdown block. Just the recap.
- Sentence-case content in bullets. Project / repo headers keep their canonical case (e.g. `didomi/console`, not `Didomi/Console`).
- No em dashes anywhere. Use commas, parentheses, or regular hyphens. Global rule across all repos.
- Don't paste full URLs inline. The Jira key / `#N` / `!N` is enough for the meeting doc; the reader can click through from there.
- If a platform errors out (network, auth, rate limit), record a single line at the top of its section and continue with the other two. Never block the whole recap on one tool failing.
