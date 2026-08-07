# Add dive, swap ctop for lazydocker

## Context

The container tooling in the `apps` role installs the colima/docker runtime plus `ctop` as the only inspection TUI. Two gaps prompted this:

- Nothing here inspects **image layers**. `dive` covers that (what each layer adds, wasted space, an efficiency score), and it overlaps with nothing already installed.
- `ctop` and `lazydocker` were being considered side by side. They should not both ship.

`ctop` is a live per-container metric grid. `lazydocker` does all of that plus images, volumes, networks, compose projects, logs, exec and prune. Three facts settle it:

- `ctop` last cut a release in **March 2022** (v0.7.7); `lazydocker` is at **v0.25.2, April 2026**.
- `lazydocker` is by the same author as `lazygit`, which this repo already installs and themes heavily (`roles/apps/files/lazygit/config.yml`). The keybinding idiom and config schema transfer.
- `ctop`'s feature set is a strict subset, so keeping both buys a second thing to configure and nothing else.

Outcome: `ctop` is removed, `lazydocker` and `dive` are added, both with managed configs, and the handful of places that name `ctop` are updated. All three formulas are confirmed present in homebrew-core, so no tap and no `trusted` entry is needed.

## Changes

### 1. `roles/apps/defaults/main.yml`, the `# Infrastructure` block (lines 54-61)

Drop `- ctop`; add `- dive` and `- lazydocker`, keeping the existing loose grouping:

```yaml
    # Infrastructure
    - awscli
    - colima
    - dive
    - docker
    - docker-compose
    - docker-buildx
    - docker-credential-helper
    - lazydocker
```

### 2. `roles/apps/tasks/infrastructure.yml`

**Removing a formula from the list does not uninstall it.** `tasks/main.yml:18-22` passes the list with `state: present` only, so `ctop` stays on disk forever unless an explicit task removes it. Follow the existing precedent at `infrastructure.yml:5-11` (`Remove orphaned docker-completion formula`), which is exactly this pattern:

- Add a `community.general.homebrew` task with `name: ctop`, `state: absent`, carrying a comment saying it was superseded by lazydocker. Idempotent: a no-op once gone.
- Add an `ansible.builtin.file` task with `path: "{{ HOME }}/.config/ctop"`, `state: absent` to clear the orphaned config directory.
- Delete the two existing ctop tasks (lines 26-37: the config dir and the symlink).

Then add the two new config symlinks, mirroring the shape the deleted ctop tasks used (a `state: directory` task, then a `state: link` task with `force: true`). `state: link` does not create intermediate directories, so the explicit `mode: "0755"` directory task is required for both:

- **lazydocker**: dir `{{ HOME }}/Library/Application Support/jesseduffield/lazydocker`, link `.../config.yml` to `{{ role_path }}/files/lazydocker/config.yml`. That path is upstream's documented macOS location (`docs/Config.md`) and it is *not* XDG. Note the `jesseduffield/` vendor segment, which the `lazygit` task at `tasks/development.yml:15-22` does not have.
- **dive**: dir `{{ HOME }}/.config/dive`, link `.../config.yaml` to `{{ role_path }}/files/dive/config.yaml`. `~/.config/dive/*.yaml` is one of dive's documented search paths, so the `~/.dive.yaml` form is not needed.

Keep `src` as `{{ role_path }}/files/...` on both, per the repo rule in `CLAUDE.md`.

### 3. New `roles/apps/files/lazydocker/config.yml`

Read `docs/Config.md` from the lazydocker repo for the current schema before writing (it was only partially reviewed during planning; do not write keys from memory). Theme it to match `roles/apps/files/lazygit/config.yml`: `gui.border: rounded`, `gui.nerdFontsVersion: "3"`, and the same Tokyo Night border and selection colours (`#ff9e64` active, `#27a1b9` inactive, `#283457` selected line). Add a leading comment naming the upstream docs URL, matching the style of `files/ctop/config`.

### 4. New `roles/apps/files/dive/config.yaml`

Upstream says no configuration is necessary, so keep it minimal and defensible: `container-engine: docker` and `log.enabled: false`. Same leading comment convention.

### 5. Delete `roles/apps/files/ctop/` (the directory and its `config`)

### 6. Docs and shell references

| File:line | Change |
|---|---|
| `README.md:187` | Infrastructure prose list: drop `ctop`, add `dive` and `lazydocker` |
| `roles/apps/README.md:11` | `infrastructure.yml` description: "ctop config" becomes "lazydocker and dive configs" |
| `roles/coreutils/README.md:10` | **Pre-existing bug**: claims this role symlinks the ctop config, which it never did (it lives in `apps`). Drop `ctop` from `(bat, ripgrep, eza, btop, ctop)` |
| `roles/shell/files/fish/config.fish:62` | `__done_exclude` regex: replace `ctop` with `lazydocker`, add `dive`. Both are full-screen TUIs and will otherwise fire spurious `done` notifications |
| `roles/ai/files/claude/settings.json` | In `permissions.deny` (lines 305-306): remove `Bash(ctop)` and `Bash(ctop *)`, add `Bash(dive)` and `Bash(dive *)`. `Bash(lazydocker)` and `Bash(lazydocker *)` are already there at 311-312. This list denies Claude launching terminal-hijacking TUIs, so `dive` belongs in it |

## Out of scope

`roles/shell/files/fish/conf.d/aliases.fish:49-51`: `docker:start` and `docker:stop` call `systemctl`, which does not exist on macOS, and the runtime here is colima anyway. A real bug, found while exploring, but unrelated to this change. Worth a separate commit.

## Verification

1. `make lint` for ansible-lint over the changed tasks. Needs the vault password.
2. `make test` for the python suites. No vault, no network. Nothing here touches claude-kit, so this is a regression guard rather than a target.
3. `make check-role ROLE=apps` for a dry-run with `--check --diff`. Confirm the diff shows: ctop absent, the two removals, the four new file tasks. Nothing else should report changed.
4. `make run-role ROLE=apps` to apply.
5. Confirm the end state:
   - `dive --version` and `lazydocker --version` both respond.
   - `command -v ctop` returns nothing, and `test -e ~/.config/ctop` is false.
   - `ls -l "$HOME/Library/Application Support/jesseduffield/lazydocker/config.yml"` and `ls -l ~/.config/dive/config.yaml` are symlinks into this checkout.
6. Re-run `make run-role ROLE=apps` and confirm it reports **no changed tasks**. Idempotency is mandatory here, and the two `state: absent` tasks are the ones most likely to break it.
7. Launch `lazydocker` against a running colima and confirm the theme applied (rounded borders, orange active border); run `dive <some-local-image>` and confirm it reads the config without warning.
