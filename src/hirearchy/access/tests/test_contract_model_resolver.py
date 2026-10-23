"""Contract of ``ModelResolver``: the charter's model beats the organization's default, which beats the built-in one."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.access import ModelResolver
from hirearchy.access.testing import IMPLEMENTATIONS, AccessHarness
from hirearchy.settings import DEFAULT_MODEL

from ._support import make


@pytest.fixture(params=IMPLEMENTATIONS[ModelResolver], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> AccessHarness:
    made = make(request, tmp_path)
    assert isinstance(made.models, ModelResolver)
    return made


def org_md(default_model: str) -> str:
    return f"---\n{default_model}---\n# Organization\n"


def test_the_built_in_model_is_the_default_of_an_organization_that_names_none(h: AccessHarness) -> None:
    assert DEFAULT_MODEL == "claude-sonnet-5.5"
    assert h.models.default_model() == DEFAULT_MODEL


def test_the_default_model_is_the_one_of_ORG_md(h: AccessHarness) -> None:
    h.put_config(org_md("default_model: claude-opus-5.5\n"))
    assert h.models.default_model() == "claude-opus-5.5"


@pytest.mark.parametrize("line", ["default_model:\n", "default_model: null\n", "default_model: ''\n", "default_model: '   '\n", "other: 1\n"])
def test_a_null_blank_or_missing_default_is_the_built_in_one(h: AccessHarness, line: str) -> None:
    h.put_config(org_md(line))
    assert h.models.default_model() == DEFAULT_MODEL


def test_the_default_model_is_stripped(h: AccessHarness) -> None:
    h.put_config(org_md("default_model: '  m-1  '\n"))
    assert h.models.default_model() == "m-1"


def test_a_change_of_ORG_md_is_seen_by_the_next_call(h: AccessHarness) -> None:
    h.put_config(org_md("default_model: m-1\n"))
    assert h.models.default_model() == "m-1"
    h.put_config(org_md("default_model: m-2\n"))
    assert h.models.default_model() == "m-2"


def test_the_charters_model_beats_the_default(h: AccessHarness) -> None:
    h.put_config(org_md("default_model: m-org\n"))
    h.put_agent("dev", {"role": "R", "model": "m-charter"})
    assert h.models.model_for("dev") == "m-charter"


def test_an_agent_without_a_model_runs_on_the_organizations_default(h: AccessHarness) -> None:
    h.put_config(org_md("default_model: m-org\n"))
    h.put_agent("dev", {"role": "R"})
    assert h.models.model_for("dev") == "m-org"


@pytest.mark.parametrize("model", [None, "", "   "])
def test_a_null_or_blank_model_is_no_model(h: AccessHarness, model: str | None) -> None:
    h.put_config(org_md("default_model: m-org\n"))
    h.put_agent("dev", {"role": "R", "model": model})
    assert h.models.model_for("dev") == "m-org"


def test_with_neither_the_built_in_model_is_used(h: AccessHarness) -> None:
    h.put_agent("dev", {"role": "R"})
    assert h.models.model_for("dev") == DEFAULT_MODEL


def test_the_charters_model_is_stripped_and_read_as_text(h: AccessHarness) -> None:
    h.put_agent("dev", {"role": "R", "model": "  m-1 "})
    assert h.models.model_for("dev") == "m-1"
    h.put_agent("dev", {"role": "R", "model": 5})
    assert h.models.model_for("dev") == "5"


def test_root_runs_on_the_default(h: AccessHarness) -> None:
    h.put_config(org_md("default_model: m-org\n"))
    assert h.models.model_for("root") == "m-org"


def test_an_agent_that_does_not_exist_is_the_error_of_the_charter_reader(h: AccessHarness) -> None:
    with pytest.raises(FileNotFoundError):
        h.models.model_for("nobody")


# ------------------------------------------------------------------------------------------ the effort of a run


def test_the_effort_is_high_when_ORG_md_names_none(h: AccessHarness) -> None:
    assert h.models.effort() == "high"


def test_the_effort_is_the_one_of_ORG_md(h: AccessHarness) -> None:
    h.put_config(org_md("effort: xhigh\n"))
    assert h.models.effort() == "xhigh"


@pytest.mark.parametrize("line", ["effort:\n", "effort: null\n", "effort: ''\n", "effort: '   '\n", "other: 1\n"])
def test_a_null_blank_or_missing_effort_is_high(h: AccessHarness, line: str) -> None:
    h.put_config(org_md(line))
    assert h.models.effort() == "high"


def test_the_effort_is_read_as_written(h: AccessHarness) -> None:
    """A level below the floor is returned as it is: the run command refuses it, not the resolver."""
    h.put_config(org_md("effort: low\n"))
    assert h.models.effort() == "low"


def test_a_change_of_ORG_md_effort_is_seen_by_the_next_call(h: AccessHarness) -> None:
    h.put_config(org_md("effort: max\n"))
    assert h.models.effort() == "max"
    h.put_config(org_md("effort: xhigh\n"))
    assert h.models.effort() == "xhigh"


def test_the_effort_is_high_when_ORG_md_cannot_be_parsed(h: AccessHarness) -> None:
    """The built-in effort: a run is never refused or skipped because of a slipped hand edit (the floor is never below ``high``)."""
    h.put_config("---\neffort: max\nextra_allowed_models: [claude-sonnet-4.6\n---\n# Organization\n")
    assert h.models.effort() == "high"
    h.put_config(org_md("effort: max\n"))
    assert h.models.effort() == "max"
