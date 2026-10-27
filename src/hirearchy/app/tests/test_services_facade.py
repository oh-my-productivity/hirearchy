"""The services slice of the ``Org`` facade: ``service_names``, ``define_service``, ``retire_service``, ``request``, ``revise_playbook`` and ``feedback``
behave as they always did (green before and after), and now go through the ports of the runtime (``service_catalog`` and ``service_commands``)."""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

from hirearchy.app import Org
from hirearchy.kernel import Message, OrgError
from hirearchy.services import Admission, Criterion, Playbook, PlaybookChange, ServiceCatalog, ServiceCommands

BRIEF: dict[str, Any] = dict(
    description="A brief.", inputs=[{"name": "topic", "description": "what", "required": True}], acceptance=["Short"],
    deliverable={"description": "one file"}, budget=4,
)


def use(org: Org, **ports: Any) -> None:
    org.runtime = dataclasses.replace(org.runtime, **ports)


@pytest.fixture
def org(tmp_path: Path) -> Org:
    made = Org.init(tmp_path / "org", "mission")
    made.hire("root", "ceo", "Chief", "Run it.", can_hire=True, max_children=2)
    made.hire("ceo", "eng", "Engineer", "Build.")
    return made


# ----------------------------------------------------------------------------------- as it always was (green before and after)


def test_a_service_is_defined_requested_answered_rated_revised_and_retired(org: Org) -> None:
    assert org.service_names("ceo") == []
    org.define_service("root", "ceo", "weekly-brief", **BRIEF)
    assert org.service_names("ceo") == ["weekly-brief"] and org.service_names("root") == [] and org.service_names("ceo/eng") == []
    task = org.request("root", "weekly-brief", {"topic": "ai"})
    assert (task.type, task.to, task.service, task.contract, task.playbook, task.budget) == ("task", "ceo", "weekly-brief", 1, 0, 4)
    assert org.revise_playbook("ceo", "weekly-brief", "first", "the steps of the first request", [], text="1. Search.\n2. Write.").version == 1  # D6: before any verdict
    org.begin_run("ceo")
    org.start_run_log("ceo")
    org.report("ceo", task.id, "done", "Delivered.", lessons="Worked.")
    note = org.feedback("root", task.id, "reject", "Too long.", source="human")
    assert (note.type, note.wake, note.feedback, note.reply_to, note.source) == ("note", False, "reject", task.id, "human")
    assert org.feedback("root", task.id, "accept").source == "relayed"  # a root verdict is the user's own only when it says so
    org.feedback("root", task.id, "reject", "A one-off.", source="human", criterion=["none"], confirms=note.id)  # the rejection has its answer: only then is it retired
    assert org.retire_service("root", "ceo", "weekly-brief", "done with it").startswith("retired service `weekly-brief` of ceo; files kept at ")
    assert org.service_names("ceo") == []


def test_the_refusals_are_the_texts_agents_are_shown(org: Org) -> None:
    with pytest.raises(OrgError, match="only root, the parent of ceo, can define its services"):
        org.define_service("ceo", "ceo", "x", **BRIEF)
    with pytest.raises(OrgError, match="no service `nope` among your direct reports"):
        org.request("root", "nope", {})
    with pytest.raises(OrgError, match="you do not own a service called `nope`"):
        org.revise_playbook("ceo", "nope", "x", "y", [])


def test_the_names_of_a_service_are_the_directories_with_a_contract(org: Org) -> None:
    org.define_service("root", "ceo", "b-service", **BRIEF)
    org.define_service("root", "ceo", "a-service", **BRIEF)
    (org.dir("ceo") / "services" / "no-contract").mkdir()
    (org.dir("ceo") / "services" / ".hidden").mkdir()
    assert org.service_names("ceo") == ["a-service", "b-service"] and org.service_names("/ceo/") == ["a-service", "b-service"]


# -------------------------------------------------------------------------------------------- through the ports


class Catalog(ServiceCatalog):
    def service_names(self, addr: str) -> list[str]:
        return [f"names-of-{addr}"]

    def read_contract(self, owner: str, name: str) -> Any:
        raise NotImplementedError

    def read_playbook(self, owner: str, name: str) -> Any:
        raise NotImplementedError

    def owned_services(self, owner: str) -> list[Any]:
        raise NotImplementedError

    def requestable_services(self, actor: str) -> list[Any]:
        raise NotImplementedError

    def criteria(self, owner: str, name: str) -> list[Criterion]:
        raise NotImplementedError

    def playbook_versions(self, owner: str, name: str) -> list[Playbook]:
        raise NotImplementedError


class Commands(ServiceCommands):
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def define_service(self, actor: str, owner: str, name: str, **kw: Any) -> str:
        self.calls.append(("define_service", (actor, owner, name), kw))
        return "DEFINED"

    def retire_service(self, actor: str, owner: str, name: str, reason: str) -> str:
        self.calls.append(("retire_service", (actor, owner, name, reason), {}))
        return "RETIRED"

    def request(
        self, actor: str, service: str, inputs: Mapping[str, object] | None, **kw: Any,
    ) -> Message:
        self.calls.append(("request", (actor, service, inputs), kw))
        return Message(sender=actor, to="ceo", type="task", body="b", id="REQUESTED")

    def revise_playbook(self, actor: str, service: str, op: str | None, reason: str, evidence: Sequence[str], **kw: Any) -> PlaybookChange:
        self.calls.append(("revise_playbook", (actor, service, op, reason, evidence), kw))
        return PlaybookChange(7, op or "", "P1", "step", Admission("b", (), ""), None, 1)

    def feedback(self, actor: str, task_id: str, verdict: str, note: str = "", **kw: Any) -> Message:
        self.calls.append(("feedback", (actor, task_id, verdict, note), kw))
        return Message(sender=actor, to="ceo", type="note", body="b", id="RATED")

    def acknowledge_playbook(self, actor: str, owner: str, service: str, item: str, op: str, **kw: Any) -> Message:
        self.calls.append(("acknowledge_playbook", (actor, owner, service, item, op), kw))
        return Message(sender=actor, to=owner, type="note", body="b", id="ACKNOWLEDGED")


