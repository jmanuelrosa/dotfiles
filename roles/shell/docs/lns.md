# lns

The shell role installs a pinned standalone [lns](https://github.com/jmanuelrosa/lns) binary, not a Fish function.
Version and checksum are configured through `LNS` in `defaults/main.yml`.

```fish
lns [ROOT] [--contains STRING] [--broken] [--remove] [--dry-run] [--yes] [--all]
```

`ROOT` defaults to the working directory; listing is read-only unless `--remove` is present.
`--contains` filters the target path, while `--broken` tests whether the link resolves to an existing target.
Targets are normalized one hop rather than fully resolved, preserving path spellings such as `/var`.
An unreadable target cannot match `--contains` but can be reported as broken.

The walker does not follow directory symlinks and excludes dependency, cache, and build trees unless `--all` is supplied.
`CLEAN_CLAUDE_EXCLUDES` remains available as a compatibility override.
Removal previews candidates and confirms once; `--yes` skips the prompt and `--dry-run` leaves links untouched.
Only links are removed, never their targets.
