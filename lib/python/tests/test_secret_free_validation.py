import yaml
from dotkit.testing import REPO

VARIABLE_FILES = [
    "vars/secrets.yml",
    "vars/work.yml",
    "host_vars/{{ profile }}.yml",
]


def test_vault_and_profile_variables_load_at_runtime_in_override_order():
    play = yaml.safe_load((REPO / "dotfiles.yml").read_text())[0]
    assert "vars_files" not in play
    loads = [task for task in play["pre_tasks"] if "ansible.builtin.include_vars" in task]
    assert len(loads) == 1
    assert loads[0]["ansible.builtin.include_vars"] == "{{ item }}"
    assert loads[0]["loop"] == VARIABLE_FILES


def test_runtime_variable_loading_is_private_and_runs_with_role_tags():
    play = yaml.safe_load((REPO / "dotfiles.yml").read_text())[0]
    task = play["pre_tasks"][0]
    assert "ansible.builtin.include_vars" in task
    assert task.get("no_log") is True
    assert "always" in task.get("tags", [])


def test_make_syntax_needs_no_vault_password():
    makefile = (REPO / "Makefile").read_text()
    recipe = makefile.split("\nsyntax:\n", 1)[1].split("\n\n", 1)[0]
    assert "ansible-playbook --syntax-check" in recipe
    assert "--ask-vault-password" not in recipe
    assert "--vault-password-file" not in recipe


def test_ci_lint_and_both_profile_syntax_checks_need_no_secrets():
    workflow = yaml.safe_load((REPO / ".github/workflows/pull_request.yml").read_text())
    job = workflow["jobs"]["lint"]
    steps = {step["name"]: step for step in job["steps"]}
    checks = {
        "Run ansible-lint": "ansible-lint",
        "Run syntax check (personal profile)": "make syntax PROFILE=personal",
        "Run syntax check (work profile)": "make syntax PROFILE=work",
    }
    for name, command in checks.items():
        step = steps[name]
        assert step["run"].strip() == command
        assert "ANSIBLE_VAULT_PASSWORD" not in step.get("env", {})
        assert "if" not in step
        assert not step.get("continue-on-error", False)


def test_ansible_internal_errors_are_not_silenced():
    config = yaml.safe_load((REPO / ".ansible-lint").read_text())
    assert "internal-error" not in config.get("warn_list", [])
    assert "internal-error" not in config.get("skip_list", [])
