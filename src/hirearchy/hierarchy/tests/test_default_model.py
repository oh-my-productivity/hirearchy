# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import testkit.reach.yaml as yaml
from testkit.reach.hirearchy.core import DEFAULT_MODEL, ROOT, Org


def set_config(org: Org, **kw) -> None:
    """Rewrite ORG.md's frontmatter (a legacy org: ``default_model: null`` or no key at all)."""
    path = org.root / "ORG.md"
    meta, body = path.read_text().split("---\n", 2)[1:]
    cfg = yaml.safe_load(meta)
    cfg.update(kw)
    for k in [k for k, v in kw.items() if v == "<missing>"]:
        cfg.pop(k)
    path.write_text("---\n" + yaml.safe_dump(cfg) + "---\n" + body)


def test_hire_without_a_model_leaves_the_charter_unpinned_so_the_org_default_applies(org):
    org.hire(ROOT, "ops", "Ops", "Do ops.")
    assert "model" not in org.charter("ops")[0] and org.model_for("ops") == DEFAULT_MODEL
    set_config(org, default_model="later")
    assert org.model_for("ops") == "later"  # a later org-wide choice reaches the agent
    org.hire(ROOT, "pinned", "Pinned", "Pinned.", model="m-x")
    assert org.model_for("pinned") == "m-x"
