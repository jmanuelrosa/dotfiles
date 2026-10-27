# superfile

Wraps the `spf` terminal file manager so quitting it leaves the shell in the last directory it showed.

```fish
spf [args...]
```

It relies on `cd_on_quit = true` in the managed config at `roles/apps/files/superfile/config.toml`.
