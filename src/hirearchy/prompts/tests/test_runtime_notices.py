"""``RuntimeNotices``: the one-time stray notice, then (only for a service owner) the sections of its services."""

from __future__ import annotations

import pytest

from hirearchy.kernel import Message
from hirearchy.prompts._notices import RuntimeNotices
from hirearchy.prompts.testing import FixedSections, NamedServices, ToldOnce


BATCH = [Message(sender="root", to="ceo", type="note", title="t", body="b", id="20260101T000000000001-root-aaaa")]


def made() -> tuple[RuntimeNotices, ToldOnce, NamedServices, FixedSections]:
    strays, services, sections = ToldOnce(), NamedServices(), FixedSections()
    return RuntimeNotices(strays, services, sections), strays, services, sections


def test_nothing_to_say_is_empty() -> None:
    notices, *_ = made()
    assert notices.notices("ceo", BATCH) == ""


def test_the_stray_notice_is_wrapped_in_newlines_and_told_once() -> None:
    notices, strays, *_ = made()
    strays.notices["ceo"] = "# Notice from the runtime\nSomething."
    assert notices.notices("ceo", BATCH) == "\n# Notice from the runtime\nSomething.\n"
    assert notices.notices("ceo", BATCH) == ""


def test_an_agent_without_services_is_not_asked_for_sections() -> None:
    notices, _, services, sections = made()
    sections.text["ceo"] = "\nnever\n"
    assert notices.notices("ceo", BATCH) == "" and sections.asked == [] and services.asked == ["ceo"]


def test_a_service_owner_gets_the_sections_after_the_notice_with_the_batch() -> None:
    notices, strays, services, sections = made()
    services.offered["ceo"] = ["weekly-brief"]
    sections.text["ceo"] = "\n# Playbook\nDo it.\n"
    strays.notices["ceo"] = "N"
    assert notices.notices("ceo", BATCH) == "\nN\n\n# Playbook\nDo it.\n"
    assert sections.asked == [("ceo", BATCH)]


def test_a_service_owner_with_no_notice_gets_only_the_sections() -> None:
    notices, _, services, sections = made()
    services.offered["ceo"] = ["weekly-brief"]
    sections.text["ceo"] = "\n# Playbook\nDo it.\n"
    assert notices.notices("ceo", BATCH) == "\n# Playbook\nDo it.\n"
