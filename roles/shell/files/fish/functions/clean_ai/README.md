# Shared AI cleanup helpers

These helpers serve both [clean_claude](../clean_claude/README.md) and [clean_pi](../clean_pi/README.md), despite several retaining Claude-prefixed names.
They discover project directories, exclude dependency/cache/build trees, flag Git-tracked candidates, and collect destructive-action confirmation.
They are not standalone commands.

`CLEAN_CLAUDE_EXCLUDES` extends the shared exclusions; `--include` opts a normally excluded directory name back in for a run.
First-party monorepo directories such as `apps` and `packages` remain searchable.

The `clean:ai` alias runs both cleaners in sequence.
Each cleaner previews and confirms separately; a combined purge therefore requires both confirmations.
