# reboot

Optional final role that prompts for and (if confirmed) issues a system restart.

## What it does

- `ansible.builtin.pause` asks "Do you want to restart the computer? (yes/no)".
- If the user answers `yes`, runs `shutdown -r now` (requires sudo).

## Vars

None.

## Profile gating

Intentionally **not** gated by `profile_roles`. The interactive prompt itself is the opt-in mechanism — the role runs every playbook execution, but does nothing unless you say yes.
