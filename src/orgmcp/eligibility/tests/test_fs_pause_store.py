"""``FsPauseStore``: where the flag files are, and what is written into them."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.eligibility._pause import FsPauseStore
from orgmcp.kernel import OrgPaths
from orgmcp.kernel.testing import ListEventSink

from ._support import RED

pytestmark = RED


def build(tmp_path: Path) -> tuple[FsPauseStore, ListEventSink]:
    events = ListEventSink()
    (tmp_path / "ceo" / "eng").mkdir(parents=True)
    return FsPauseStore(OrgPaths(tmp_path), events), events


def test_the_flag_is_the_file_dot_paused_in_the_directory_of_the_agent(tmp_path: Path) -> None:
    store, _ = build(tmp_path)
    store.pause("ceo/eng", "budget")
    assert (tmp_path / "ceo" / "eng" / ".paused").read_bytes() == b"budget"


def test_the_flag_of_root_is_in_the_organization_itself(tmp_path: Path) -> None:
    store, _ = build(tmp_path)
    store.pause("root", "paused by the user")
    assert (tmp_path / ".paused").read_text(encoding="utf-8") == "paused by the user"


def test_an_address_is_normalized(tmp_path: Path) -> None:
    store, events = build(tmp_path)
    store.pause(" /ceo/ ", "budget")
    assert store.paused("ceo") == "budget" and (tmp_path / "ceo" / ".paused").is_file()
    assert events.events[0].fields["agent"] == " /ceo/ "  # the event says what it was asked, as it always did


def test_the_reason_is_written_as_utf8_without_a_newline_added(tmp_path: Path) -> None:
    store, _ = build(tmp_path)
    store.pause("ceo", "Pause: café ☕")
    assert (tmp_path / "ceo" / ".paused").read_bytes() == "Pause: café ☕".encode()


def test_pausing_an_agent_whose_directory_is_gone_raises(tmp_path: Path) -> None:
    store, events = build(tmp_path)
    with pytest.raises(FileNotFoundError):
        store.pause("ghost", "budget")
    assert events.events == []


def test_resuming_an_agent_whose_directory_is_gone_is_nothing(tmp_path: Path) -> None:
    store, events = build(tmp_path)
    store.resume("ghost")
    assert events.events == []
