"""How the npm registry tokens stay out of every process but the package manager."""


import pytest
import yaml
from dotkit.testing import REPO

SHELL = REPO / "roles/shell"
WORK = REPO / "roles/work"
KEYCHAIN_TASKS = SHELL / "tasks/keychain_token.yml"
WRAPPERS = SHELL / "files/fish/functions/npm_token"
WRAPPED = ["npm", "npx", "pnpm", "pnpx", "bun", "bunx", "yarn"]

TOKENS = [
    # role, conf.d template, vault variable, keychain names variable, render task
    ("shell", "secrets.fish.j2", "NPM_TOKEN", "NPM_TOKEN_KEYCHAIN", "Render fish secrets file from vault"),
    ("work", "exports.fish.j2", "DID_NPM_TOKEN", "DID_NPM_TOKEN_KEYCHAIN", "Render work secrets file from vault"),
]


def tasks_of(path):
    return yaml.safe_load(path.read_text())


def task(path, name):
    matching = [entry for entry in tasks_of(path) if entry.get("name") == name]
    assert len(matching) == 1, f"expected exactly one '{name}' task in {path}"
    return matching[0]


@pytest.mark.parametrize("role,template,variable,names,render", TOKENS)
def test_no_token_is_exported_and_each_registers_its_keychain_item(role, template, variable, names, render):
    source = (REPO / f"roles/{role}/templates/{template}").read_text()
    entry = f"{variable}:{{{{ {names}.service }}}}:{{{{ {names}.account }}}}"
    assert f"{{{{ {variable} }}}}" not in source
    assert f"{{% if {variable} %}}" in source
    assert f"contains -- {entry} $NPM_TOKEN_KEYCHAIN_ITEMS" in source
    assert f"or set -ga NPM_TOKEN_KEYCHAIN_ITEMS {entry}" in source


@pytest.mark.parametrize("role,template,variable,names,render", TOKENS)
def test_each_role_mirrors_its_token_through_the_shared_tasks(role, template, variable, names, render):
    path = REPO / f"roles/{role}/tasks/main.yml"
    tasks = tasks_of(path)
    include = task(path, f"Mirror {variable} into the login keychain")
    assert include["ansible.builtin.include_tasks"] in (
        "keychain_token.yml",
        "{{ CURRENT_DIR }}/roles/shell/tasks/keychain_token.yml",
    )
    assert include["vars"] == {
        "keychain_token_value": f"{{{{ {variable} }}}}",
        "keychain_token_service": f"{{{{ {names}.service }}}}",
        "keychain_token_account": f"{{{{ {names}.account }}}}",
    }
    rendered = task(path, render)
    assert rendered["diff"] is False
    assert tasks.index(rendered) < tasks.index(include)
    defaults = yaml.safe_load((REPO / f"roles/{role}/defaults/main.yml").read_text())
    assert set(defaults[names]) == {"service", "account"}


def test_the_role_defaults_name_distinct_keychain_items():
    shell = yaml.safe_load((SHELL / "defaults/main.yml").read_text())["NPM_TOKEN_KEYCHAIN"]
    work = yaml.safe_load((WORK / "defaults/main.yml").read_text())["DID_NPM_TOKEN_KEYCHAIN"]
    assert shell["service"] != work["service"]


def keychain_tasks():
    read, guard, store, delete = tasks_of(KEYCHAIN_TASKS)
    return read, guard, store, delete


def test_every_keychain_command_hides_its_output():
    for entry in tasks_of(KEYCHAIN_TASKS):
        if "ansible.builtin.command" in entry:
            assert entry["no_log"] is True, entry["name"]


def test_an_unreadable_keychain_fails_before_the_write():
    read, guard, _, _ = keychain_tasks()
    assert "ansible.builtin.fail" in guard
    assert guard["when"] == f"{read['register']}.rc not in [0, 44]"
    assert "keychain_token_value" not in guard["ansible.builtin.fail"]["msg"]


def test_the_keychain_read_is_quiet_and_runs_in_check_mode():
    read, _, _, _ = keychain_tasks()
    assert read["changed_when"] is False
    assert read["failed_when"] is False
    assert read["check_mode"] is False
    argv = read["ansible.builtin.command"]["argv"]
    assert argv[:2] == ["security", "find-generic-password"]
    assert argv[-1] == "-w"


def test_the_keychain_write_keeps_the_token_off_argv_and_runs_only_on_drift():
    read, _, store, _ = keychain_tasks()
    command = store["ansible.builtin.command"]
    assert command["argv"] == ["security", "-i"]
    assert command["stdin"].startswith("add-generic-password -U ")
    assert "keychain_token_value |" in command["stdin"]
    assert store["diff"] is False
    register = read["register"]
    assert store["when"] == [
        "keychain_token_value | length > 0",
        f"{register}.rc != 0 or {register}.stdout != keychain_token_value",
    ]


def test_an_emptied_vault_value_removes_the_keychain_item():
    read, _, _, delete = keychain_tasks()
    assert delete["ansible.builtin.command"]["argv"][:2] == ["security", "delete-generic-password"]
    assert delete["when"] == ["keychain_token_value | length == 0", f"{read['register']}.rc == 0"]


def test_the_glab_config_render_never_diffs():
    assert task(WORK / "tasks/main.yml", "Render glab config with personal + work hosts")["diff"] is False


def test_the_ssh_private_keys_never_print():
    entry = task(REPO / "roles/ssh/tasks/main.yml", "Install SSH private keys")
    assert entry["no_log"] is True
    assert entry["diff"] is False


def test_every_wrapper_delegates_to_the_keychain_helper():
    for name in WRAPPED:
        source = (WRAPPERS / f"{name}.fish").read_text()
        assert source.startswith(f"function {name} ")
        assert f"_npm_token {name} $argv" in source


def test_the_work_role_no_longer_carries_its_own_wrappers():
    assert not (WORK / "files/fish/functions/npm_token").exists()
