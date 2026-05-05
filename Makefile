.PHONY: deps lint syntax check check-role run run-role verify vm-create vm-start vm-ssh vm-destroy

# Active profile. Override at the CLI: `make run PROFILE=work`.
PROFILE ?= personal

# Refresh sudo's timestamp, then keep it alive in a background loop while
# whatever follows runs. macOS sudo expires every 5 minutes by default, which
# kills long Ansible runs at the first `become: true` task after the timeout.
# Each line of a Makefile recipe runs in its own shell, so we chain everything
# through `\` to share the keepalive's job control.
SUDO_KEEPALIVE = sudo -v && \
	( while true; do sudo -n true; sleep 60; done ) & \
	KEEPALIVE_PID=$$! ; \
	trap "kill $$KEEPALIVE_PID 2>/dev/null" EXIT INT TERM

# Install / refresh pinned Ansible collections
deps:
	ansible-galaxy collection install -r requirements.yml

# Static analysis
lint:
	ansible-lint

syntax:
	ansible-playbook --syntax-check --inventory inventory.yml --ask-vault-password --extra-vars "profile=$(PROFILE)" dotfiles.yml

# Preview (dry-run, no changes applied)
check:
	@$(SUDO_KEEPALIVE) ; \
	ansible-playbook --check --diff --inventory inventory.yml --ask-vault-password --extra-vars "profile=$(PROFILE)" dotfiles.yml

check-role:
	@test -n "$(ROLE)" || (echo "Usage: make check-role ROLE=shell" && exit 1)
	@$(SUDO_KEEPALIVE) ; \
	ansible-playbook --check --diff --inventory inventory.yml --ask-vault-password --extra-vars "profile=$(PROFILE)" --tags $(ROLE) dotfiles.yml

# Execute
run:
	@$(SUDO_KEEPALIVE) ; \
	ansible-playbook --inventory inventory.yml --ask-vault-password --extra-vars "profile=$(PROFILE)" dotfiles.yml

run-role:
	@test -n "$(ROLE)" || (echo "Usage: make run-role ROLE=shell" && exit 1)
	@$(SUDO_KEEPALIVE) ; \
	ansible-playbook --inventory inventory.yml --ask-vault-password --extra-vars "profile=$(PROFILE)" --tags $(ROLE) dotfiles.yml

# Smoke-test that core tooling and config symlinks landed
verify:
	@echo "Verifying installed tooling..."
	@for cmd in bat eza fd rg fzf fish starship gh git; do \
		if command -v $$cmd >/dev/null 2>&1; then \
			echo "  [ok]   $$cmd"; \
		else \
			echo "  [MISS] $$cmd" && exit 1; \
		fi; \
	done
	@echo "Verifying config symlinks..."
	@for link in \
		$$HOME/.config/bat/config \
		$$HOME/.config/ripgrep/config \
		$$HOME/.config/eza/theme.yml \
		$$HOME/.config/fish/config.fish \
		$$HOME/.config/starship.toml \
		$$HOME/.config/ghostty/config; do \
		if [ -L $$link ]; then \
			echo "  [ok]   $$link"; \
		else \
			echo "  [MISS] $$link" && exit 1; \
		fi; \
	done
	@echo "All checks passed."

# macOS VM testing (requires: brew install cirruslabs/cli/tart)
vm-create:
	tart clone ghcr.io/cirruslabs/macos-sequoia-base:latest dotfiles-test

vm-start:
	tart run dotfiles-test

vm-ssh:
	ssh admin@$$(tart ip dotfiles-test)

vm-destroy:
	tart delete dotfiles-test
