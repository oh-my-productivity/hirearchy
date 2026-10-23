"""Contract of ``ModelFloorAudit``: the agents whose model is outside the allowed set are named, with the fix, and nothing else changes."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.access import ModelFloorAudit
from hirearchy.access.testing import IMPLEMENTATIONS, AccessHarness

from ._support import make

PAIR = "claude-sonnet-5.5, claude-opus-5.5"
FIX = (
    "Fix: set model: claude-sonnet-5.5 in each one's AGENT.md (you for your direct reports, the manager for the others); "
    "they keep running as they are until then."
)


@pytest.fixture(params=IMPLEMENTATIONS[ModelFloorAudit], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> AccessHarness:
    made = make(request, tmp_path)
    assert isinstance(made.floor, ModelFloorAudit)
    return made


def org_md(lines: str) -> str:
    return f"---\n{lines}---\n# Organization\n"


def test_nothing_is_below_the_floor_by_default(h: AccessHarness) -> None:
    h.put_agent("ceo", {"role": "R"})
    h.put_agent("cto", {"role": "R", "model": "claude-sonnet-5.5"})
    h.put_agent("cfo", {"role": "R", "model": "claude-opus-5.5"})
    assert h.floor.below_floor() == []
    assert h.floor.note() == ""


def test_an_organization_without_agents_has_nothing_below_the_floor(h: AccessHarness) -> None:
    assert h.floor.below_floor() == [] and h.floor.note() == ""


def test_an_agent_with_a_charter_model_outside_the_set_is_named(h: AccessHarness) -> None:
    h.put_agent("ceo", {"role": "R", "model": "claude-haiku-4.5"})
    h.put_agent("cto", {"role": "R", "model": "claude-opus-5.5"})
    assert h.floor.below_floor() == [("ceo", "claude-haiku-4.5")]


def test_agents_that_inherit_a_default_model_outside_the_set_are_named(h: AccessHarness) -> None:
    h.put_config(org_md("default_model: claude-haiku-4.5\n"))
    h.put_agent("ceo", {"role": "R"})
    h.put_agent("cto", {"role": "R", "model": "claude-sonnet-5.5"})
    assert h.floor.below_floor() == [("ceo", "claude-haiku-4.5")]


def test_a_widened_set_admits_its_extra_ids(h: AccessHarness) -> None:
    h.put_config(org_md("extra_allowed_models: [claude-sonnet-4.6]\n"))
    h.put_agent("ceo", {"role": "R", "model": "claude-sonnet-4.6"})
    h.put_agent("cto", {"role": "R", "model": "claude-haiku-4.5"})
    assert h.floor.below_floor() == [("cto", "claude-haiku-4.5")]
    assert h.floor.note().startswith(f"Model floor: below the allowed models ({PAIR}, claude-sonnet-4.6): cto on claude-haiku-4.5. ")


def test_the_note_is_one_line_naming_each_agent_and_the_fix(h: AccessHarness) -> None:
    h.put_agent("ceo", {"role": "R"})
    h.put_agent("ceo/eng", {"role": "R", "model": "claude-haiku-4.5"})
    h.put_agent("ops", {"role": "R", "model": "claude-sonnet-4.6"})
    assert h.floor.note() == f"Model floor: below the allowed models ({PAIR}): ceo/eng on claude-haiku-4.5, ops on claude-sonnet-4.6. {FIX}"
    assert "\n" not in h.floor.note()


def test_the_order_is_the_directory_order_and_root_is_never_listed(h: AccessHarness) -> None:
    h.put_agent("zed", {"role": "R", "model": "m-z"})
    h.put_agent("ceo", {"role": "R", "model": "m-c"})
    h.put_agent("ceo/eng", {"role": "R", "model": "m-e"})
    assert [addr for addr, _ in h.floor.below_floor()] == ["ceo", "ceo/eng", "zed"]
    assert "root" not in [addr for addr, _ in h.floor.below_floor()]


# ------------------------------------------------------------------------------ an ORG.md whose settings block cannot be parsed

BROKEN = "---\nmax_depth: 4\nextra_allowed_models: [claude-sonnet-4.6\n---\n# Organization\n"  # a hand edit slipped: the YAML does not parse


def test_an_ORG_md_that_cannot_be_parsed_names_nobody_and_raises_nothing(h: AccessHarness) -> None:
    """Root's status and whoami answer as they did before the floor: the allowed set is unknown, so no agent is claimed to be below it."""
    h.put_agent("ceo", {"role": "R", "model": "claude-haiku-4.5"})
    h.put_agent("cto", {"role": "R"})
    h.put_config(BROKEN)
    assert h.floor.below_floor() == []
    assert h.floor.note() == ""


def test_the_agents_are_named_again_once_ORG_md_is_repaired(h: AccessHarness) -> None:
    h.put_agent("ceo", {"role": "R", "model": "claude-haiku-4.5"})
    h.put_config(BROKEN)
    assert h.floor.note() == ""
    h.put_config(org_md("max_depth: 4\n"))
    assert h.floor.below_floor() == [("ceo", "claude-haiku-4.5")]
