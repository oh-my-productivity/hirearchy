# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import pytest
import testkit.reach.yaml as yaml
from testkit.kiro_world import kiro_runner
from testkit.reach.hirearchy.core import DEFAULT_MODEL, ROOT, Org

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


def model_arg(cmd: list[str]) -> str:
    assert cmd.count("--model") == 1
    return cmd[cmd.index("--model") + 1]


# ------------------------------------------------------------------------------------------ the run command
def test_the_scheduler_command_always_carries_the_model(org):
    cmd, _, _ = kiro_runner()(org, "ceo", "P")
    assert model_arg(cmd) == "claude-sonnet-5.5" and cmd[-2:] == ["--model", "claude-sonnet-5.5"]
    cmd, _, _ = kiro_runner()(org, "ceo/eng", "P")
    assert model_arg(cmd) == "claude-sonnet-5.5"


def test_the_scheduler_command_keeps_an_explicit_model(org):
    set_config(org, default_model="org-model")
    charter_model(org, "charter-model")
    assert model_arg(kiro_runner()(org, "ceo", "P")[0]) == "charter-model"
    assert model_arg(kiro_runner()(org, "ceo/eng", "P")[0]) == "org-model"


@pytest.mark.parametrize("value", [None, "<missing>"])
def test_the_scheduler_command_for_a_legacy_org_config_uses_the_default(org, value):
    set_config(org, default_model=value)
    assert model_arg(kiro_runner()(org, "ceo", "P")[0]) == DEFAULT_MODEL
