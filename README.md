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
ansible-galaxy collection install community.general
ansible-playbook --inventory inventory.yml --ask-vault-password --ask-become-pass dotfiles.yml
```

### Run a single role

```bash
make run-role ROLE=shell
```

## Roles

Roles execute in order. Each role can be run individually using its tag.

| Role | Tag | Description |
|------|-----|-------------|
| brew | `brew` | Installs and updates Homebrew, installs `mas` (Mac App Store CLI) |
| system | `system` | Installs CLI utilities, configures macOS system preferences (keyboard, Finder, Dock, etc.) |
| shell | `shell` | Sets up Fish shell, Ghostty terminal, Starship prompt, Fish plugins |
| ssh | `ssh` | Loads SSH keys into `~/.ssh` |
| user | `user` | Creates user directories (`~/developer`, `~/pictures`, `~/downloads`) and links wallpapers |
| apps | `apps` | Installs browsers, dev tools, editors, AI tools, databases, infrastructure, and more |
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

### VM Testing

Requires [Tart](https://github.com/cirruslabs/tart) (`brew install cirruslabs/cli/tart`).

| Command | Description |
|---------|-------------|
| `make vm-create` | Create a clean macOS VM from base image |
| `make vm-start` | Start the test VM |
| `make vm-ssh` | SSH into the test VM |
| `make vm-destroy` | Delete the test VM |

## What's Included

### Shell & Terminal

- [Fish](https://fishshell.com) shell + [Fisher](https://github.com/jorgebucaran/fisher) plugin manager
- [Ghostty](https://ghostty.org) terminal
- [Starship](https://starship.rs) prompt
- GnuPG
- Fish plugins: ssh-agent, done, autopair, replay, sponge, puffer-fish, fzf

### CLI Utilities

bat, duf, eza, fd, fzf, glances, neofetch, ripgrep, wget, zoxide, unar

### Browsers

Google Chrome, Zen, Brave

### Development

HTTPie, Git, git-delta, LazyGit, GitHub CLI, fnm (Node version manager), Bun, scc, hyperfine

### AI

Gemini CLI, Ollama, ChatGPT, Cursor, Claude, Claude Code, CodexBar

### Editors

VS Code, Zed

### Databases

libpq, pgcli, DBeaver

### Infrastructure

AWS CLI, Docker, Docker Compose, Docker Buildx, Google Cloud CLI

### Multimedia

mpv, Spotify

### System & Window Management

Aerospace (tiling window manager), FiraCode Nerd Font, Logi Options+, Mole

### Communication

Slack, Discord, WhatsApp

### Other

nnn (file manager), TradingView, Bitwarden, NextDNS

### NPM Packages

GitHub Copilot

## License

[MIT](LICENSE)
