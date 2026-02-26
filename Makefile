.PHONY: lint syntax check check-role run run-role vm-create vm-start vm-ssh vm-destroy

# Static analysis
lint:
	ansible-lint

syntax:
	@echo "dummy" > /tmp/vault_pass
	ansible-playbook --syntax-check --inventory inventory.yml --vault-password-file /tmp/vault_pass dotfiles.yml
	@rm -f /tmp/vault_pass

# Preview (dry-run, no changes applied)
check:
	ansible-playbook --check --diff --inventory inventory.yml --ask-vault-password --ask-become-pass dotfiles.yml

check-role:
	@test -n "$(ROLE)" || (echo "Usage: make check-role ROLE=shell" && exit 1)
	ansible-playbook --check --diff --inventory inventory.yml --ask-vault-password --ask-become-pass --tags $(ROLE) dotfiles.yml

# Execute
run:
	ansible-playbook --inventory inventory.yml --ask-vault-password --ask-become-pass dotfiles.yml

run-role:
	@test -n "$(ROLE)" || (echo "Usage: make run-role ROLE=shell" && exit 1)
	ansible-playbook --inventory inventory.yml --ask-vault-password --ask-become-pass --tags $(ROLE) dotfiles.yml

# macOS VM testing (requires: brew install cirruslabs/cli/tart)
vm-create:
	tart clone ghcr.io/cirruslabs/macos-sequoia-base:latest dotfiles-test

vm-start:
	tart run dotfiles-test

vm-ssh:
	ssh admin@$$(tart ip dotfiles-test)

vm-destroy:
	tart delete dotfiles-test
