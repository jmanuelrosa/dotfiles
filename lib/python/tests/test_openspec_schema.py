"""The `product-team` OpenSpec schema is structurally sound without the CLI present.

`openspec schema validate` is the real authority, but it needs the CLI installed and this
suite runs with no network and no node. What is checkable here is the part that breaks
silently: a template renamed without updating `schema.yaml`, a `requires:` edge naming an
artifact that does not exist, or a cycle. Each of those makes the schema unusable while
the file still looks fine, and none of them is caught by reading it.

The DAG assertions are deliberately structural rather than pinning the exact order, so
inserting a stage does not fail this suite for the wrong reason. The one ordering fact
that IS pinned is `red-team` seeing the design, because that placement is the whole
difference between this schema and the pipeline it improves on.
"""

import yaml

from dotkit.testing import REPO

SCHEMA_DIR = REPO / "roles/ai/files/openspec/schemas/product-team"
SCHEMA = SCHEMA_DIR / "schema.yaml"
TEMPLATES = SCHEMA_DIR / "templates"

# Upstream's four, which are carried unchanged so a future fork stays diffable.
STOCK_TEMPLATES = ("proposal.md", "spec.md", "design.md", "tasks.md")

# The three stages the measured comparison showed spec-driven lacks.
ADDED_ARTIFACTS = ("research", "ux-spec", "red-team")


def load():
    return yaml.safe_load(SCHEMA.read_text())


def artifacts():
    return {a["id"]: a for a in load()["artifacts"]}


def test_schema_parses_and_is_named():
    schema = load()
    assert schema["name"] == "product-team"
    assert schema["description"].strip()


def test_every_template_referenced_exists():
    for artifact in artifacts().values():
        target = TEMPLATES / artifact["template"]
        assert target.is_file(), f"{artifact['id']} references a missing template: {target}"


def test_no_orphan_templates():
    referenced = {a["template"] for a in artifacts().values()}
    on_disk = {p.name for p in TEMPLATES.iterdir() if p.suffix == ".md"}
    assert on_disk == referenced, "a template on disk is referenced by no artifact, or vice versa"


def test_stock_templates_are_present():
    for name in STOCK_TEMPLATES:
        assert (TEMPLATES / name).is_file()


def test_every_requires_edge_names_a_declared_artifact():
    declared = set(artifacts())
    for name, artifact in artifacts().items():
        for dependency in artifact.get("requires") or []:
            assert dependency in declared, f"{name} requires undeclared artifact {dependency!r}"


def test_apply_requires_a_declared_artifact():
    for dependency in load()["apply"]["requires"]:
        assert dependency in artifacts()


def test_the_graph_is_acyclic_and_fully_reachable():
    graph = {name: list(a.get("requires") or []) for name, a in artifacts().items()}

    resolved, guard = set(), len(graph) + 1
    while len(resolved) < len(graph) and guard:
        for name, dependencies in graph.items():
            if name not in resolved and all(d in resolved for d in dependencies):
                resolved.add(name)
        guard -= 1
    assert resolved == set(graph), f"cycle or unreachable artifact among {set(graph) - resolved}"


def test_exactly_one_root():
    roots = [name for name, a in artifacts().items() if not (a.get("requires") or [])]
    assert len(roots) == 1, f"expected one entry point, found {roots}"


def test_the_added_stages_are_present_and_instructed():
    declared = artifacts()
    for name in ADDED_ARTIFACTS:
        assert name in declared, f"{name} is the point of this schema and is missing"
    for name, artifact in declared.items():
        assert artifact.get("instruction", "").strip(), f"{name} carries no instruction"


def test_red_team_sees_the_design():
    """The one ordering fact worth pinning.

    Putting the adversarial pass after the design is what separates this schema from the
    product-team pipeline, whose stage-3 placement never sees one. The measured run found
    the pipeline missing design-level defects until implementation because of it.
    """
    assert "design" in artifacts()["red-team"]["requires"]


def test_ux_spec_precedes_the_design():
    """States drive the data contract, so the design has to be able to read them."""
    assert "ux-spec" in artifacts()["design"]["requires"]


def test_tasks_cannot_be_written_before_the_adversarial_pass():
    assert "red-team" in artifacts()["tasks"]["requires"]
