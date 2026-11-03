# prt

Shortcut for the `pr-track` skill's script, which lives in the agent catalog.

```fish
prt                      # list tracked PRs and anything that needs you
prt ack <ref>            # clear a PR's "needs you" items
prt drafts <ref>         # replies drafted for teammates, to post yourself
prt add <url>            # track a PR from its repo, merging it once ready
prt merge <ref> [--off]  # keep tracking without merging, or see what the merge waits for
prt rm <ref> [--force]   # stop tracking
prt take <ref>           # apply work a rejected push left behind, then /ship
```

`<ref>` is the URL, or the PR number when only one tracked PR has it.
`/ship` and `/pr` ask whether to track the PR they open, so `prt add` is only for a PR opened some other way.
A tracked PR's bot comments, teammate comments, CI failures and conflicts are fixed and pushed in the background; a macOS notification arrives only for judgment calls, stuck runs, requested changes, and a merge or close.
Your local branch falls behind after such a push, so pull before continuing on it.
The background poller is the `ai` role's `dotfiles.pr-track` launch agent, which logs to `~/Library/Logs/pr-track.log`.
