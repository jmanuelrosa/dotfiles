# shell

Provisions Fish, Ghostty, Starship, and Television, plus the pinned standalone `lns` and `shoo` tools.
Installs packages and Fisher plugins, selects Fish as the login shell, and symlinks the repository's configs into `~/.config`.

```sh
make run-role ROLE=shell
```

Provisioning prompts for vault and macOS passwords.
See [defaults](defaults/main.yml) for package lists, plugins, release checksums, and the Television cable allowlist; [tasks](tasks/main.yml) defines installation behavior.
See [lns usage](docs/lns.md) and the upstream [shoo documentation](https://github.com/jmanuelrosa/shoo) for the standalone commands.

## Fish startup snippets

| Feature | Documentation |
|---|---|
| Shell shortcuts | [aliases](files/fish/conf.d/aliases/README.md) |
| Environment defaults | [exports](files/fish/conf.d/exports/README.md) |
| Directory-scoped Google Cloud configuration | [gcloud-profiles](files/fish/conf.d/gcloud-profiles/README.md) |

## Fish functions

| Feature | Documentation |
|---|---|
| Shared AI cleanup helpers | [clean_ai](files/fish/functions/clean_ai/README.md) |
| Claude artifacts and stored state | [clean_claude](files/fish/functions/clean_claude/README.md) |
| Pi artifacts and sessions | [clean_pi](files/fish/functions/clean_pi/README.md) |
| Homebrew, system, and Node cleanup | [clean_all](files/fish/functions/clean_all/README.md) |
| Docker cleanup | [clean_docker](files/fish/functions/clean_docker/README.md) |
| Node dependencies and caches | [clean_node](files/fish/functions/clean_node/README.md) |
| Company-specific Git identity | [create_gitconfig](files/fish/functions/create_gitconfig/README.md) |
| npm registry tokens from the login keychain, per call | [npm_token](files/fish/functions/npm_token/README.md) |
| Pi failure capture | [pi_debug](files/fish/functions/pi_debug/README.md) |
| Directory and history pickers | [television](files/fish/functions/television/README.md) |
| Kura skill picker helpers | [kura](files/fish/functions/kura/README.md) |
| Shared output vocabulary | [ui](files/fish/functions/ui/README.md) |
| Git worktrees | [wt](files/fish/functions/wt/README.md) |

Each feature directory owns its scripts, related helpers, and a short README.
Ansible discovers `.fish` files recursively and installs flat symlinks by filename, preserving Fish's startup and autoload behavior.
Filenames must be unique within each category; documentation is not installed.
Re-run the role after moving or deleting source files: it relinks moved ones and removes the dangling links left behind.
Tests remain under `files/fish/functions/tests/` and `lib/python/tests/`.

## Other configuration

- [config.fish](files/fish/config.fish): interactive startup and key bindings.
- [Ghostty](files/ghostty/config) and [Starship](files/starship.toml): terminal and prompt configuration.
- [Television](files/television/config.toml): picker configuration and vendored [cables](files/television/cable/); the role refreshes upstream channels, prunes those outside the allowlist, and generates Fish integration using the installed `tv` version.
- [secrets.fish.j2](templates/secrets.fish.j2): registers `NPM_TOKEN`'s keychain item for the [npm_token](files/fish/functions/npm_token/README.md) wrappers, rendered with mode `0600`. The token itself is never exported: [keychain_token.yml](tasks/keychain_token.yml) mirrors it from the vault into the login keychain, and the work role reuses that file for `DID_NPM_TOKEN`.

Installation modifies `/etc/shells` and the login shell, and channel updates require network access.
