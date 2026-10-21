"""``services define-service request feedback retire-service`` over fakes: the arguments become the calls, the snapshots follow, the words are the old ones."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.cli._commands_services import DefineServiceCommand, FeedbackCommand, RequestCommand, RetireServiceCommand, ServicesCommand
from hirearchy.cli.testing import MemoryText
from hirearchy.kernel import OrgError
from hirearchy.services import Contract

from ._fakes import FakeOffice, FakeReadings, FakeServices, new_office, new_readings, new_services
from ._support import Fixture, go, parse


TEXT = MemoryText({"criterion.md": "Has a title.\n", "notes.md": "For the owner.\n", "playbook.md": "Step one.\n"})


def define_world(tmp_path: Path, contracts: dict[tuple[str, str], Contract] | None = None) -> tuple[Fixture, FakeServices, FakeOffice, DefineServiceCommand]:
    f, services, office = Fixture(tmp_path), new_services(contracts), new_office()
    return f, services, office, DefineServiceCommand(f.session, lambda: services, lambda: services, lambda: services, lambda: office, TEXT, f.out)


def test_services_lists_what_root_can_request(tmp_path: Path) -> None:
    f, readings = Fixture(tmp_path), new_readings()
    go(ServicesCommand(f.session, lambda: readings, f.out), "services")
    assert f.session.calls == [("open", False)]  # read-only: nothing is announced
    assert readings.last("services_text") == (("root",), {})
    assert f.out.stdout == "services text\n"


def test_a_first_definition_passes_every_part_and_commits(tmp_path: Path) -> None:
    f, services, office, command = define_world(tmp_path)
    go(command, "define-service", "ceo", "weekly", "--description", "A note", "--input", "topic*:what", "--input", "tone:how",
       "--acceptance", "@criterion.md", "--acceptance", "Short.", "--deliverable", "The note", "--format", "markdown", "--max-words", "300",
       "--path", "/out", "--budget", "4", "--playbook", "@playbook.md", "--locked", "--notes", "@notes.md")
    assert f.session.calls == [("open", True)]
    args, kwargs = services.last("define_service")
    assert args == ("root", "ceo", "weekly")
    assert kwargs == {
        "description": "A note",
        "inputs": [{"name": "topic", "description": "what", "required": True}, {"name": "tone", "description": "how", "required": False}],
        "acceptance": ["Has a title.\n", "Short."], "deliverable": {"description": "The note", "format": "markdown", "max_words": 300, "path": "/out"},
        "budget": 4, "playbook": "Step one.\n", "locked": True, "notes": "For the owner.\n", "add_acceptance": None, "remove_acceptance": None,
    }
    assert office.last("commit") == (("root: service weekly of ceo",), {})
    assert f.out.stdout == "defined service `weekly` for ceo\n"


def test_an_amendment_without_a_description_keeps_the_rest_of_the_deliverable(tmp_path: Path) -> None:
    old = Contract("weekly", "ceo", deliverable={"description": "The note", "format": "markdown"})
    f, services, office, command = define_world(tmp_path, {("ceo", "weekly"): old})
    go(command, "define-service", "ceo/", "weekly", "--max-words", "200")
    assert services.last("read_contract") == (("ceo", "weekly"), {})  # the owner's address normalized
    assert services.last("define_service")[1]["deliverable"] == {"description": "The note", "format": "markdown", "max_words": 200}


def test_a_deliverable_with_a_description_is_taken_as_it_is(tmp_path: Path) -> None:
    f, services, office, command = define_world(tmp_path)
    go(command, "define-service", "ceo", "weekly", "--deliverable", "New", "--format", "text")
    assert "read_contract" not in services.names()
    assert services.last("define_service")[1]["deliverable"] == {"description": "New", "format": "text"}


def test_no_deliverable_part_means_no_deliverable(tmp_path: Path) -> None:
    f, services, office, command = define_world(tmp_path)
    go(command, "define-service", "ceo", "weekly", "--add-acceptance", "Has a summary.", "--remove-acceptance", "@criterion.md", "--no-locked")
    _, kwargs = services.last("define_service")
    assert kwargs["deliverable"] is None and kwargs["locked"] is False and kwargs["inputs"] is None and kwargs["acceptance"] is None
    assert kwargs["add_acceptance"] == ["Has a summary."] and kwargs["remove_acceptance"] == ["Has a title.\n"]
    assert "read_contract" not in services.names()


def test_a_refused_definition_is_not_committed(tmp_path: Path) -> None:
    f, services, office, command = define_world(tmp_path)
    services.refuse = OrgError("no such agent: nobody")
    with pytest.raises(OrgError):
        go(command, "define-service", "nobody", "weekly")
    assert office.calls == [] and f.out.stdout == ""


def test_request_turns_the_inputs_into_a_mapping(tmp_path: Path) -> None:
    f, services, office = Fixture(tmp_path), new_services(), new_office()
    go(RequestCommand(f.session, lambda: services, lambda: office, f.out), "request", "weekly", "--input", "topic=tests", "--input", " k = a=b",
       "--title", "Weekly", "--note", "Please.", "--budget", "3", "--revises", "r-0")
    assert f.session.calls == [("open", True)]
    assert services.last("request") == (("root", "weekly", {"topic": "tests", "k": " a=b"}), {"title": "Weekly", "note": "Please.", "budget": 3, "revises": "r-0"})
    assert office.last("commit") == (("root: request r-1 -> ceo",), {})
    assert f.out.stdout == "request r-1 -> ceo (service weekly, budget 3)\n"


def test_an_input_without_an_equals_sign_is_refused_before_anything_is_asked(tmp_path: Path) -> None:
    f, services, office = Fixture(tmp_path), new_services(), new_office()
    with pytest.raises(OrgError, match=r"--input must be key=value \(got 'topic'\)"):
        go(RequestCommand(f.session, lambda: services, lambda: office, f.out), "request", "weekly", "--input", "topic")
    assert f.session.calls == [("open", True)] and services.calls == [] and office.calls == []


def test_feedback_tells_the_owner_and_says_who(tmp_path: Path) -> None:
    f, services, office = Fixture(tmp_path), new_services(), new_office()
    go(FeedbackCommand(f.session, lambda: services, lambda: office, f.out), "feedback", "r-1", "reject", "--note", "Too long.")
    assert f.session.calls == [("open", True)]
    assert services.last("feedback") == (("root", "r-1", "reject", "Too long."), {})
    assert office.last("commit") == (("root: feedback f-1 -> ceo",), {})
    assert f.out.stdout == "feedback reject on r-1 -> ceo\n"


def test_feedback_accepts_only_a_verdict(tmp_path: Path) -> None:
    f, services, office = Fixture(tmp_path), new_services(), new_office()
    with pytest.raises(SystemExit):
        parse(FeedbackCommand(f.session, lambda: services, lambda: office, f.out), "feedback", "r-1", "maybe")


def test_retire_service_says_what_happened_before_it_snapshots(tmp_path: Path) -> None:
    f, services, office = Fixture(tmp_path), new_services(), new_office()
    go(RetireServiceCommand(f.session, lambda: services, lambda: office, f.out), "retire-service", "ceo", "weekly", "--reason", "Not needed.")
    assert services.last("retire_service") == (("root", "ceo", "weekly", "Not needed."), {})
    assert f.out.stdout == "retired service `weekly` of ceo\n" and office.last("commit") == (("root: retired service weekly of ceo",), {})
