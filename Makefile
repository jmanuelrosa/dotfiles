.PHONY: deps lint syntax check check-role run run-role test verify harness harness-check harness-apply harness-report vm-create vm-start vm-ssh vm-destroy

# Active profile. Override at the CLI: `make run PROFILE=work`.
PROFILE ?= personal

# The harness payload, and its generator. uv supplies a Python with tomllib whatever
# python3 is on PATH.
HARNESS ?= roles/ai/files/harness
HARNESS_BUILD = uv run --no-project python $(HARNESS)/bin/harness-build

# Test deps are resolved per-run by uv, so there is no venv to create or refresh.
PYTEST = uv run --with pytest --with pyyaml pytest

# Install / refresh pinned Ansible collections
deps:
	ansible-galaxy collection install -r requirements.yml

# Static analysis
lint:
	ansible-lint

# Every python suite: the tools, the registries, the skill scripts, the hook, and the
# suite layout itself. Fast, hermetic, no vault or become password.
#
# The roots are listed in pytest.ini rather than here, so `pytest` on its own collects
# what `make test` does. Naming one path here is what let four suites go dark.
#
# PYTHONDONTWRITEBYTECODE keeps pytest's assertion rewriter from leaving __pycache__
# inside a skill directory, which is symlinked whole into ~/.claude.
test:
	PYTHONDONTWRITEBYTECODE=1 $(PYTEST) -q

# Render every harness's permission and sandbox files from $(HARNESS)/policy. Writes
# Claude's settings.json only when an owned key changed, so close Claude sessions first.
harness:
	PYTHONDONTWRITEBYTECODE=1 $(HARNESS_BUILD) build

# Write nothing; name each file or owned key that no longer matches the policy.
harness-check:
	PYTHONDONTWRITEBYTECODE=1 $(HARNESS_BUILD) build --check

# Merge the policy's owned keys into ~/.codex/config.toml and install its rules file,
# which the ai role also does on every run. CHECK=1 writes nothing.
harness-apply:
	PYTHONDONTWRITEBYTECODE=1 $(HARNESS_BUILD) apply codex $(if $(CHECK),--check)

# Every policy rule a harness receives no counterpart for.
harness-report:
	PYTHONDONTWRITEBYTECODE=1 $(HARNESS_BUILD) report

syntax:
	ansible-playbook --syntax-check --inventory inventory.yml --ask-vault-password --extra-vars "profile=$(PROFILE)" dotfiles.yml

# Preview (dry-run, no changes applied)
check:
	ansible-playbook --check --diff --inventory inventory.yml --ask-vault-password --ask-become-pass --extra-vars "profile=$(PROFILE)" dotfiles.yml

check-role:
	@test -n "$(ROLE)" || (echo "Usage: make check-role ROLE=shell" && exit 1)
	ansible-playbook --check --diff --inventory inventory.yml --ask-vault-password --ask-become-pass --extra-vars "profile=$(PROFILE)" --tags $(ROLE) dotfiles.yml

# Execute
run:
	ansible-playbook --inventory inventory.yml --ask-vault-password --ask-become-pass --extra-vars "profile=$(PROFILE)" dotfiles.yml

run-role:
	@test -n "$(ROLE)" || (echo "Usage: make run-role ROLE=shell" && exit 1)
	ansible-playbook --inventory inventory.yml --ask-vault-password --ask-become-pass --extra-vars "profile=$(PROFILE)" --tags $(ROLE) dotfiles.yml

# Smoke-test that core tooling and config symlinks landed
verify:
	@echo "Verifying installed tooling..."
	@for cmd in bat eza fd rg tv fish starship gh git hostof lns shoo; do \
		if command -v $$cmd >/dev/null 2>&1; then \
			echo "  [ok]   $$cmd"; \
		else \
			echo "  [MISS] $$cmd" && exit 1; \
		fi; \
	done
	@if [ -f $$HOME/.local/bin/hostof ] && [ ! -L $$HOME/.local/bin/hostof ]; then \
		echo "  [ok]   $$HOME/.local/bin/hostof is a release asset"; \
	else \
		echo "  [MISS] $$HOME/.local/bin/hostof is not a release asset" && exit 1; \
	fi
	@if [ -f $$HOME/.local/bin/lns ] && [ ! -L $$HOME/.local/bin/lns ]; then \
		echo "  [ok]   $$HOME/.local/bin/lns is a release asset"; \
	else \
		echo "  [MISS] $$HOME/.local/bin/lns is not a release asset" && exit 1; \
	fi
	@if [ -f $$HOME/.local/bin/shoo ] && [ ! -L $$HOME/.local/bin/shoo ]; then \
		echo "  [ok]   $$HOME/.local/bin/shoo is a release asset"; \
	else \
		echo "  [MISS] $$HOME/.local/bin/shoo is not a release asset" && exit 1; \
	fi
	@echo "Verifying config symlinks..."
	@for link in \
		$$HOME/.config/bat/config \
		$$HOME/.config/ripgrep/config \
		$$HOME/.config/eza/theme.yml \
		$$HOME/.config/fish/config.fish \
		$$HOME/.config/starship.toml \
		$$HOME/.config/ghostty/config \
		$$HOME/.config/television/config.toml; do \
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
