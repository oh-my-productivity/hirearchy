"""The fakes that stand for the texts and the parts of ``prompts`` (consumers put them in when their test is not about the prompts)."""

from __future__ import annotations

from pathlib import Path

from hirearchy.kernel import Message
from hirearchy.prompts import RunPromptBuilder, StateSummarizer, Whoami
from hirearchy.prompts.testing import (
    FixedRunPrompt,
    FixedSections,
    FixedStates,
    FixedStateSummary,
    FixedWhoami,
    NamedServices,
    ToldOnce,
    memory_world,
)

NOTE = Message(sender="root", to="ceo", type="note", title="t", body="b", id="20260101T000000000001-root-aaaa")


def test_the_fixed_texts_are_what_they_were_given_and_remember_the_questions() -> None:
    summary, who, prompt = FixedStateSummary("S"), FixedWhoami("W"), FixedRunPrompt("P")
    assert isinstance(summary, StateSummarizer) and isinstance(who, Whoami) and isinstance(prompt, RunPromptBuilder)
    assert summary.state_summary("a") == "S" and summary.state_summary("b", ["x"]) == "S"
    assert who.whoami("a") == "W"
    assert prompt.run_prompt("a", [NOTE]) == "P"
    assert summary.asked == [("a", None), ("b", ["x"])] and who.asked == ["a"] and prompt.asked == [("a", [NOTE])]


def test_the_states_default_to_idle_and_are_by_normalized_address() -> None:
    states = FixedStates()
    assert states.state("ceo") == "idle"
    states.words["ceo/eng"] = "running"
    assert states.state("ceo/eng/") == "running"


def test_the_services_are_the_ones_offered_and_the_questions_are_remembered() -> None:
    services = NamedServices()
    services.offered["ceo"] = ["a", "b"]
    assert services.service_names("ceo") == ["a", "b"] and services.service_names("ops") == [] and services.asked == ["ceo", "ops"]
    services.service_names("ceo").append("c")
    assert services.service_names("ceo") == ["a", "b"]  # a copy


def test_the_sections_are_the_text_put_in_and_the_batch_is_remembered() -> None:
    sections = FixedSections()
    sections.text["ceo"] = "T"
    assert sections.prompt_sections("ceo", [NOTE]) == "T" and sections.prompt_sections("ops", []) == ""
    assert sections.asked == [("ceo", [NOTE]), ("ops", [])]


def test_a_notice_is_told_once() -> None:
    strays = ToldOnce()
    strays.notices["ceo"] = "N"
    assert strays.take_notice("ceo") == "N" and strays.take_notice("ceo") == "" and strays.take_notice("ops") == ""
    strays.record("ceo", ["a", "b"])
    assert strays.recorded == [("ceo", ("a", "b"))]


def test_a_world_is_an_organization_of_its_own(tmp_path: Path) -> None:
    w = memory_world(tmp_path)
    w.agent("ceo", {"role": "Chief"}, "Run.")
    sent = w.send("root", "ceo", "task", "Plan", "b")
    assert [m.id for m in w.mail.messages("ceo", "inbox")] == [sent.id]
    assert [m.id for m in w.mail.messages("root", "sent")] == [sent.id]
