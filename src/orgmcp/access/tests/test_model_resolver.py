# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import testkit.reach.yaml as yaml
from testkit.reach.orgmcp.core import DEFAULT_MODEL, ROOT, Org

CHARTER = "---\nrole: CEO\n{model}tools: [read]\n---\nLead.\n"


def set_config(org: Org, **kw) -> None:
    """Rewrite ORG.md's frontmatter (a legacy org: ``default_model: null`` or no key at all)."""
    path = org.root / "ORG.md"
    meta, body = path.read_text().split("---\n", 2)[1:]
    cfg = yaml.safe_load(meta)
    cfg.update(kw)
    for k in [k for k, v in kw.items() if v == "<missing>"]:
        cfg.pop(k)
    path.write_text("---\n" + yaml.safe_dump(cfg) + "---\n" + body)


def charter_model(org: Org, model: str | None) -> None:
    org.write(ROOT, "ceo/AGENT.md", CHARTER.format(model=f"model: {model}\n" if model else ""))


# ------------------------------------------------------------------------------------------ resolution order
def test_charter_model_beats_org_config_beats_default(org):
    assert org.model_for("ceo") == DEFAULT_MODEL  # no model anywhere
    set_config(org, default_model="org-model")
    assert org.model_for("ceo") == "org-model" and org.model_for("ceo/eng") == "org-model"
    charter_model(org, "charter-model")
    assert org.model_for("ceo") == "charter-model" and org.model_for("ceo/eng") == "org-model"
