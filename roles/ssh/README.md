# ssh

Deploys SSH key pairs into `~/.ssh/`.

## What it does

- Ensures `~/.ssh/` exists with mode `0700`.
- Loops over `SSH_KEYS + SSH_KEYS_EXTRA`, writing each entry's `content` to `~/.ssh/<name>` (mode `0600`) and `public` to `~/.ssh/<name>.pub` (mode `0644`).

## Vars

- `SSH_KEYS` (group_vars/all.yml) — base list of `{name, content, public}` deployed on every profile. Default is just the personal `id_ed25519`.
- `SSH_KEYS_EXTRA` (host_vars/<profile>.yml) — additional keys per profile. `host_vars/work.yml` adds `id_didomi`.

## Vault references

`SSH_KEYS` and `SSH_KEYS_EXTRA` reference variables that live in the vault-encrypted `vars/secrets.yml` and `vars/work.yml` (e.g. `SSH_KEY`, `SSH_PUBLIC`, `SSH_DIDOMI_KEY`, `SSH_DIDOMI_PUBLIC`).

## Notes

Private-key writes use `no_log: true` to keep key material out of Ansible output.
