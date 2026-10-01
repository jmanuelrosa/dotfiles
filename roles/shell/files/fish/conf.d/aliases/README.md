# Shell aliases

`aliases.fish` defines navigation, modern Unix tools, Git, Homebrew, Docker, AI cleanup, Kura, and Pi shortcuts.
Fish loads the installed snippet automatically at startup.

The `clean:*` aliases delegate to the cleanup functions; they do not add confirmation or dry-run protection.
`clean:ai` runs the Claude cleaner followed by the Pi cleaner, stopping if the first fails.
Docker shortcuts target the Colima socket exported by [exports](../exports/README.md).

Edit `aliases.fish`, then reload with `source ~/.config/fish/conf.d/aliases.fish`.
