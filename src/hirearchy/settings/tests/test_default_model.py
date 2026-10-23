# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import pytest
import testkit.reach.yaml as yaml
from testkit.reach.hirearchy.core import DEFAULT_CONFIG, DEFAULT_MODEL, ROOT, Org

from hirearchy.kernel import OrgError

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
    """A charter written before the model floor (docs/design/org-agent-model-floor.md): on disk, behind ``write``, which would refuse the id."""
    (org.dir("ceo") / "AGENT.md").write_text(CHARTER.format(model=f"model: {model}\n" if model else ""), encoding="utf-8")


# ------------------------------------------------------------------------------------------ the constant
def test_the_default_is_one_constant_used_by_the_default_config():
    assert DEFAULT_MODEL == "claude-sonnet-5.5" and DEFAULT_CONFIG["default_model"] == DEFAULT_MODEL


@pytest.mark.parametrize("value", [None, "", "<missing>"])
def test_an_org_without_an_explicit_default_model_runs_on_the_default(org, value):
    set_config(org, default_model=value)  # ORG.md says `default_model: null`, an empty value, or has no such key
    assert org.default_model == DEFAULT_MODEL and org.model_for("ceo") == DEFAULT_MODEL
    charter_model(org, "kept-explicit")
    assert org.model_for("ceo") == "kept-explicit"


def test_a_new_org_writes_the_default_and_an_explicit_one_is_kept(tmp_path):
    fresh = Org.init(tmp_path / "a", "m")
    assert fresh.config["default_model"] == DEFAULT_MODEL and "default_model: claude-sonnet-5.5" in (fresh.root / "ORG.md").read_text()
    other = Org.init(tmp_path / "b", "m", {"default_model": "claude-opus-5.5"})
    assert other.default_model == "claude-opus-5.5"
    with pytest.raises(OrgError, match="default_model: model .claude-haiku-4.5. is not allowed"):
        Org.init(tmp_path / "c", "m", {"default_model": "claude-haiku-4.5"})
    assert not (tmp_path / "c" / "ORG.md").exists()