def test_service_names_come_from_the_catalog_of_the_runtime(org: Org) -> None:
    use(org, service_catalog=Catalog())
    assert org.service_names("ceo") == ["names-of-ceo"]


def test_define_service_comes_from_the_commands_of_the_runtime_with_the_names_of_the_port(org: Org) -> None:
    fake = Commands()
    use(org, service_commands=fake)
    assert org.define_service("root", "ceo", "x", description="d", inputs=["a"], acceptance=["c"], deliverable={"description": "f"}, budget=2,
                              playbook="p", locked=True, notes="n", add_acceptance=["+"], remove_acceptance=["-"]) == "DEFINED"
    assert fake.calls == [("define_service", ("root", "ceo", "x"), {
        "description": "d", "inputs": ["a"], "acceptance": ["c"], "deliverable": {"description": "f"}, "budget": 2, "playbook": "p", "locked": True,
        "notes": "n", "add_acceptance": ["+"], "remove_acceptance": ["-"], "answers": None, "about": None, "words": None,
    })]
    org.define_service("root", "ceo", "y")
    assert fake.calls[1][2] == {
        "description": None, "inputs": None, "acceptance": None, "deliverable": None, "budget": None, "playbook": None, "locked": None, "notes": None,
        "add_acceptance": None, "remove_acceptance": None, "answers": None, "about": None, "words": None,
    }


def test_org_define_service_passes_answers_about_and_words(org: Org) -> None:
    fake = Commands()
    use(org, service_commands=fake)
    assert org.define_service("root", "ceo", "x", add_acceptance=["+"], answers="M1", about="C2", words="Yes, add it.") == "DEFINED"
    assert org.define_service("root", "ceo", "x", add_acceptance=["+"], words="Add it, please.") == "DEFINED"
    assert [(c[2]["answers"], c[2]["about"], c[2]["words"]) for c in fake.calls] == [("M1", "C2", "Yes, add it."), (None, None, "Add it, please.")]


def test_org_request_passes_base(org: Org) -> None:
    fake = Commands()
    use(org, service_commands=fake)
    assert org.request("root", "x", {"topic": "ai"}, revises="R", source="human", base="delivered").id == "REQUESTED"
    assert fake.calls[0][2]["base"] == "delivered"


def test_the_other_commands_come_from_the_commands_of_the_runtime(org: Org) -> None:
    fake = Commands()
    use(org, service_commands=fake)
    assert org.retire_service("root", "ceo", "x", "why") == "RETIRED"
    assert org.request("root", "x", {"topic": "ai"}, title="T", note="N", extra_acceptance=["e"], budget=3, revises="R", source="human").id == "REQUESTED"
    assert org.request("root", "x", None).id == "REQUESTED"
    assert org.revise_playbook("ceo", "x", "add", "reason", ["R1"], kind="step", text="Search.").version == 7
    assert org.feedback("root", "T1", "reject", "words").id == "RATED" and org.feedback("root", "T1", "accept").id == "RATED"
    assert org.feedback("root", "T1", "reject", "yes", source="human", criterion=["C1"], confirms="M1").id == "RATED"
    assert fake.calls == [
        ("retire_service", ("root", "ceo", "x", "why"), {}),
        ("request", ("root", "x", {"topic": "ai"}), {"title": "T", "note": "N", "extra_acceptance": ["e"], "budget": 3, "revises": "R", "source": "human", "base": None}),
        ("request", ("root", "x", None), {"title": "", "note": "", "extra_acceptance": None, "budget": None, "revises": None, "source": None, "base": None}),
        ("revise_playbook", ("ceo", "x", "add", "reason", ["R1"]), {"item": None, "kind": "step", "text": "Search.", "when": None, "then": None, "after": None, "version": None, "acknowledged": None, "content": None}),
        ("feedback", ("root", "T1", "reject", "words"), {"source": None, "criterion": None, "confirms": None}),
        ("feedback", ("root", "T1", "accept", ""), {"source": None, "criterion": None, "confirms": None}),
        ("feedback", ("root", "T1", "reject", "yes"), {"source": "human", "criterion": ["C1"], "confirms": "M1"}),
    ]


def test_org_acknowledge_playbook_delegates(org: Org) -> None:
    fake = Commands()
    use(org, service_commands=fake)
    assert org.acknowledge_playbook("root", "ceo", "x", "P1", "edit", text_hash="0123456789ab", words="Yes.").id == "ACKNOWLEDGED"
    assert org.acknowledge_playbook("ceo", "eng", "x", "P2", "retire").id == "ACKNOWLEDGED"
    assert fake.calls == [
        ("acknowledge_playbook", ("root", "ceo", "x", "P1", "edit"), {"text_hash": "0123456789ab", "words": "Yes."}),
        ("acknowledge_playbook", ("ceo", "eng", "x", "P2", "retire"), {"text_hash": None, "words": None}),
    ]


def test_revise_playbook_without_evidence_is_a_type_error(org: Org) -> None:
    org.define_service("root", "ceo", "weekly-brief", **BRIEF)
    with pytest.raises(TypeError, match="evidence"):
        org.revise_playbook("ceo", "weekly-brief", "first", "why")  # type: ignore[call-arg]
    assert org.revise_playbook("ceo", "weekly-brief", "first", "why", evidence=[], text="1. Search.").version == 1  # the first version needs none: [] is the answer
