"""``DirectReportOwners``, ``CappedPlaybookTexts``, ``EventedPlaybookWriter``: the small rules of the commands."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.kernel import OrgError, OrgPaths
from orgmcp.kernel.testing import FakeClock, ListEventSink
from orgmcp.services._places import OrgServicePlaces
from orgmcp.services._texts import CappedPlaybookTexts, DirectReportOwners, EventedPlaybookWriter
from orgmcp.services.testing import MemoryServiceStore, ServicesWorld, memory_world

from ._support import populated


@pytest.fixture
def w(tmp_path: Path) -> ServicesWorld:
    return populated(memory_world(tmp_path))


def texts(w: ServicesWorld, config: str | None = None) -> CappedPlaybookTexts:
    if config is not None:
        w.d.configure(config)
    return CappedPlaybookTexts(w.d.settings)


# ------------------------------------------------------------------------------ owners


def test_a_full_address_is_normalized_and_kept(w: ServicesWorld) -> None:
    owners = DirectReportOwners(w.d.agents)
    assert owners.resolve("root", "/ceo/eng/") == "ceo/eng"
    assert owners.resolve("ceo", "ceo/eng") == "ceo/eng"


def test_root_names_agents_by_their_address_only(w: ServicesWorld) -> None:
    owners = DirectReportOwners(w.d.agents)
    assert owners.resolve("root", "ghost") == "ghost" and owners.resolve("", "eng") == "eng"


def test_a_manager_may_give_the_short_name_of_a_direct_report(w: ServicesWorld) -> None:
    assert DirectReportOwners(w.d.agents).resolve("ceo", "eng") == "ceo/eng"


def test_a_short_name_that_is_an_agent_of_its_own_is_that_agent(w: ServicesWorld) -> None:
    assert DirectReportOwners(w.d.agents).resolve("ceo", "ops") == "ops"  # ``ops`` exists at the top: the name is taken as it is


def test_a_short_name_that_is_nobodys_is_a_report_that_does_not_exist_yet(w: ServicesWorld) -> None:
    assert DirectReportOwners(w.d.agents).resolve("ceo", "ghost") == "ceo/ghost"


# ------------------------------------------------------------------------------ playbook texts


def test_a_playbook_is_its_text_stripped(w: ServicesWorld) -> None:
    assert texts(w).body("\n  ## Steps\n1. Do.  \n\n") == "## Steps\n1. Do."


def test_the_frontmatter_the_caller_wrote_is_dropped(w: ServicesWorld) -> None:
    assert texts(w).body("---\nversion: 9\n---\nSteps.\n") == "Steps."


def test_windows_line_ends_become_unix_ones(w: ServicesWorld) -> None:
    assert texts(w).body("---\r\nx: 1\r\n---\r\nOne.\r\nTwo.\r\n") == "One.\nTwo."


def test_a_text_that_only_looks_like_a_frontmatter_is_kept(w: ServicesWorld) -> None:
    assert texts(w).body("--- not a block\nSteps.") == "--- not a block\nSteps."


@pytest.mark.parametrize("content", [None, "", "  \n\t", "---\nx: 1\n---\n"])
def test_an_empty_playbook_is_refused(w: ServicesWorld, content: str | None) -> None:
    with pytest.raises(OrgError) as e:
        texts(w).body(content)
    assert str(e.value) == "the playbook is empty: write the workflow (steps: who does what, in which order, which check)"


def test_a_playbook_may_have_exactly_as_many_words_as_the_cap(w: ServicesWorld) -> None:
    capped = texts(w, "---\nmission: test\nplaybook_max_words: 4\n---\nrules\n")
    assert capped.body("a b c d") == "a b c d"
    with pytest.raises(OrgError) as e:
        capped.body("a b c d e")
    assert str(e.value) == (
        "the playbook is 5 words; the limit is 4 (playbook_max_words). Condense it to the steps that "
        "matter and move detail into a file under your work/ directory."
    )


def test_the_cap_is_read_when_the_text_is_checked_not_before(w: ServicesWorld) -> None:
    capped = CappedPlaybookTexts(w.d.settings)
    w.d.configure("---\nmission: test\nplaybook_max_words: 2\n---\nrules\n")
    with pytest.raises(OrgError, match="the limit is 2"):
        capped.body("a b c")


def test_the_default_cap_is_one_thousand_words(w: ServicesWorld) -> None:
    assert len(texts(w).body(" ".join(["w"] * 1000)).split()) == 1000
    with pytest.raises(OrgError, match="the playbook is 1001 words; the limit is 1000"):
        texts(w).body(" ".join(["w"] * 1001))


# ------------------------------------------------------------------------------ the writer


def writer(clock: FakeClock) -> tuple[EventedPlaybookWriter, MemoryServiceStore, ListEventSink]:
    store, events = MemoryServiceStore(OrgServicePlaces(OrgPaths(Path("/org")))), ListEventSink()
    return EventedPlaybookWriter(store, clock, events), store, events


def test_a_written_playbook_has_the_frontmatter_the_runtime_makes() -> None:
    clock = FakeClock()
    pb, store, _ = writer(clock)
    assert pb.write("ceo", "brief", 1, "Steps.", "root", "initial playbook") == "ceo/services/brief/PLAYBOOK.md"
    meta, body = store.read_playbook("ceo", "brief") or ({}, "")
    assert list(meta) == ["service", "version", "revised", "by", "reason"]
    assert (meta["service"], meta["version"], meta["by"], meta["reason"], body.strip()) == ("brief", 1, "root", "initial playbook", "Steps.")
    assert str(meta["revised"]).endswith("+00:00") and len(str(meta["revised"])) == len("2026-10-18T10:00:00.000001+00:00")


def test_the_time_of_a_revision_is_the_time_of_the_clock() -> None:
    clock = FakeClock()
    pb, store, _ = writer(clock)
    pb.write("ceo", "brief", 1, "Steps.", "root", "r")
    first = (store.read_playbook("ceo", "brief") or ({}, ""))[0]["revised"]
    clock.advance(3600)
    pb.write("ceo", "brief", 2, "More.", "ceo", "r", 1)
    assert (store.read_playbook("ceo", "brief") or ({}, ""))[0]["revised"] > first  # type: ignore[operator]


def test_the_old_version_is_kept_when_one_is_named() -> None:
    pb, store, _ = writer(FakeClock())
    pb.write("ceo", "brief", 1, "One.", "root", "r")
    pb.write("ceo", "brief", 2, "Two.", "ceo", "r", 1)
    assert [v for v, _ in store.playbook_history("ceo", "brief")] == [1, 2]


def test_a_revision_is_an_event_by_its_author() -> None:
    pb, _, events = writer(FakeClock())
    pb.write("ceo", "brief", 2, "Two.", "ceo", "r", None)
    (event,) = events.events
    assert (event.kind, event.actor, event.fields) == ("service.revise", "ceo", {"owner": "ceo", "service": "brief", "version": 2, "by": "ceo"})
