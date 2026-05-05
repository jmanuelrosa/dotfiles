# jmanuelrosa's dotfiles

Ansible-based macOS dotfiles. Automates the full setup of a development machine — system preferences, shell, terminal, applications, SSH keys, and more. Idempotent, modular, and safe to re-run.

## Requirements

- macOS on Apple Silicon
- [Homebrew](https://brew.sh) (installed automatically by the bootstrap script)
- [Ansible](https://docs.ansible.com) + [`community.general`](https://galaxy.ansible.com/community/general) collection
- Ansible Vault password (for encrypted secrets)

## Quick Start

### Fresh machine

```bash
bash <(curl -s https://raw.githubusercontent.com/jmanuelrosa/dotfiles/main/bootstrap.sh)
```

This clones the repo, installs Homebrew, Ansible, and runs the full playbook.

### Existing machine

```bash
git clone https://github.com/jmanuelrosa/dotfiles.git
cd dotfiles
brew install ansible
ansible-galaxy collection install -r requirements.yml
ansible-playbook --inventory inventory.yml --ask-vault-password --ask-become-pass dotfiles.yml
```

### Run a single role

```bash
make run-role ROLE=shell
```

### Multi-Mac profiles

Two profiles ship out of the box: `personal` (default) and `work`. The active
profile selects which roles run.

```bash
make run                     # personal profile (default)
make run PROFILE=work        # adds the work role + extra SSH key
make check PROFILE=work      # dry-run with work profile
```

Per-profile overrides live in [`host_vars/personal.yml`](host_vars/personal.yml)
and [`host_vars/work.yml`](host_vars/work.yml). The role-to-profile mapping is
in [`group_vars/all.yml`](group_vars/all.yml) under `profile_roles`.

## Roles

Roles execute in order. Each role can be run individually using its tag.

| Role | Tag | Description |
|------|-----|-------------|
| brew | `brew` | Installs and updates Homebrew, installs `mas` (Mac App Store CLI) |
| macos | `macos` | Configures macOS system preferences (keyboard, Finder, Dock) and firmware tweaks (boot sound, hibernation) |
| coreutils | `coreutils` | Installs modern Unix-replacement utilities (bat, eza, fd, fzf, ripgrep, etc.) and links their configs. Domain-specific CLIs (awscli, gh, docker, etc.) live in `apps`. |
| shell | `shell` | Sets up Fish shell, Ghostty terminal, Starship prompt, Fish plugins |
| ssh | `ssh` | Loads SSH keys into `~/.ssh` |
| user | `user` | Creates user directories (`~/developer`, `~/pictures`, `~/downloads`) and links wallpapers |
| apps | `apps` | Installs browsers, dev tools, editors, databases, infrastructure, and more |
| ai | `ai` | Installs and configures AI tools (Claude, Gemini, Ollama, ChatGPT, Cursor, etc.) |
| security | `security` | Installs security tools (NextDNS via Mac App Store) |
| work | `work` | Work-specific SSH keys, credentials, and utility scripts |
| cleanup | `cleanup` | Removes unused Homebrew dependencies and clears cache |
| reboot | `reboot` | Prompts for a system restart |

## Usage

All commands are available through the Makefile.

### Development

| Command | Description |
|---------|-------------|
| `make lint` | Run ansible-lint |
| `make syntax` | Validate playbook syntax (no vault needed) |
| `make check` | Dry-run preview of all changes (no changes applied) |
| `make check-role ROLE=shell` | Dry-run preview of a specific role |

### Execution

| Command | Description |
|---------|-------------|
| `make run` | Execute the full playbook |
| `make run-role ROLE=shell` | Execute a specific role |
| `make verify` | Smoke-test that core tools and config symlinks are in place |
| `make deps` | Install / refresh pinned Ansible collections from `requirements.yml` |

### VM Testing

Use a clean macOS VM via [Tart](https://github.com/cirruslabs/tart) to exercise a fresh-machine bootstrap without polluting your real Mac.

```bash
brew install cirruslabs/cli/tart    # one-time
make vm-create                       # clones a clean macOS Sequoia base image
make vm-start                        # boots the VM (leave running)
make vm-ssh                          # opens a shell into the VM
# inside the VM:
bash <(curl -s https://raw.githubusercontent.com/jmanuelrosa/dotfiles/main/bootstrap.sh)
make verify                          # confirm tools and configs landed
exit                                  # back to host
make vm-destroy                      # tear it down when finished
```

| Command | Description |
|---------|-------------|
| `make vm-create` | Create a clean macOS VM from base image |
| `make vm-start` | Start the test VM |
| `make vm-ssh` | SSH into the test VM |
| `make vm-destroy` | Delete the test VM |

## Customize

This repo is set up for the author's machines, but is intended to be forkable.

### For your own machine

1. Fork the repo and clone it.
2. Replace `vars/secrets.yml` with your own vault-encrypted file. Start from the keys listed in [`vars/work.yml.example`](vars/work.yml.example) and the secrets referenced under [`roles/shell/templates/secrets.fish.j2`](roles/shell/templates/secrets.fish.j2).
3. Drop or replace the `work` role if you don't need work-specific tooling.
4. Adjust `BREW_PACKAGES` (and other overridable values like `VSCODE_EXTENSIONS`, `FISH_PLUGINS`, `OSX_DEFAULTS`) in each role's `defaults/main.yml`. Per-profile overrides go in `host_vars/<profile>.yml`.
5. Run `make check` first to preview, then `make run`.

### Conventions and contributing

See [`AGENTS.md`](AGENTS.md) for layout conventions, commit style, and role anatomy.

## What's Included

### Shell & Terminal

- [Fish](https://fishshell.com) shell + [Fisher](https://github.com/jorgebucaran/fisher) plugin manager
- [Ghostty](https://ghostty.org) terminal
- [Starship](https://starship.rs) prompt
- GnuPG
- Fish plugins: ssh-agent, done, autopair, replay, sponge, puffer-fish, fzf

### CLI Utilities

bat, btop, duf, eza, fastfetch, fd, fzf, httpie, hyperfine, nnn, ripgrep, scc, vnstat, wget, zoxide, unar (modern Unix replacements; configs managed under `roles/coreutils/files/`)

### Browsers

Google Chrome, Zen, Brave, Helium

### Development

Git, git-delta, LazyGit, GitHub CLI, GitLab CLI (glab), fnm (Node version manager), Bun, Sentry CLI, Bruno (API client)

### AI

Gemini CLI, Ollama, ChatGPT, Claude, Claude Code, Cursor, CodexBar

Claude Code skills are managed per-project using the `claude-skill` function:

```bash
claude-skill list                            # Show available skills
claude-skill add vercel-react-best-practices # Link a skill into current project
claude-skill remove vercel-react-best-practices # Remove it
```

### Editors

VS Code

### Databases

libpq, pgcli, DBeaver

### Infrastructure

AWS CLI, Colima, Docker, Docker Compose, Docker Buildx, ctop, Google Cloud CLI

### Multimedia

mpv, Spotify, VLC, BlackHole (16ch virtual audio)

### System & Window Management

Aerospace (tiling window manager), FiraCode Nerd Font, Logi Options+, Mole, Maccy (clipboard manager)

### Communication

Slack, Discord, WhatsApp

### Other

TradingView, Bitwarden, Notion, Figma, SF Symbols, NextDNS

### NPM Packages

GitHub Copilot, Pi Coding Agent

## License

[MIT](LICENSE)
