"""A retired service's copy keeps a ``RETIRED.md`` (design 4.5, L22, PC-9): who retired it, why and under which approval; a continuation moves it into
``history/RETIRED.v<n>.md`` so that the record stays readable."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from hirearchy.kernel import OrgError, split_frontmatter
from hirearchy.services.testing import ServicesWorld, fs_world, memory_world

from ._support import answer, define, implementations, populated

SERVICE = "weekly-brief"
COPY = re.compile(r"ceo/services/\.retired/weekly-brief-\d{8}T\d{12}")


@pytest.fixture(params=implementations([fs_world, memory_world]))
def w(request: pytest.FixtureRequest, tmp_path: Path) -> ServicesWorld:
    return populated(request.param(tmp_path))


def retired_copy(reply: str) -> str:
    found = COPY.search(reply)
    assert found is not None, reply
    return found.group(0)


def recorded_and_retired(w: ServicesWorld, **kw: str) -> str:
    """``ceo`` offers ``weekly-brief``, one request of it has a result, and root retires it; returns the retired copy's directory."""
    define(w)
    answer(w, w.commands.request("root", SERVICE, {"topic": "ai"}))
    return retired_copy(w.commands.retire_service("root", "ceo", SERVICE, "not needed", **kw))


def test_root_retire_writes_retired_md_with_retired_by_reason_and_approved_in(w: ServicesWorld) -> None:
    define(w)
    copy = retired_copy(w.commands.retire_service("root", "ceo", SERVICE, "  the team was restructured  ", approved_in="change 0123456789ab"))
    text = w.text(f"{copy}/RETIRED.md")
    assert text is not None
    meta = split_frontmatter(text)[0]
    assert list(meta) == ["retired", "by", "reason", "approved_in"]
    assert (meta["by"], meta["reason"], meta["approved_in"]) == ("root", "the team was restructured", "change 0123456789ab")
    assert isinstance(meta["retired"], str) and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d.*", meta["retired"])


def test_a_retire_without_an_approval_leaves_approved_in_out(w: ServicesWorld) -> None:
    define(w)
    copy = retired_copy(w.commands.retire_service("root", "ceo", SERVICE, "not needed"))
    text = w.text(f"{copy}/RETIRED.md")
    assert text is not None
    meta = split_frontmatter(text)[0]
    assert list(meta) == ["retired", "by", "reason"] and meta["by"] == "root"


def test_an_agents_retire_with_approved_in_is_refused_word_for_word(w: ServicesWorld) -> None:
    define(w, owner="ceo/eng", name="inner", actor="ceo")
    with pytest.raises(OrgError) as refused:
        w.commands.retire_service("ceo", "ceo/eng", "inner", "not needed", approved_in="change 0123456789ab")
    assert str(refused.value) == "refused: approved_in records the user's approval of a change; only root passes it. Nothing was retired."
    assert w.catalog.service_names("ceo/eng") == ["inner"]
    assert not [e for e in w.events.events if e.kind == "service.retire"]
    w.commands.retire_service("ceo", "ceo/eng", "inner", "not needed")  # an agent client retires as before, and its copy has a record too
    (record,) = [p for p in w.rels() if p.endswith("RETIRED.md")]
    text = w.text(record)
    assert record.startswith("ceo/eng/services/.retired/inner-") and text is not None and split_frontmatter(text)[0]["by"] == "ceo"


def test_a_continuation_moves_retired_md_to_history(w: ServicesWorld) -> None:
    copy = recorded_and_retired(w, approved_in="change 0123456789ab")
    record = w.text(f"{copy}/RETIRED.md")
    assert record is not None
    define(w)  # root defines it again: the retired copy has a request with a result, so this continues it
    live = "ceo/services/weekly-brief"
    assert w.text(f"{live}/RETIRED.md") is None
    assert w.text(f"{live}/history/RETIRED.v1.md") == record  # v1: the contract version it retired


def test_a_copy_without_retired_md_reads_as_before(w: ServicesWorld) -> None:
    define(w)
    answer(w, w.commands.request("root", SERVICE, {"topic": "ai"}))
    w.store.retire("ceo", SERVICE, "20260101T000000000001")  # a copy as an organization from before Phase 2 keeps it: no record
    assert not [p for p in w.rels() if p.endswith("RETIRED.md")]
    define(w)
    assert w.catalog.service_names("ceo") == [SERVICE]
    assert not [p for p in w.rels() if "RETIRED" in p.rsplit("/", 1)[1]]
