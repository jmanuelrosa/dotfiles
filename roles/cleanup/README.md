# cleanup

Reclaims disk by removing unused Homebrew dependencies and pruning the cache.

## What it does

- `brew autoremove` — removes formulae installed only as dependencies that nothing depends on now.
- `brew cleanup --prune=all`: removes old versions of installed formulae and the entire download cache.

## Vars

None.

## Notes

Each task uses `changed_when: result.stdout != ""` — they're effectively no-ops when there's nothing to clean, so the run reports "ok" rather than perpetual "changed".
