"""The hierarchy slice of the ``Org`` facade: ``hire``, ``retire`` and ``retire_team`` behave as they always did (green before and after), and now go
through the ports of the runtime (``hiring`` and ``retirement``); the refund note and the charter body come from the notices and the document templates
of the runtime, not from the legacy ``templates`` module."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from orgmcp import core
from orgmcp.app import Org, wiring
from orgmcp.hierarchy import Hiring, Retired, Retirement
from orgmcp.kernel import OrgError
from orgmcp.templates import DocumentTemplates, Notices
from orgmcp.templates.testing import RecordingNotices


@pytest.fixture
def org(tmp_path: Path) -> Org:
    made = Org.init(tmp_path / "org", "mission")
    made.hire("root", "ceo", "Chief", "Run it.", can_hire=True, max_children=2)
    made.hire("ceo", "eng", "Engineer", "Build.")
    return made


# ----------------------------------------------------------------------------------- as it always was (green before and after)


def test_hire_writes_the_charter_and_returns_the_address(org: Org) -> None:
    assert org.hire("ceo", "ops", "Ops", "Do ops.", tools=[]) == "ceo/ops"
    meta, body = org.charter("ceo/ops")
    assert (meta["role"], meta["hired_by"], meta["can_hire"], meta["max_children"]) == ("Ops", "ceo", False, 5)
    assert body == "# Role: Ops\n\nDo ops."


def test_hire_refuses_with_the_words_it_always_used(org: Org) -> None:
    with pytest.raises(OrgError, match="not a reserved word"):
        org.hire("ceo", "work", "R", "c")
    with pytest.raises(OrgError, match="does not allow hiring"):
        org.hire("ceo/eng", "kid", "R", "c")
    with pytest.raises(OrgError, match="ceo/eng already exists"):
        org.hire("ceo", "eng", "R", "c")


def test_retire_team_returns_a_retired_that_core_exports(org: Org) -> None:
    org.send("root", "ceo", "runs", budget=6)
    org.send("ceo", "ceo/eng", "runs", budget=4)
    result = org.retire_team("ceo", "eng", "done")
    assert getattr(core, "Retired") is Retired and isinstance(result, Retired) and result == ("ceo/eng", 4, "ceo")
    assert org.budget("ceo") == 6 and not org.exists("ceo/eng")


def test_retire_returns_the_address(org: Org) -> None:
    assert org.retire("ceo", "eng", "done") == "ceo/eng"


# -------------------------------------------------------------------------------------------- through the ports


class Hirer(Hiring):
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def hire(self, actor: str, name: str, role: str, charter: str, **kw: object) -> str:
        self.calls.append((actor, name, role, charter, kw))
        return "from-the-port"


class Retirer(Retirement):
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str, str]] = []

    def retire(self, actor: str, name: str, reason: str) -> str:
        self.calls.append(("retire", actor, name, reason))
        return "retire-from-the-port"

    def retire_team(self, actor: str, name: str, reason: str) -> Retired:
        self.calls.append(("retire_team", actor, name, reason))
        return Retired("team-from-the-port", 1, None)


def test_hire_comes_from_the_hiring_of_the_runtime_with_every_argument(org: Org) -> None:
    hirer = Hirer()
    org.runtime = dataclasses.replace(org.runtime, hiring=hirer)
    assert org.hire("ceo", "ops", "Ops", "Do ops.", model="m", tools=["b"], can_hire=True, max_children=3, workspace="/w", inputs=["/i"]) == "from-the-port"
    assert hirer.calls == [("ceo", "ops", "Ops", "Do ops.", {
        "model": "m", "tools": ["b"], "can_hire": True, "max_children": 3, "workspace": "/w", "inputs": ["/i"],
    })]


def test_the_defaults_of_hire_are_the_ones_it_always_had(org: Org) -> None:
    hirer = Hirer()
    org.runtime = dataclasses.replace(org.runtime, hiring=hirer)
    org.hire("ceo", "ops", "Ops", "Do ops.")
    assert hirer.calls[0][4] == {
        "model": None, "tools": None, "can_hire": False, "max_children": 5, "workspace": None, "inputs": None,
    }


def test_retire_and_retire_team_come_from_the_retirement_of_the_runtime(org: Org) -> None:
    retirer = Retirer()
    org.runtime = dataclasses.replace(org.runtime, retirement=retirer)
    assert org.retire("ceo", "eng", "r1") == "retire-from-the-port"
    assert org.retire_team("ceo", "eng", "r2") == Retired("team-from-the-port", 1, None)
    assert retirer.calls == [("retire", "ceo", "eng", "r1"), ("retire_team", "ceo", "eng", "r2")]


def test_the_refund_note_is_worded_by_the_notices_of_the_runtime(org: Org) -> None:
    org.send("root", "ceo", "runs", budget=6)
    org.send("ceo", "ceo/eng", "runs", budget=4)
    notices = RecordingNotices()
    org.runtime = wiring.open_runtime(org.root, {Notices: notices})
    org.retire("ceo", "eng", "done")
    assert notices.calls == [("budget_returned", ("ceo/eng", 4, "ceo", "done"))]
    (note,) = [m for m in org.messages("ceo", "inbox") if m.sender == "runtime"]
    assert note.body == "budget_returned: ceo/eng | 4 | ceo | done"


def test_the_charter_body_is_written_by_the_templates_of_the_runtime(org: Org) -> None:
    class Shouting(DocumentTemplates):
        def org_rules(self, mission: str | None) -> str:
            return ""

        def charter_body(self, role: str, charter: str) -> str:
            return f"# {role.upper()}\n\n{charter.upper()}\n"

        def task_body(self, goal: str, acceptance: str, inputs: object) -> str:
            return ""

        def result_body(self, summary: str, artifacts: object, lessons: str = "") -> str:
            return ""

    org.runtime = wiring.open_runtime(org.root, {DocumentTemplates: Shouting()})
    org.hire("ceo", "ops", "Ops", "Do ops.")
    assert org.charter("ceo/ops")[1] == "# OPS\n\nDO OPS."
