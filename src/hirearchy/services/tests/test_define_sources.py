"""The contract records each criterion's source and the user's words (design 10.1 steps 5 and 6): ``sources`` and ``elicitation`` in SERVICE.md."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from hirearchy.kernel import OrgError, split_frontmatter
from hirearchy.services import CriterionSource, ServiceCommands, criterion_sources
from hirearchy.services.testing import IMPLEMENTATIONS, ServicesWorld

from ._support import amend, define, implementations, make, write_version

CONTRACT = "ceo/services/weekly-brief/SERVICE.md"
QUOTE = "Use the words from the notes."
ASKED = "Owners: initials or full names?"
WORDS = f"{ASKED} initials. {QUOTE}"
SOURCES: list[dict[str, Any]] = [{"from": QUOTE, "asked": ASKED}, {"default": True}]  # parallel to BRIEF's two criteria


@pytest.fixture(params=implementations(IMPLEMENTATIONS[ServiceCommands]))
def w(request: pytest.FixtureRequest, tmp_path: Path) -> ServicesWorld:
    return make(request, tmp_path)


def meta_of(w: ServicesWorld) -> dict[str, object]:
    text = w.text(CONTRACT)
    assert text is not None
    return split_frontmatter(text)[0]


def test_a_first_definition_writes_sources_parallel_to_acceptance_and_the_elicitation(w: ServicesWorld) -> None:
    define(w, sources=SOURCES, elicitation=f"  {WORDS}  ")
    meta = meta_of(w)
    assert meta["sources"] == SOURCES and meta["elicitation"] == WORDS
    assert len(meta["sources"]) == len(meta["acceptance"])  # type: ignore[arg-type]


def test_a_definition_without_sources_writes_neither_key(w: ServicesWorld) -> None:
    define(w)
    assert "sources" not in meta_of(w) and "elicitation" not in meta_of(w)


def test_sources_that_do_not_fit_the_criteria_are_refused_and_write_nothing(w: ServicesWorld) -> None:
    refused: list[object] = [
        [{"default": True}], [{"default": True}] * 3, "default", [{"default": True}, "x"], [{"default": False}, {}], [{"from": "", "asked": "q"}, {}],
        [{"asked": "q"}, {}], [{"from": QUOTE, "default": True}, {}], [{"colour": "red"}, {}], [{"from_tasks": []}, {}], [{"from_tasks": "t-1"}, {}],
    ]
    for bad in refused:
        with pytest.raises(OrgError, match="sources"):
            define(w, sources=bad)
    with pytest.raises(OrgError, match="elicitation"):
        define(w, sources=SOURCES, elicitation="x" * 4001)
    with pytest.raises(OrgError, match="elicitation"):
        define(w, sources=SOURCES, elicitation="   ")
    assert w.text(CONTRACT) is None


def test_an_agents_call_with_sources_or_elicitation_is_refused(w: ServicesWorld) -> None:
    for over in ({"sources": SOURCES}, {"elicitation": WORDS}):
        with pytest.raises(OrgError, match="sources and elicitation are root's"):
            define(w, owner="ceo/eng", actor="ceo", **over)
    assert w.text("ceo/eng/services/weekly-brief/SERVICE.md") is None


def test_an_amendment_cannot_pass_sources_or_elicitation(w: ServicesWorld) -> None:
    define(w, sources=SOURCES, elicitation=WORDS)
    with pytest.raises(OrgError, match="sources and elicitation record a first definition"):
        amend(w, add_acceptance=["Has a summary."], words="Add a summary.", sources=[{}, {}, {}])
    assert meta_of(w)["version"] == 1


def test_criterion_sources_reads_user_default_tasks_amendment_and_unknown(w: ServicesWorld) -> None:
    define(w, acceptance=["One.", "Two.", "Three.", "Four."], sources=[{"from": QUOTE, "asked": ASKED}, {"default": True}, {"from_tasks": ["t-1", "t-2"]}, {}],
           elicitation=WORDS)
    amend(w, add_acceptance=["Five."], words="Add a fifth check.")
    assert criterion_sources(w.store, "ceo", "weekly-brief") == {
        "C1": CriterionSource("user", QUOTE, ASKED), "C2": CriterionSource("default"), "C3": CriterionSource("tasks", tasks=("t-1", "t-2")),
        "C4": CriterionSource("unknown"), "C5": CriterionSource("amendment", "Add a fifth check.", ""),
    }
    assert criterion_sources(w.store, "ceo", "nothing-here") == {}


def test_a_contract_from_before_phase_2_reads_unknown_for_every_criterion(w: ServicesWorld) -> None:
    define(w)
    assert criterion_sources(w.store, "ceo", "weekly-brief") == {"C1": CriterionSource("unknown"), "C2": CriterionSource("unknown")}
    write_version(w, 2, ["At most 600 words", "Every factual claim has a source URL", "Third."])  # an amendment that records no words
    assert criterion_sources(w.store, "ceo", "weekly-brief")["C3"] == CriterionSource("unknown")


def test_a_removed_criterion_keeps_its_source(w: ServicesWorld) -> None:
    define(w, sources=SOURCES, elicitation=WORDS)
    amend(w, remove_acceptance=["At most 600 words"], words="Drop the limit.")
    assert criterion_sources(w.store, "ceo", "weekly-brief")["C1"] == CriterionSource("user", QUOTE, ASKED)


def test_the_amendment_reply_shows_the_words_root_added(w: ServicesWorld) -> None:
    define(w, sources=SOURCES, elicitation=WORDS)
    reply = amend(w, add_acceptance=["Has a summary."], words="Add a summary.")
    assert reply.endswith('\nC3 from your words "Add a summary."; words I added: has.')
    again = amend(w, add_acceptance=["Add a table."], words="Add a table.")
    assert again.endswith('\nC4 from your words "Add a table."; words I added: none.')
    many = amend(w, add_acceptance=["Alpha bravo charlie delta echo foxtrot golf hotel india juliet."], words="Add.")
    assert many.endswith('; words I added: alpha, bravo, charlie, delta, echo, foxtrot, golf, hotel, +2 more.')


def test_an_amendment_that_adds_nothing_has_no_such_line(w: ServicesWorld) -> None:
    define(w)
    reply = amend(w, remove_acceptance=["At most 600 words"], words="Drop the limit.")
    assert " from your words " not in reply


def test_a_first_definition_by_a_plan_writes_approved_in(w: ServicesWorld) -> None:
    define(w, approved_in="plan 0123456789ab")
    assert meta_of(w)["approved_in"] == "plan 0123456789ab"
    define(w, name="other", approved_in="  change 0123456789ab ")
    text = w.text("ceo/services/other/SERVICE.md")
    assert text is not None and split_frontmatter(text)[0]["approved_in"] == "change 0123456789ab"


def test_a_definition_without_an_approval_writes_no_approved_in(w: ServicesWorld) -> None:
    define(w)
    assert "approved_in" not in meta_of(w)


def test_an_agents_approved_in_is_refused(w: ServicesWorld) -> None:
    with pytest.raises(OrgError) as refused:
        define(w, owner="ceo/eng", name="inner", actor="ceo", approved_in="plan 0123456789ab")
    assert str(refused.value) == "refused: approved_in records the user's approval of a change; only root passes it. Nothing was written."
    assert w.text("ceo/eng/services/inner/SERVICE.md") is None


def test_an_amendment_with_approved_in_is_refused_and_keeps_the_mark_of_v1(w: ServicesWorld) -> None:
    define(w, approved_in="plan 0123456789ab")
    with pytest.raises(OrgError, match="approved_in"):
        amend(w, add_acceptance=["Brief"], words="Add a brief.", approved_in="plan 0123456789ab")
    assert meta_of(w)["version"] == 1
